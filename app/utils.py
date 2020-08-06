import base64
from PIL.Image import Image
from io import BytesIO


def image_to_data_uri(img: Image):
    ''' Convert PILLOW image to data URI '''
    buffered = BytesIO()
    img.save(buffered, 'JPEG')
    img_base64 = base64.b64encode(buffered.getvalue())
    data_uri_byte = bytes("data:image/jpeg;base64,",
                          encoding='utf-8') + img_base64
    data_uri_string = data_uri_byte.decode('utf-8')
    return data_uri_string
