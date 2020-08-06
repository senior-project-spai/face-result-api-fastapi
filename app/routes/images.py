from fastapi import APIRouter, HTTPException
import pymysql
from PIL import Image

from app.config import MYSQL_CONFIG_FADE
from app.s3 import get_file_stream
from app.utils import image_to_data_uri

router = APIRouter()


@router.get("/latest")
def read_latest_image():
    ''' return image and data of the latest image '''
    # Connect to database
    sql_connection = pymysql.connect(**MYSQL_CONFIG_FADE)

    # Get DictCursor
    with sql_connection.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id, path, timestamp "
                       "FROM image "
                       "ORDER BY timestamp DESC "
                       "LIMIT 1;")
        image = cursor.fetchone()

    # Check if the latest image is exist
    if image is None:
        raise HTTPException(404, "Image not found")

    # Get image from S3
    image["Image"] = Image.open(get_file_stream(image["path"]))

    # Close database connection
    sql_connection.close()

    return {'id': image['id'],
            'path': image['path'],
            'timestamp': image['timestamp'],
            'data_uri': image_to_data_uri(image["Image"])}
