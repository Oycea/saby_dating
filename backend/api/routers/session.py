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
        print('Connection opened')
        return conn
    except:
        print('Can`t establish connection to database')
