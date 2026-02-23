FROM python:3.11-slim-trixie as python-base

RUN apt update && apt install -yq gcc libpq-dev && rm -rf /etc/apk/cache

FROM python-base as production
WORKDIR /usr/src/app

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY ./wakatime_tracker /usr/src/app/wakatime_tracker
