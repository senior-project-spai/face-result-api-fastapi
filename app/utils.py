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

    # text_size according to the size of box
    text_size = int((rb_corner[1] - lt_corner[1]) * 0.04 * 4)

    draw.text(lt_corner, title, font=ImageFont.truetype(
        "app/font/RobotoMono-Bold.ttf", size=text_size))
    return img

def find_intersect_area(r0, r1):
    ''' find intersection area, return None if they are not intersect'''
    left = max(r1["left"], r0["left"])
    right = min(r1["right"], r0["right"])
    bottom = min(r1["bottom"], r0["bottom"])
    top = max(r1["top"], r0["top"])

    if (left < right) and (top < bottom):
        return (right - left) * (bottom - top)
    else:
        return None