import os
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]
connection_pool = pool.SimpleConnectionPool(1, 10, DATABASE_URL)

def get_conn():
    return connection_pool.getconn()

def release_conn(conn):
    connection_pool.putconn(conn)

def save_font(font_name: str):
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fonts (font_name)
            VALUES (%s)
            ON CONFLICT (font_name) DO NOTHING
        """, (font_name,))
        conn.commit()
        release_conn(conn)
        print(f"บันทึก {font_name} สำเร็จ")
    except Exception as e:
        print(f"error: {e}")
        raise
    