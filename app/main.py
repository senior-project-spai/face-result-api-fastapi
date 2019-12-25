import os
from typing import Tuple

# fastapi
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

# sql
import pymysql
from pymysql.cursors import DictCursor

# Image
import base64
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# S3
import s3


# Environment variables
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_PORT = int(os.getenv('MYSQL_PORT'))
MYSQL_DB = os.getenv('MYSQL_DB')

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=['*'])

connection = None


@app.on_event('startup')
def startup():
    global connection
    connection = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, passwd=MYSQL_PASSWORD, db=MYSQL_DB)


@app.on_event('shutdown')
def shutdown():
    connection.close()


def image_to_data_uri(img: Image.Image):
    buffered = BytesIO()
    img.save(buffered, 'JPEG')
    img_base64 = base64.b64encode(buffered.getvalue())
    data_uri_byte = bytes("data:image/jpeg;base64,",
                          encoding='utf-8') + img_base64
    data_uri_string = data_uri_byte.decode('utf-8')
    return data_uri_string


def draw_box(img, lt_corner: Tuple[int], rb_corner: Tuple[int], index: int):
    draw = ImageDraw.Draw(img)
    draw.rectangle([lt_corner, rb_corner], outline="red", width=2)
    draw.text(lt_corner, str(index), font=ImageFont.truetype(
        "font/RobotoMono-Bold.ttf", size=16))
    return img


def get_s3_image(uri: str):
    img_stream = s3.get_file_stream(uri)
    return Image.open(img_stream)


def get_latest_result_all():
    if not connection.open:
        connection.ping(reconnect=True)
    with connection.cursor(cursor=DictCursor) as cursor:
        query_latest = ("SELECT branch_id, camera_id, epoch "
                        "FROM data "
                        "ORDER BY epoch DESC "
                        "LIMIT 1;")
        cursor.execute(query_latest)
        row = cursor.fetchone()

        query_all_result = ("SELECT branch_id, camera_id, filepath, epoch,"
                            "       gender, gender_confident, race, race_confident,"
                            "       position_top, position_left, position_right, position_bottom, position_left "
                            "FROM data "
                            "WHERE branch_id=%s AND camera_id=%s AND epoch=%s;")
        cursor.execute(query_all_result,
                       (row['branch_id'], row['camera_id'], row['epoch']))
        rows = cursor.fetchall()
    return rows


@app.get("/_api/result/latest")
def result_latest():
    rows = get_latest_result_all()

    original_image = get_s3_image(rows[0]["filepath"])

    image_with_box = original_image
    results = []
    for index, row in enumerate(rows):
        image_with_box = draw_box(image_with_box, (row['position_left'], row['position_top']), (
            row['position_right'], row['position_bottom']), index)
        results.append({
            'gender': {
                'gender': row['gender'],
                'confidence': row['gender_confident']
            },
            'race': {
                'race': row['race'],
                'confidence': row['race_confident']
            }
        })

    return {'epoch': rows[0]['epoch'],
            'branch_id': rows[0]['branch_id'],
            'camera_id': rows[0]['camera_id'],
            'results': results,
            'photo_data_uri': image_to_data_uri(image_with_box)}
