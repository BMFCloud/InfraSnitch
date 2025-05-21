import pyodbc
import logging
import time

def get_connection(retries=3, delay=5):
    for attempt in range(1, retries + 1):
        try:
            print("\n🔐 SQL Server Connection Setup")
            server = input("Enter SQL Server address (e.g., localhost or 10.0.0.1\\SQLINSTANCE): ").strip()
            database = input("Enter database name [default: master]: ").strip() or "master"

            driver = '{ODBC Driver 17 for SQL Server}'
            connection_string = (
                f"DRIVER={driver};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"Trusted_Connection=yes;"
            )

            conn = pyodbc.connect(connection_string)
            logging.info("✅ Database connection established.")
            return conn, server

        except pyodbc.Error as e:
            logging.warning(f"❌ Attempt {attempt} failed: {e}")
            if attempt < retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logging.error("❌ Max retries reached. Connection failed.")
                raise


