FROM python:3.10.4-slim-buster
RUN pip install --upgrade pip
ENV PYTHONUNBUFFERED 1
RUN mkdir /book_explorer
WORKDIR /book_explorer
COPY requirements.txt /book_explorer/
RUN pip install -r requirements.txt
COPY . /book_explorer/
RUN python manage.py migrate
EXPOSE 8000
