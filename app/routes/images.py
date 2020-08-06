from fastapi import APIRouter, HTTPException
import pymysql
from PIL import Image

from app.config import MYSQL_CONFIG_FADE
from app.s3 import get_file_stream
from app.utils import image_to_data_uri

router = APIRouter()

SELECT_ALL_FACES_RESULT_QUERY = """
SELECT 
    face.id as id,
    face.position_top,
    face.position_right,
    face.position_bottom, 
    face.position_left,
    gender.male_confidence,
    gender.female_confidence,
    age.0_to_10_confidence,
    age.11_to_20_confidence,
    age.21_to_30_confidence,
    age.31_to_40_confidence,
    age.41_to_50_confidence,
    age.51_to_60_confidence,
    age.61_to_70_confidence,
    age.71_to_100_confidence,
    emotion.uncertain_confidence,
    emotion.angry_confidence,
    emotion.disgusted_confidence,
    emotion.fearful_confidence,
    emotion.happy_confidence,
    emotion.neutral_confidence,
    emotion.sad_confidence,
    emotion.surprised_confidence,
    face_recognition.label
FROM face 
    INNER JOIN gender ON face.gender_id = gender.id
    INNER JOIN age ON face.age_id = age.id
    INNER JOIN emotion ON face.emotion_id = emotion.id
    INNER JOIN face_recognition ON face.face_recognition_id = face_recognition.id
WHERE face.image_id=%(image_id)s;
"""

def fetch_latest_image(cnx: pymysql.connections.Connection):
    # Get DictCursor
    with cnx.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id, path, timestamp "
                       "FROM image "
                       "ORDER BY timestamp DESC "
                       "LIMIT 1;")
        image_row = cursor.fetchone()
    return image_row


@router.get('/latest/faces')
def read_all_faces_latest_image():
    # Connect to database
    sql_connection = pymysql.connect(**MYSQL_CONFIG_FADE)

    latest_image = fetch_latest_image(sql_connection)

    with sql_connection.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
        cursor.execute(SELECT_ALL_FACES_RESULT_QUERY, {'image_id': latest_image['id']})
        faces = cursor.fetchall()

    # Close database connection
    sql_connection.close()

    return faces if faces is not None else []


@router.get("/latest")
def read_latest_image():
    ''' return image and data of the latest image '''
    # Connect to database
    sql_connection = pymysql.connect(**MYSQL_CONFIG_FADE)

    # fetch latest image from database
    latest_image = fetch_latest_image(sql_connection)

    # Check if the latest image is exist
    if latest_image is None:
        raise HTTPException(404, "Image not found")

    # Get image from S3
    latest_image["Image"] = Image.open(get_file_stream(latest_image["path"]))

    # Close database connection
    sql_connection.close()

    return {'id': latest_image['id'],
            'path': latest_image['path'],
            'timestamp': latest_image['timestamp'],
            'data_uri': image_to_data_uri(latest_image["Image"])}
