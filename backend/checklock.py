from services.oracle_db_service import get_connection


def main():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        print("=" * 70)
        print("GSVAI ORACLE DATABASE LOCK CHECK")
        print("=" * 70)

        # ---------------------------------------------------------
        # 1. Check current session
        # ---------------------------------------------------------
        print("\nCURRENT SESSION")
        print("-" * 70)

        cursor.execute("""
            SELECT
                SYS_CONTEXT('USERENV', 'SID') AS SID,
                SYS_CONTEXT('USERENV', 'SESSION_USER') AS SESSION_USER,
                SYS_CONTEXT('USERENV', 'INSTANCE_NAME') AS INSTANCE_NAME
            FROM dual
        """)

        for row in cursor.fetchall():
            print("SID           :", row[0])
            print("SESSION USER  :", row[1])
            print("INSTANCE      :", row[2])

        # ---------------------------------------------------------
        # 2. Check locks on invoice tables
        # ---------------------------------------------------------
        print("\nINVOICE TABLE LOCKS")
        print("-" * 70)

        cursor.execute("""
            SELECT
                lo.session_id,
                lo.oracle_username,
                lo.os_user_name,
                lo.locked_mode,
                o.object_name,
                o.object_type
            FROM v$locked_object lo
            JOIN all_objects o
                ON o.object_id = lo.object_id
            WHERE UPPER(o.object_name) IN (
                'GSVAI_INVOICES',
                'GSVAI_INVOICE_LINES'
            )
            ORDER BY o.object_name
        """)

        rows = cursor.fetchall()

        if not rows:
            print("No locks found on invoice tables.")
        else:
            for row in rows:
                print()
                print("Session ID     :", row[0])
                print("Oracle User    :", row[1])
                print("OS User        :", row[2])
                print("Locked Mode    :", row[3])
                print("Object         :", row[4])
                print("Object Type    :", row[5])

        # ---------------------------------------------------------
        # 3. Check active transactions
        # ---------------------------------------------------------
        print("\nACTIVE TRANSACTIONS")
        print("-" * 70)

        cursor.execute("""
            SELECT
                s.sid,
                s.serial#,
                s.username,
                s.status,
                s.machine,
                s.program,
                t.start_time
            FROM v$transaction t
            JOIN v$session s
                ON t.addr = s.taddr
            ORDER BY t.start_time
        """)

        rows = cursor.fetchall()

        if not rows:
            print("No active transactions found.")
        else:
            for row in rows:
                print()
                print("SID            :", row[0])
                print("SERIAL#        :", row[1])
                print("USERNAME       :", row[2])
                print("STATUS         :", row[3])
                print("MACHINE        :", row[4])
                print("PROGRAM        :", row[5])
                print("START TIME     :", row[6])

        # ---------------------------------------------------------
        # 4. Row counts
        # ---------------------------------------------------------
        print("\nCURRENT ROW COUNTS")
        print("-" * 70)

        cursor.execute("SELECT COUNT(*) FROM GSVAI_INVOICES")
        print("GSVAI_INVOICES      :", cursor.fetchone()[0])

        cursor.execute("SELECT COUNT(*) FROM GSVAI_INVOICE_LINES")
        print("GSVAI_INVOICE_LINES  :", cursor.fetchone()[0])

        print("\n" + "=" * 70)
        print("LOCK CHECK COMPLETE")
        print("=" * 70)

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()