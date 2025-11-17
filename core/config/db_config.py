import mysql.connector
from mysql.connector import Error

def test_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="admin",
            database="records"
        )

        if connection.is_connected():
            print("✅ Database Connection Established Successfully!")
            return True

    except Error as e:
        print("❌ Database Connection Failed!")
        print("Error:", e)
        return False

    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()
