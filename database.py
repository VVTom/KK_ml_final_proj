import os

import psycopg2
from dotenv import load_dotenv



load_dotenv()


def postgres_connection():
    """Устанавливает и возвращает соединение с PostgreSQL."""

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL не найден в .env")

    try:
        conn = psycopg2.connect(database_url)

    except Exception as e:
        print("❌ Ошибка при подключении к базе данных.")
        raise e

    conn.autocommit = True

    return conn


# test
# conn = postgres_connection()

# print(conn)
# print("Подключение успешно")

# conn.close()
