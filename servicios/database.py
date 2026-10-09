import os
import mysql.connector.pooling


db_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="uruturn_pool",
    pool_size=10,
    host=os.getenv("DB_HOST", "db"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME", "uruturn_db"),
    user=os.getenv("DB_USER", "uruturn_user"),
    password=os.getenv("DB_PASSWORD", "uruturn_password"),
)


def get_db():
    """Inyección de dependencia para endpoints."""
    conn = db_pool.get_connection()
    try:
        yield conn
    finally:
        conn.close()
