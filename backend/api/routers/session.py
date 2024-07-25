import psycopg2

conn_params = {
    'dbname': 'sabytin',
    'user': 'sabytin_user',
    'password': 'uhmWgCHZsBMaHisGHJbKagzN8t6irG7k',
    'host': 'dpg-cqgk6j2j1k6c73dfacq0-a.frankfurt-postgres.render.com',
    'port': '5432'
}


def open_conn():
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        print('Connection opened')
        return cursor, conn
    except:
        print('Can`t establish connection to database')


def close_conn(cursor, conn):
    try:
        cursor.close()
        conn.close()
        print('Connection closed')
    except:
        print('Can`t close connection')
