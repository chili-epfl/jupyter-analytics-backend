FROM python:3.11-alpine

RUN apk update && \
    apk add --no-cache postgresql-client && \
    apk add --no-cache htop 

WORKDIR /app

COPY . .
RUN pip install -r requirements.txt
RUN pip install --only-binary=:all: -r requirements-binary.txt

EXPOSE 5000

CMD gunicorn -k gevent -b 0.0.0.0:5000 -w 1 application
