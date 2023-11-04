FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
COPY ./datalab_entrypoint-0.1.tar.gz /code/datalab_entrypoint-0.1.tar.gz

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
RUN pip install datalab_entrypoint-0.1.tar.gz

COPY ./app /code/app
COPY ./functions /code/functions
RUN pip install -r /code/functions/requirements.txt

CMD ["python", "app/main.py"]
