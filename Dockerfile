FROM python:3.8-alpine

#MAINTAINER Alex Mattson "alex.mattson@gmail.com"
# test

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

RUN addgroup -S appuser && adduser -S -G appuser appuser
USER appuser

ENTRYPOINT [ "python" ]

CMD [ "app.py" ]