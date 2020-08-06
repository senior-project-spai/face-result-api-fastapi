import os

MYSQL_CONFIG = {
    "host": os.getenv('MYSQL_HOST'),
    "port": int(os.getenv('MYSQL_PORT')),
    "user": os.getenv('MYSQL_USER'),
    "passwd": os.getenv('MYSQL_PASSWORD'),
    "db": os.getenv('MYSQL_DB'),
}

MYSQL_CONFIG_FADE = {
    **MYSQL_CONFIG,
    "db": 'face_recognition'
}
