import psycopg2
import psycopg2.extras
import logging

from config import POSTGRES_NAME, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT

logger = logging.getLogger(__name__)


def open_conn():
    """
    Открывает соединение с базой данных

    :return: Соединение с БД
    :raises: Ошибка при подключении к БД
    """
    try:
        connection = psycopg2.connect(
            dbname=POSTGRES_NAME,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT
        )
        return connection
    except psycopg2.Error as e:
        logger.error(f"Невозможно подключиться к БД: {e}")
        raise e
