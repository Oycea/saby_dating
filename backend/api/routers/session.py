import psycopg2

from config import *


def open_conn():
    try:
        connection = psycopg2.connect(
            dbname=POSTGRES_NAME,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT
        )
        print('Connection opened')
        return connection
    except:
        print('Can`t establish connection to database')
