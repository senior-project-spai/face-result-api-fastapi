FROM tiangolo/uvicorn-gunicorn:python3.7-alpine3.8

LABEL maintainer="Rawit Panjaroen<check.rawit@gmail.com>"

RUN apk --no-cache add build-base \
                       jpeg-dev \
                       zlib-dev \
                       freetype-dev \
                       lcms2-dev \
                       openjpeg-dev \
                       tiff-dev \
                       tk-dev \
                       tcl-dev \
                       harfbuzz-dev \
                       fribidi-dev

COPY ./app /app

RUN pip install -r /app/requirements.txt