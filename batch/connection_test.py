import os

import psycopg
from dotenv import load_dotenv


load_dotenv()


def main():
    connection = psycopg.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )

    with connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), version();")
            database, version = cursor.fetchone()

            print(f"Database: {database}")
            print(f"PostgreSQL: {version}")

    connection.close()


if __name__ == "__main__":
    main()