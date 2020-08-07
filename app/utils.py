import base64
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import Tuple


def image_to_data_uri(img: Image.Image):
    ''' Convert PILLOW image to data URI '''
    buffered = BytesIO()
    img.save(buffered, 'JPEG')
    img_base64 = base64.b64encode(buffered.getvalue())
    data_uri_byte = bytes("data:image/jpeg;base64,",
                          encoding='utf-8') + img_base64
    data_uri_string = data_uri_byte.decode('utf-8')
    return data_uri_string


def draw_box(img: Image.Image, lt_corner: Tuple[int], rb_corner: Tuple[int], title: str):
    draw = ImageDraw.Draw(img)
    draw.rectangle([lt_corner, rb_corner], outline="red", width=2)
    draw.text(lt_corner, title, font=ImageFont.truetype(
        "app/font/RobotoMono-Bold.ttf", size=16))
    return img
