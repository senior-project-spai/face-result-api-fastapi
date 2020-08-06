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

WORKDIR /app

# Install python package
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ./app /app/app
