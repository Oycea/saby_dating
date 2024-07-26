import psycopg2
import asyncpg


def get_database_connection():
    try:
        conn = psycopg2.connect(user='postgres', password='1234', database='postgres', host='localhost')
        print('Connection opened')
        return conn
    except:
        print('Can`t establish connection to database')


# async def get_database_connection():
#     return asyncpg.connect(user='postgres', password='Grigory333', database='postgres', host='localhost')