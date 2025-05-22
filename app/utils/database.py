import mysql.connector
from mysql.connector import Error

def get_db_connection():
    try:
        return mysql.connector.connect(
            host='127.0.0.1',  # Replace with your MySQL host
            user='root',  # Replace with your MySQL username
            password='root',  # Replace with your MySQL password
            database='TriathlonForge',  # Replace with your database name
            port=8889
        )
    except Error as e:
        print(f"Database connection Error: {e}")
        return None
