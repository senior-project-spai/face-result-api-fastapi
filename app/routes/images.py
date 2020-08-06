from fastapi import APIRouter, HTTPException
import pymysql
from PIL import Image

from app.config import MYSQL_CONFIG_FADE
from app.s3 import get_file_stream
from app.utils import image_to_data_uri

router = APIRouter()


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

    # Close database connection
    sql_connection.close()

    return {} # TODO: return all result


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
