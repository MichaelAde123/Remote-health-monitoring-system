import mysql.connector
from mysql.connector import Error

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="",  # Replace with your actual MySQL password
            database="project4db",
            port=3306
        )
        return conn
    except Error as e:
        print(f"Database connection failed: {e}")
        return None

def query_db(query, args=(), one=False):
    conn = get_db_connection()
    result = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, args)
            result = cursor.fetchone() if one else cursor.fetchall()
        except Error as e:
            print(f"Query failed: {e}")
        finally:
            cursor.close()
            conn.close()
    return result

def execute_db(query, args=()):
    conn = get_db_connection()
    success = False
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query, args)
            conn.commit()
            success = True
        except Error as e:
            print(f"Execution failed: {e}")
        finally:
            cursor.close()
            conn.close()
    return success
