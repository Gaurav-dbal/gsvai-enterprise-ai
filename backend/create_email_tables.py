from services.oracle_db_service import get_connection


def create_tables():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # ---------------------------------------------------------
        # 1. EMAIL TABLE
        # ---------------------------------------------------------
        create_email_table = """
        CREATE TABLE EMAIL (
            EMAIL_ID            VARCHAR2(50) PRIMARY KEY,
            MESSAGE_ID          VARCHAR2(500),
            SENDER_EMAIL        VARCHAR2(320) NOT NULL,
            RECIPIENT_EMAIL     VARCHAR2(320),
            CC_EMAIL            VARCHAR2(2000),
            SUBJECT             VARCHAR2(1000),
            BODY                CLOB,
            RECEIVED_DATE       TIMESTAMP,
            STATUS              VARCHAR2(30) DEFAULT 'RECEIVED' NOT NULL,
            CREATED_DATE        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
            UPDATED_DATE        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
        )
        """

        # ---------------------------------------------------------
        # 2. EMAIL_ANALYSIS TABLE
        # ---------------------------------------------------------
        create_email_analysis_table = """
        CREATE TABLE EMAIL_ANALYSIS (
            ANALYSIS_ID         VARCHAR2(50) PRIMARY KEY,
            EMAIL_ID            VARCHAR2(50) NOT NULL,
            EMAIL_TYPE          VARCHAR2(50),
            PRIORITY            VARCHAR2(20),
            CONFIDENCE          NUMBER(5,4),
            EXTRACTED_DATA      CLOB,
            RECOMMENDED_ACTION  VARCHAR2(100),
            REASONING_SUMMARY   CLOB,
            ANALYZED_DATE       TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,

            CONSTRAINT FK_EMAIL_ANALYSIS
                FOREIGN KEY (EMAIL_ID)
                REFERENCES EMAIL(EMAIL_ID)
        )
        """

        # Create EMAIL
        try:
            cursor.execute(create_email_table)
            print("SUCCESS: EMAIL table created.")

        except Exception as e:
            if "ORA-00955" in str(e):
                print("INFO: EMAIL table already exists.")
            else:
                raise

        # Create EMAIL_ANALYSIS
        try:
            cursor.execute(create_email_analysis_table)
            print("SUCCESS: EMAIL_ANALYSIS table created.")

        except Exception as e:
            if "ORA-00955" in str(e):
                print("INFO: EMAIL_ANALYSIS table already exists.")
            else:
                raise

        connection.commit()

        print("\nEmail automation tables are ready.")

    except Exception as e:
        connection.rollback()
        print(f"ERROR: {e}")
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    create_tables()