import psycopg2
from app.db.connection import get_db

conn = next(get_db())
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'chat_messages'")
print(cur.fetchall())
