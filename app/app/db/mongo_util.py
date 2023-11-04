import logging

from mongoengine import connect, disconnect

from app.core.config import settings


MONGODB_CONNECTION_NAME = "datalab_db"


def connect_mongodb():
    """
        db=None,
        host=None,
        port=None,
        username=None,
        password=None,
        authentication_source=None,
    :return:
    """
    logging.info("connect mongodb")
    connect(
        db=settings.MONGODB_DB,
        host=settings.MONGODB_SERVER,
        port=settings.MONGODB_PORT,
        username=settings.MONGODB_USER,
        password=settings.MONGODB_PASSWORD,
        authentication_source=settings.MONGODB_AUTH_SOURCE
    )


def disconnect_mongodb():
    logging.info("disconnect mongodb")
    disconnect()
