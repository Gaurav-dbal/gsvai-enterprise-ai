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

        # Add new columns to EMAIL if they do not exist
        cursor.execute("SELECT column_name FROM user_tab_cols WHERE table_name = 'EMAIL'")
        existing_cols = {row[0].upper() for row in cursor.fetchall()}

        new_columns = [
            ("ROUTED_AGENT", "VARCHAR2(100)"),
            ("ROUTING_ACTION", "VARCHAR2(100)"),
            ("SUGGESTED_REPLY", "CLOB"),
            ("RAG_SOURCES", "CLOB"),
            ("TRACE_DATA", "CLOB"),
            ("ERROR_MESSAGE", "CLOB"),
            ("REPLY_TEXT", "CLOB"),
            ("REPLY_SENT_AT", "TIMESTAMP"),
        ]

        for col_name, col_type in new_columns:
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE EMAIL ADD ({col_name} {col_type})")
                    print(f"SUCCESS: Added column {col_name} to EMAIL.")
                except Exception as e:
                    if "ORA-01430" in str(e):
                        print(f"INFO: Column {col_name} already exists.")
                    else:
                        print(f"WARNING: Could not add {col_name}: {e}")

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