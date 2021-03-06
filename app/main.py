import os
from typing import Tuple
import csv
from io import StringIO
import time

# fastapi
from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from pydantic import BaseModel

# sql
import pymysql
from pymysql.cursors import DictCursor

# Image
from PIL import Image, ImageDraw, ImageFont
from app.utils import image_to_data_uri

# S3
from app import s3

# logging
import logging
logger = logging.getLogger("api")

# routes
from app import routes

# Environment variables
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_PORT = int(os.getenv('MYSQL_PORT'))
MYSQL_DB = os.getenv('MYSQL_DB')

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=['*'])

# including routes
app.include_router(routes.images.router, prefix="/_api/images", tags=["images"])


# TODO: use method from utils.py instead
def draw_box(img, lt_corner: Tuple[int], rb_corner: Tuple[int], title: str):
    draw = ImageDraw.Draw(img)
    draw.rectangle([lt_corner, rb_corner], outline="red", width=2)
    draw.text(lt_corner, title, font=ImageFont.truetype(
        "app/font/RobotoMono-Bold.ttf", size=16))
    return img


def get_s3_image(uri: str):
    img_stream = s3.get_file_stream(uri)
    return Image.open(img_stream)


@app.get("/_api/result/csv")
def result_csv(start: float = None,
               end: float = None,
               race: str = None,
               gender: str = None,
               min_age: int = None,
               max_age: int = None,
               branch: int = None,
               camera: int = None,
               min_gender_confidence: float = None,
               max_gender_confidence: float = None,
               min_age_confidence: float = None,
               max_age_confidence: float = None,
               min_race_confidence: float = None,
               max_race_confidence: float = None):

    # If all param is none, return nothing
    if all([branch is None, camera is None,
            max_gender_confidence is None, max_race_confidence is None, max_age_confidence is None,
            min_gender_confidence is None, min_age_confidence is None, min_race_confidence is None,
            start is None, end is None,
            race is None, gender is None, min_age is None, max_age is None]):
        raise HTTPException(
            status_code=400, detail="At least one parameter is needed")

    # get data from DB
    connection = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        passwd=MYSQL_PASSWORD,
        db=MYSQL_DB,
        autocommit=True
    )
    rows = None
    with connection.cursor(cursor=DictCursor) as cursor:
        query = ("SELECT "
                 "  FaceImage.id AS ID, "
                 "  FaceImage.time AS Time, "
                 "  FaceImage.branch_id AS `Branch ID`, "
                 "  FaceImage.camera_id AS `Camera ID`, "
                 "  FaceImage.image_path AS `Image Path`, "
                 "  Gender.type AS Gender, "
                 "  Gender.confidence AS `Gender Confidence`, "
                 "  Age.min_age AS `Min Age`, "
                 "  Age.max_age AS `Max Age`, "
                 "  Age.confidence AS `Age Confidence`, "
                 "  Race.type AS Race, "
                 "  Race.confidence AS `Race Confidence` "
                 "FROM FaceImage "
                 "  INNER JOIN Gender ON FaceImage.id = Gender.face_image_id "
                 "  INNER JOIN Age ON FaceImage.id = Age.face_image_id "
                 "  INNER JOIN Race ON FaceImage.id = Race.face_image_id")

        # Add WHERE Clause
        condition_list = []
        if start is not None:
            condition_list.append("FaceImage.time >= %(start)s")
        if end is not None:
            condition_list.append("FaceImage.time <= %(end)s")
        if race is not None:
            condition_list.append("Race.type like %(race)s")
        if gender is not None:
            condition_list.append("Gender.type like %(gender)s")
        if min_age is not None:
            condition_list.append("Age.min_age >= %(min_age)s")
        if max_age is not None:
            condition_list.append("Age.max_age <= %(max_age)s")
        if min_gender_confidence is not None:
            condition_list.append(
                "Gender.confidence >= %(min_gender_confidence)s")
        if min_age_confidence is not None:
            condition_list.append(
                "Gender.confidence <= %(min_age_confidence)s")
        if min_race_confidence is not None:
            condition_list.append(
                "Race.confidence >= %(min_race_confidence)s")
        if max_gender_confidence is not None:
            condition_list.append(
                "Race.confidence <= %(max_gender_confidence)s")
        if max_age_confidence is not None:
            condition_list.append("Age.confidence >= %(max_age_confidence)s")
        if max_race_confidence is not None:
            condition_list.append("Age.confidence <= %(max_race_confidence)s")
        if branch is not None:
            condition_list.append("FaceImage.branch_id = %(branch)s")
        if camera is not None:
            condition_list.append("FaceImage.camera_id = %(camera)s")
        # Convert to string
        condition_query_str = ""
        for condition in condition_list:
            condition_query_str += condition
            if condition != condition_list[-1]:
                condition_query_str += " AND "
        if condition_query_str != "":
            query += " WHERE " + condition_query_str

        print(query)
        effected_row = cursor.execute(query, {
            "start": start,
            "end": end,
            "race": "%{}%".format(race),
            "gender": "%{}%".format(gender),
            "branch": branch,
            "camera": camera,
            "max_age": max_age,
            "min_age": min_age,
            "min_gender_confidence": min_gender_confidence,
            "min_age_confidence": min_age_confidence,
            "min_race_confidence": min_race_confidence,
            "max_gender_confidence": max_gender_confidence,
            "max_age_confidence": max_age_confidence,
            "max_race_confidence": max_race_confidence
        })
        rows = cursor.fetchall()
    connection.close()

    # Return nothing if rows is empty
    if not rows:
        # return 204 code
        raise HTTPException(status_code=204, detail="Result is empty")

    # Transform to CSV
    csv_stream = StringIO()
    csv_writer = csv.DictWriter(csv_stream, fieldnames=list(rows[0].keys()))
    csv_writer.writeheader()
    csv_writer.writerows(rows)
    csv_stream.seek(0)

    # Send to response
    time_str = time.strftime("%d_%b_%Y_%H:%M:%S_+0000", time.gmtime())
    csv_name = "result_{}.csv".format(time_str)
    return StreamingResponse(csv_stream, media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="{}"'.format(csv_name)})


def get_result(face_image_id=None):
    connection = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, passwd=MYSQL_PASSWORD, db=MYSQL_DB, autocommit=True)
    with connection.cursor(cursor=DictCursor) as cursor:
        if face_image_id:
            query_latest_face_image = ("SELECT id, image_path, camera_id, branch_id, `time`, "
                                       "       position_top, position_right, position_bottom, position_left "
                                       "FROM FaceImage "
                                       "WHERE id=%(face_image_id)s "
                                       "ORDER BY time DESC "
                                       "LIMIT 1;")
        else:
            # Get latest face_image_id
            query_latest_face_image = ("SELECT id, image_path, camera_id, branch_id, `time`, "
                                       "       position_top, position_right, position_bottom, position_left "
                                       "FROM FaceImage "
                                       "ORDER BY time DESC "
                                       "LIMIT 1;")
        cursor.execute(query_latest_face_image, {
                       'face_image_id': face_image_id})
        face_image_row = cursor.fetchone()

        # return empty dict to all results if face_image is not found
        if face_image_row is None:
            return {}, {}, {}, {}

        # Get face_image_id
        face_image_id = face_image_row['id']

        # Get Gender Result
        query_gender = ("SELECT type, confidence "
                        "FROM Gender "
                        "WHERE face_image_id=%s;")
        cursor.execute(query_gender, (face_image_id,))
        gender_row = cursor.fetchone()

        # Get Race Result
        query_race = ("SELECT type, confidence "
                      "FROM Race "
                      "WHERE face_image_id=%s;")
        cursor.execute(query_race, (face_image_id,))
        race_row = cursor.fetchone()

        # Get Age Result
        query_age = ("SELECT min_age, max_age, confidence "
                     "FROM Age "
                     "WHERE face_image_id=%s;")
        cursor.execute(query_age, (face_image_id,))
        age_row = cursor.fetchone()
    connection.close()
    logger.debug(face_image_row, gender_row, race_row, age_row)
    return face_image_row, gender_row, race_row, age_row


@app.get("/_api/result/{face_image_id}")
def result(face_image_id: str):
    # Get all rows
    if face_image_id == 'latest':
        face_image_result, gender_result, race_result, age_result = get_result()
    else:
        face_image_result, gender_result, race_result, age_result = get_result(
            int(face_image_id))

    # raise error if face_image is not found
    if not face_image_result:
        raise HTTPException(status_code=404, detail="Face image not found")

    # Get image
    image = get_s3_image(face_image_result['image_path'])

    # Draw box if all positions are not null
    if all([face_image_result['position_left'],
            face_image_result['position_top'],
            face_image_result['position_right'],
            face_image_result['position_bottom']]):
        image = draw_box(image,
                         (face_image_result['position_left'],
                          face_image_result['position_top']),
                         (face_image_result['position_right'],
                          face_image_result['position_bottom']),
                         "")

    # Insert one result
    results = [{
        'gender': {
            'type': gender_result['type'],
            'confidence': gender_result['confidence']
        },
        'race': {
            'type': race_result['type'],
            'confidence': race_result['confidence']
        },
        'age': {
            'min_age': age_result['min_age'],
            'max_age': age_result['max_age'],
            'confidence': age_result['confidence']
        }
    }]

    return {'epoch': face_image_result['time'],
            'id': face_image_result['id'],
            'branch_id': face_image_result['branch_id'],
            'camera_id': face_image_result['camera_id'],
            'results': results,
            'photo_data_uri': image_to_data_uri(image)}


# For check with probe in openshift
@app.get('/healthz')
def health_check():
    return
