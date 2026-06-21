import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Generator

def get_db_connection():
    return psycopg2.connect(
        dbname="ai_pm_copilot",
        user="postgres",
        password="postgres",
        host="localhost",
        port="5432"
    )

def get_db() -> Generator:
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
