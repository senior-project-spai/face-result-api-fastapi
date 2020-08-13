from fastapi import APIRouter, HTTPException
import pymysql
from PIL import Image

from app.config import MYSQL_CONFIG_FADE
from app.s3 import get_file_stream
from app.utils import image_to_data_uri, draw_box, find_intersect_area

router = APIRouter()

TABLE_COLUMN_NAME = {'age': ["0_to_10_confidence",
                         "11_to_20_confidence",
                         "21_to_30_confidence",
                         "31_to_40_confidence",
                         "41_to_50_confidence",
                         "51_to_60_confidence",
                         "61_to_70_confidence",
                         "71_to_100_confidence"],
                 'gender': ['male_confidence',
                            'female_confidence'],
                 'emotion': ["uncertain_confidence",
                             "angry_confidence",
                             "disgusted_confidence",
                             "fearful_confidence",
                             "happy_confidence",
                             "neutral_confidence",
                             "sad_confidence",
                             "surprised_confidence"],
                 'face_recognition': ['label']}


def fetch_image(image_id: str, cnx: pymysql.connections.Connection):
    image_id = image_id if image_id != "latest" else None
    # Get DictCursor
    with cnx.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id, path, timestamp, gender_timestamp, age_timestamp, emotion_timestamp, face_recognition_timestamp "
                       "FROM image "
                       "WHERE id=COALESCE(%(image_id)s,id) "
                       "ORDER BY timestamp DESC "
                       "LIMIT 1;", {'image_id': image_id})
        image_row = cursor.fetchone()
    return image_row


@router.get('/{image_id}/faces')
def read_all_faces_image(image_id: str):
    # Connect to database
    sql_connection = pymysql.connect(**MYSQL_CONFIG_FADE)

    image = fetch_image(image_id, sql_connection)

    # Check if the latest image is exist
    if image is None:
        raise HTTPException(404, "Image not found")

    with sql_connection.cursor(cursor=pymysql.cursors.DictCursor) as cursor:

        # Fetch results from each tables
        fetch_result = {}
        for table_result, table_column_list in TABLE_COLUMN_NAME.items():

            # Skip this table if result is not inserted
            if image[f'{table_result}_timestamp'] is None:
                continue

            # Fetch result from database
            cursor.execute(f"SELECT id, position_top, position_right, position_bottom, position_left, {', '.join(table_column_list)} "
                           f"FROM {table_result} "
                           "WHERE image_id=%(image_id)s "
                           "ORDER BY timestamp;",
                           {'image_id': image['id']})
            fetch_result[table_result] = cursor.fetchall()

    # Close database connection
    sql_connection.close()

    # Create faces from all fetched results
    faces = []
    # Iterate through each table
    for table, result_list in fetch_result.items():
        # Iterate through each result in that table
        for result in result_list:
            # Find the exist face
            face_index_to_update = None
            for face_index, face in enumerate(faces):
                # Calculate intersection area
                area = find_intersect_area({'top': face['position_top'],
                                            'right': face['position_right'],
                                            'bottom': face['position_bottom'],
                                            'left': face['position_left']},
                                           {'top': result['position_top'],
                                            'right': result['position_right'],
                                            'bottom': result['position_bottom'],
                                            'left': result['position_left']})

                # condition to update the exist face
                # condition: if the intersection between face and result is exist
                # TODO: use a better condition
                if area is not None:
                    face_index_to_update = face_index
                    break

            if face_index_to_update is not None:
                # Update face position to the exist face
                faces[-1]["position_top"] = min(faces[-1]["position_top"], result["position_top"])
                faces[-1]["position_right"] = max(faces[-1]["position_right"], result["position_right"])
                faces[-1]["position_bottom"] = max(faces[-1]["position_bottom"], result["position_bottom"])
                faces[-1]["position_left"] = min(faces[-1]["position_left"], result["position_left"])

                # Add each column
                for column_name in TABLE_COLUMN_NAME[table]:
                    faces[face_index_to_update][column_name] = result[column_name]
            else:
                # Create new face
                faces.append({})

                # Add face position
                for position in ("position_top", "position_right", "position_bottom", "position_left"):
                    faces[-1][position] = result[position]

                # Add each column
                for column_name in TABLE_COLUMN_NAME[table]:
                    faces[-1][column_name] = result[column_name]

    return faces


@router.get("/{image_id}")
def read_image(image_id: str):
    ''' return image and data of the latest image '''
    # Connect to database
    sql_connection = pymysql.connect(**MYSQL_CONFIG_FADE)

    # Fetch image by ID
    image = fetch_image(image_id, sql_connection)

    # Check if the latest image is exist
    if image is None:
        sql_connection.close()
        raise HTTPException(404, "Image not found")

    # Fetch all faces position
    with sql_connection.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id, position_top, position_right, position_bottom, position_left "
                       "FROM face "
                       "WHERE image_id=%(image_id)s "
                       "ORDER BY timestamp;",
                       {'image_id': image['id']})
        faces = cursor.fetchall()

    # Close database connection
    sql_connection.close()

    # Get image from S3
    image["Image"] = Image.open(get_file_stream(image["path"]))

    return {'id': image['id'],
            'path': image['path'],
            'timestamp': image['timestamp'],
            'data_uri': image_to_data_uri(image["Image"])}


@router.get("/")
def read_all_images():
    ''' Return all images '''
    # Connect to database
    sql_connection = pymysql.connect(**MYSQL_CONFIG_FADE)

    with sql_connection.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id, path, timestamp "
                       "FROM image "
                       "ORDER BY timestamp DESC ")
        images = cursor.fetchall()

    # Close database connection
    sql_connection.close()

    return images if images is not None else []
