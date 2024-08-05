import psycopg2
from backend.api.config import POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_DATABASE, POSTGRES_PORT


def get_database_connection():
    try:
        conn = psycopg2.connect(user=POSTGRES_USER, password=POSTGRES_PASSWORD,
                                database=POSTGRES_DATABASE, host=POSTGRES_HOST, port=POSTGRES_PORT)
        print('Connection opened')
        return conn
    except:
        print('Can`t establish connection to database')
