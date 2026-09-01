import json
from services.oracle_db_service import get_connection


def table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM user_tables
        WHERE table_name = :table_name
        """,
        {"table_name": table_name.upper()},
    )
    return cursor.fetchone()[0] > 0


def column_exists(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM user_tab_cols
        WHERE table_name = :table_name
          AND column_name = :column_name
        """,
        {
            "table_name": table_name.upper(),
            "column_name": column_name.upper(),
        },
    )
    return cursor.fetchone()[0] > 0


def seed_default_roles_and_users(cursor):
    """Seed system roles and initial default users if not present."""
    default_roles = [
        (
            "ADMIN",
            "Full enterprise platform administrator with full access to configuration, connections, users, and workflows.",
            json.dumps([
                "USER_VIEW", "USER_MANAGE",
                "ROLE_VIEW", "ROLE_MANAGE",
                "FUSION_CONNECTION_VIEW", "FUSION_CONNECTION_CREATE", "FUSION_CONNECTION_EDIT", "FUSION_CONNECTION_TEST", "FUSION_CONNECTION_DISABLE",
                "INVOICE_VIEW", "INVOICE_UPLOAD", "INVOICE_REVIEW", "INVOICE_EDIT", "INVOICE_APPROVE", "INVOICE_REJECT",
                "FUSION_MAPPING_VIEW", "FUSION_MAPPING_EDIT",
                "FUSION_SUBMIT",
                "AUDIT_VIEW"
            ]),
            1,
        ),
        (
            "USER",
            "Standard business user with access to AI Workspace and invoice viewing/upload.",
            json.dumps([
                "INVOICE_VIEW", "INVOICE_UPLOAD", "INVOICE_REVIEW",
                "FUSION_CONNECTION_VIEW", "FUSION_MAPPING_VIEW"
            ]),
            1,
        ),
        (
            "INVOICE_REVIEWER",
            "Accounts Payable Specialist focused on reviewing and correcting extracted invoice fields.",
            json.dumps([
                "INVOICE_VIEW", "INVOICE_UPLOAD", "INVOICE_REVIEW", "INVOICE_EDIT",
                "FUSION_CONNECTION_VIEW", "FUSION_MAPPING_VIEW"
            ]),
            1,
        ),
        (
            "INVOICE_APPROVER",
            "Accounts Payable Manager authorized to approve/reject invoices and submit to Oracle Fusion ERP.",
            json.dumps([
                "INVOICE_VIEW", "INVOICE_REVIEW", "INVOICE_APPROVE", "INVOICE_REJECT",
                "FUSION_CONNECTION_VIEW", "FUSION_MAPPING_VIEW", "FUSION_SUBMIT", "AUDIT_VIEW"
            ]),
            1,
        ),
    ]

    for role_name, desc, perms_json, is_sys in default_roles:
        cursor.execute(
            "SELECT COUNT(*) FROM GSVAI_ROLES WHERE ROLE_NAME = :role_name",
            {"role_name": role_name},
        )
        if cursor.fetchone()[0] == 0:
            print(f"Seeding Role: {role_name}...")
            cursor.execute(
                """
                INSERT INTO GSVAI_ROLES (ROLE_NAME, DESCRIPTION, PERMISSIONS_JSON, IS_SYSTEM, CREATED_AT, UPDATED_AT)
                VALUES (:role_name, :description, :permissions_json, :is_system, SYSTIMESTAMP, SYSTIMESTAMP)
                """,
                {
                    "role_name": role_name,
                    "description": desc,
                    "permissions_json": perms_json,
                    "is_system": is_sys,
                },
            )

    default_users = [
        ("user_admin", "admin", "admin@enterprise.ai", "Enterprise Administrator", "ADMIN", "ACTIVE"),
        ("user_reviewer", "ap_reviewer", "reviewer@enterprise.ai", "Senior AP Reviewer", "INVOICE_REVIEWER", "ACTIVE"),
        ("user_approver", "ap_manager", "manager@enterprise.ai", "AP Approver & Controller", "INVOICE_APPROVER", "ACTIVE"),
        ("user_standard", "user1", "user1@enterprise.ai", "Standard Business User", "USER", "ACTIVE"),
    ]

    for user_id, uname, email, fname, role, status in default_users:
        cursor.execute(
            "SELECT COUNT(*) FROM GSVAI_USERS WHERE USER_ID = :user_id OR USERNAME = :username",
            {"user_id": user_id, "username": uname},
        )
        if cursor.fetchone()[0] == 0:
            print(f"Seeding User: {uname} ({role})...")
            cursor.execute(
                """
                INSERT INTO GSVAI_USERS (USER_ID, USERNAME, EMAIL, FULL_NAME, ROLE, STATUS, CREATED_AT, UPDATED_AT)
                VALUES (:user_id, :username, :email, :full_name, :role, :status, SYSTIMESTAMP, SYSTIMESTAMP)
                """,
                {
                    "user_id": user_id,
                    "username": uname,
                    "email": email,
                    "full_name": fname,
                    "role": role,
                    "status": status,
                },
            )


def main():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # =====================================================
        # 1. GSVAI_INVOICES
        # =====================================================
        if not table_exists(cursor, "GSVAI_INVOICES"):
            print("Creating GSVAI_INVOICES...")
            cursor.execute(
                """
                CREATE TABLE GSVAI_INVOICES (
                    INVOICE_ID        NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    DOCUMENT_NAME     VARCHAR2(500) NOT NULL,
                    VENDOR_NAME       VARCHAR2(500),
                    INVOICE_NUMBER    VARCHAR2(200),
                    INVOICE_DATE      DATE,
                    DUE_DATE          DATE,
                    PO_NUMBER         VARCHAR2(200),
                    CURRENCY          VARCHAR2(20),
                    SUBTOTAL          NUMBER(18,2),
                    TAX_AMOUNT        NUMBER(18,2),
                    TOTAL_AMOUNT      NUMBER(18,2),
                    PAYMENT_TERMS     VARCHAR2(1000),
                    STATUS            VARCHAR2(50) DEFAULT 'REVIEW_REQUIRED',
                    VALIDATION_STATUS VARCHAR2(50) DEFAULT 'PENDING',
                    OCI_JOB_ID        VARCHAR2(255),
                    RAW_RESULT        CLOB,
                    ORIGINAL_DATA     CLOB,
                    REVIEWED_BY       VARCHAR2(255),
                    REVIEWED_AT       TIMESTAMP(6),
                    REVIEW_COMMENTS   VARCHAR2(2000),
                    FUSION_INVOICE_ID VARCHAR2(255),
                    FUSION_STATUS     VARCHAR2(100),
                    FUSION_SUBMITTED_AT TIMESTAMP(6),
                    FUSION_CONNECTION_ID NUMBER,
                    CREATED_AT        TIMESTAMP(6) DEFAULT SYSTIMESTAMP
                )
                """
            )
            print("GSVAI_INVOICES created.")
        else:
            print("GSVAI_INVOICES exists. Checking columns...")
            if not column_exists(cursor, "GSVAI_INVOICES", "FUSION_CONNECTION_ID"):
                print("Adding FUSION_CONNECTION_ID to GSVAI_INVOICES...")
                cursor.execute("ALTER TABLE GSVAI_INVOICES ADD (FUSION_CONNECTION_ID NUMBER)")

        # =====================================================
        # 2. GSVAI_INVOICE_LINES
        # =====================================================
        if not table_exists(cursor, "GSVAI_INVOICE_LINES"):
            print("Creating GSVAI_INVOICE_LINES...")
            cursor.execute(
                """
                CREATE TABLE GSVAI_INVOICE_LINES (
                    LINE_ID        NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    INVOICE_ID     NUMBER NOT NULL,
                    LINE_NUMBER    NUMBER,
                    DESCRIPTION    VARCHAR2(1000),
                    ITEM_NUMBER    VARCHAR2(200),
                    QUANTITY       NUMBER(18,4),
                    UNIT_PRICE     NUMBER(18,4),
                    TAX_AMOUNT     NUMBER(18,2),
                    LINE_AMOUNT    NUMBER(18,2),
                    CREATED_AT     TIMESTAMP(6) DEFAULT SYSTIMESTAMP,

                    CONSTRAINT FK_GSVAI_INVOICE_LINES
                        FOREIGN KEY (INVOICE_ID)
                        REFERENCES GSVAI_INVOICES(INVOICE_ID)
                )
                """
            )
            print("GSVAI_INVOICE_LINES created.")

        # =====================================================
        # 3. GSVAI_FUSION_CONNECTIONS
        # =====================================================
        if not table_exists(cursor, "GSVAI_FUSION_CONNECTIONS"):
            print("Creating GSVAI_FUSION_CONNECTIONS...")
            cursor.execute(
                """
                CREATE TABLE GSVAI_FUSION_CONNECTIONS (
                    CONNECTION_ID       NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    CONNECTION_NAME     VARCHAR2(255) NOT NULL UNIQUE,
                    BASE_URL            VARCHAR2(1000) NOT NULL,
                    ENVIRONMENT         VARCHAR2(50) NOT NULL,
                    AUTHENTICATION_TYPE VARCHAR2(50) DEFAULT 'BASIC',
                    USERNAME            VARCHAR2(255),
                    PASSWORD_SECRET     VARCHAR2(1000),
                    BUSINESS_UNIT       VARCHAR2(255),
                    DEFAULT_CURRENCY    VARCHAR2(20) DEFAULT 'USD',
                    STATUS              VARCHAR2(50) DEFAULT 'NOT_TESTED',
                    IS_ACTIVE           NUMBER(1) DEFAULT 1,
                    LAST_TESTED_AT      TIMESTAMP(6),
                    LAST_TEST_MESSAGE   VARCHAR2(1000),
                    CREATED_AT          TIMESTAMP(6) DEFAULT SYSTIMESTAMP,
                    UPDATED_AT          TIMESTAMP(6) DEFAULT SYSTIMESTAMP
                )
                """
            )
            print("GSVAI_FUSION_CONNECTIONS created.")
        else:
            print("GSVAI_FUSION_CONNECTIONS already exists.")

        # =====================================================
        # 4. GSVAI_FUSION_SUBMISSIONS
        # =====================================================
        if not table_exists(cursor, "GSVAI_FUSION_SUBMISSIONS"):
            print("Creating GSVAI_FUSION_SUBMISSIONS...")
            cursor.execute(
                """
                CREATE TABLE GSVAI_FUSION_SUBMISSIONS (
                    SUBMISSION_ID        NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    INVOICE_ID           NUMBER NOT NULL,
                    CONNECTION_ID        NUMBER,
                    FUSION_INVOICE_ID    VARCHAR2(255),
                    STATUS               VARCHAR2(100) NOT NULL,
                    ENVIRONMENT          VARCHAR2(50),
                    REQUEST_PAYLOAD      CLOB,
                    RESPONSE_PAYLOAD     CLOB,
                    ERROR_MESSAGE        VARCHAR2(2000),
                    SUBMITTED_AT         TIMESTAMP(6) DEFAULT SYSTIMESTAMP,
                    UPDATED_AT           TIMESTAMP(6) DEFAULT SYSTIMESTAMP,

                    CONSTRAINT FK_GSVAI_FUSION_SUBMISSIONS
                        FOREIGN KEY (INVOICE_ID)
                        REFERENCES GSVAI_INVOICES(INVOICE_ID)
                )
                """
            )
            print("GSVAI_FUSION_SUBMISSIONS created.")
        else:
            print("GSVAI_FUSION_SUBMISSIONS exists. Checking columns...")
            if not column_exists(cursor, "GSVAI_FUSION_SUBMISSIONS", "CONNECTION_ID"):
                print("Adding CONNECTION_ID to GSVAI_FUSION_SUBMISSIONS...")
                cursor.execute("ALTER TABLE GSVAI_FUSION_SUBMISSIONS ADD (CONNECTION_ID NUMBER)")
            if not column_exists(cursor, "GSVAI_FUSION_SUBMISSIONS", "ENVIRONMENT"):
                print("Adding ENVIRONMENT to GSVAI_FUSION_SUBMISSIONS...")
                cursor.execute("ALTER TABLE GSVAI_FUSION_SUBMISSIONS ADD (ENVIRONMENT VARCHAR2(50))")

        # =====================================================
        # 5. GSVAI_INVOICE_FIELD_MAPPINGS
        # =====================================================
        if not table_exists(cursor, "GSVAI_INVOICE_FIELD_MAPPINGS"):
            print("Creating GSVAI_INVOICE_FIELD_MAPPINGS...")
            cursor.execute(
                """
                CREATE TABLE GSVAI_INVOICE_FIELD_MAPPINGS (
                    MAPPING_ID       NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    INVOICE_ID       NUMBER,
                    CONNECTION_ID    NUMBER,
                    SOURCE_FIELD     VARCHAR2(100) NOT NULL,
                    SOURCE_SECTION   VARCHAR2(50) NOT NULL,
                    TARGET_FIELD     VARCHAR2(100) NOT NULL,
                    TARGET_SECTION   VARCHAR2(50) NOT NULL,
                    TRANSFORMATION   VARCHAR2(100),
                    IS_ACTIVE        NUMBER(1) DEFAULT 1,
                    CREATED_AT       TIMESTAMP(6) DEFAULT SYSTIMESTAMP,

                    CONSTRAINT FK_GSVAI_INVOICE_MAP_INV
                        FOREIGN KEY (INVOICE_ID)
                        REFERENCES GSVAI_INVOICES(INVOICE_ID)
                )
                """
            )
            print("GSVAI_INVOICE_FIELD_MAPPINGS created.")
        else:
            print("GSVAI_INVOICE_FIELD_MAPPINGS exists. Checking columns...")
            if not column_exists(cursor, "GSVAI_INVOICE_FIELD_MAPPINGS", "CONNECTION_ID"):
                print("Adding CONNECTION_ID to GSVAI_INVOICE_FIELD_MAPPINGS...")
                cursor.execute("ALTER TABLE GSVAI_INVOICE_FIELD_MAPPINGS ADD (CONNECTION_ID NUMBER)")

        # =====================================================
        # 6. GSVAI_USERS & GSVAI_ROLES
        # =====================================================
        if not table_exists(cursor, "GSVAI_ROLES"):
            print("Creating GSVAI_ROLES...")
            cursor.execute(
                """
                CREATE TABLE GSVAI_ROLES (
                    ROLE_NAME         VARCHAR2(50) PRIMARY KEY,
                    DESCRIPTION       VARCHAR2(500),
                    PERMISSIONS_JSON  CLOB,
                    IS_SYSTEM         NUMBER(1) DEFAULT 1,
                    CREATED_AT        TIMESTAMP(6) DEFAULT SYSTIMESTAMP,
                    UPDATED_AT        TIMESTAMP(6) DEFAULT SYSTIMESTAMP
                )
                """
            )
            print("GSVAI_ROLES created.")

        if not table_exists(cursor, "GSVAI_USERS"):
            print("Creating GSVAI_USERS...")
            cursor.execute(
                """
                CREATE TABLE GSVAI_USERS (
                    USER_ID           VARCHAR2(100) PRIMARY KEY,
                    USERNAME          VARCHAR2(255) NOT NULL UNIQUE,
                    EMAIL             VARCHAR2(255) NOT NULL,
                    FULL_NAME         VARCHAR2(255),
                    ROLE              VARCHAR2(50) NOT NULL,
                    STATUS            VARCHAR2(50) DEFAULT 'ACTIVE',
                    CREATED_AT        TIMESTAMP(6) DEFAULT SYSTIMESTAMP,
                    UPDATED_AT        TIMESTAMP(6) DEFAULT SYSTIMESTAMP,

                    CONSTRAINT FK_GSVAI_USERS_ROLE
                        FOREIGN KEY (ROLE)
                        REFERENCES GSVAI_ROLES(ROLE_NAME)
                )
                """
            )
            print("GSVAI_USERS created.")

        # =====================================================
        # 7. GSVAI_AUDIT_LOGS
        # =====================================================
        if not table_exists(cursor, "GSVAI_AUDIT_LOGS"):
            print("Creating GSVAI_AUDIT_LOGS...")
            cursor.execute(
                """
                CREATE TABLE GSVAI_AUDIT_LOGS (
                    LOG_ID           NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    USER_ID          VARCHAR2(100),
                    ACTION           VARCHAR2(100) NOT NULL,
                    RESOURCE_TYPE    VARCHAR2(100),
                    RESOURCE_ID      VARCHAR2(255),
                    DETAILS_JSON     CLOB,
                    STATUS           VARCHAR2(50),
                    CREATED_AT       TIMESTAMP(6) DEFAULT SYSTIMESTAMP
                )
                """
            )
            print("GSVAI_AUDIT_LOGS created.")

        # =====================================================
        # 8. GSVAI_DATABASE_CONNECTIONS
        # =====================================================
        if not table_exists(cursor, "GSVAI_DATABASE_CONNECTIONS"):
            print("Creating GSVAI_DATABASE_CONNECTIONS...")
            cursor.execute(
                """
                CREATE TABLE GSVAI_DATABASE_CONNECTIONS (
                    CONNECTION_ID       NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    CONNECTION_NAME     VARCHAR2(255) NOT NULL UNIQUE,
                    DATABASE_TYPE       VARCHAR2(50) DEFAULT 'ORACLE',
                    HOST                VARCHAR2(255),
                    PORT                NUMBER DEFAULT 1521,
                    SERVICE_NAME        VARCHAR2(255),
                    SCHEMA_NAME         VARCHAR2(255),
                    USERNAME            VARCHAR2(255),
                    PASSWORD_SECRET     VARCHAR2(1000),
                    STATUS              VARCHAR2(50) DEFAULT 'CONNECTED',
                    IS_ACTIVE           NUMBER(1) DEFAULT 1,
                    IS_DEFAULT          NUMBER(1) DEFAULT 0,
                    LAST_TESTED_AT      TIMESTAMP(6),
                    LAST_TEST_MESSAGE   VARCHAR2(1000),
                    CREATED_AT          TIMESTAMP(6) DEFAULT SYSTIMESTAMP,
                    UPDATED_AT          TIMESTAMP(6) DEFAULT SYSTIMESTAMP
                )
                """
            )
            print("GSVAI_DATABASE_CONNECTIONS created.")
        else:
            print("GSVAI_DATABASE_CONNECTIONS already exists.")

        # Seed default database connection if table is empty
        cursor.execute("SELECT COUNT(*) FROM GSVAI_DATABASE_CONNECTIONS")
        if cursor.fetchone()[0] == 0:
            print("Seeding default GSVAI Enterprise Database connection...")
            cursor.execute(
                """
                INSERT INTO GSVAI_DATABASE_CONNECTIONS (
                    CONNECTION_NAME, DATABASE_TYPE, SCHEMA_NAME, USERNAME, STATUS, IS_ACTIVE, IS_DEFAULT, LAST_TESTED_AT, LAST_TEST_MESSAGE, CREATED_AT, UPDATED_AT
                ) VALUES (
                    'GSVAI Enterprise Database (Oracle Autonomous DB)', 'ORACLE', 'ADMIN', 'ADMIN', 'CONNECTED', 1, 1, SYSTIMESTAMP, 'Primary Autonomous Database active and connected.', SYSTIMESTAMP, SYSTIMESTAMP
                )
                """
            )

        # Seed roles & users
        seed_default_roles_and_users(cursor)

        conn.commit()

        print()
        print("=" * 60)
        print("DATABASE SCHEMA INITIALIZATION & SEEDING COMPLETE")
        print("=" * 60)

        cursor.execute(
            """
            SELECT table_name
            FROM user_tables
            WHERE table_name IN (
                'GSVAI_INVOICES',
                'GSVAI_INVOICE_LINES',
                'GSVAI_FUSION_CONNECTIONS',
                'GSVAI_FUSION_SUBMISSIONS',
                'GSVAI_INVOICE_FIELD_MAPPINGS',
                'GSVAI_USERS',
                'GSVAI_ROLES',
                'GSVAI_AUDIT_LOGS'
            )
            ORDER BY table_name
            """
        )
        print("Active Database Tables:")
        for row in cursor.fetchall():
            print(" -", row[0])

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()