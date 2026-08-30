import os
# pyrefly: ignore [missing-import]
import oracledb
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_WALLET_PASSWORD = os.getenv("DB_WALLET_PASSWORD")
DB_WALLET_DIR = os.getenv("DB_WALLET_DIR")
DB_DSN = os.getenv("DB_DSN")

print("=" * 60)
print("GSVAI - ORACLE DATABASE CONNECTION TEST")
print("=" * 60)

print("\nLoading database configuration...")

try:
    connection = oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        config_dir=DB_WALLET_DIR,
        wallet_location=DB_WALLET_DIR,
        wallet_password=DB_WALLET_PASSWORD
    )

    print("Database connection successful!")

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            SYS_CONTEXT('USERENV', 'DB_NAME'),
            SYS_CONTEXT('USERENV', 'SERVICE_NAME'),
            USER
        FROM dual
    """)

    db_name, service_name, username = cursor.fetchone()

    print("\nDatabase Information")
    print("-" * 40)
    print("Database   :", db_name)
    print("Service    :", service_name)
    print("User       :", username)

    cursor.close()
    connection.close()

    print("\n" + "=" * 60)
    print("GSVAI DATABASE CONNECTION SUCCESSFUL")
    print("=" * 60)

except Exception as e:

    print("\n" + "=" * 60)
    print("DATABASE CONNECTION FAILED")
    print("=" * 60)

    print("\nError:")
    print(e)