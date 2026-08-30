from services.oracle_db_service import get_connection


def main():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        print("=" * 60)
        print("GSVAI INVOICE DATA CLEANUP")
        print("=" * 60)

        # Delete child records first because of the foreign key
        print("Deleting invoice line items...")
        cursor.execute("DELETE FROM GSVAI_INVOICE_LINES")
        lines_deleted = cursor.rowcount
        print(f"Invoice lines deleted: {lines_deleted}")

        # Delete parent invoice records
        print("Deleting invoices...")
        cursor.execute("DELETE FROM GSVAI_INVOICES")
        invoices_deleted = cursor.rowcount
        print(f"Invoices deleted: {invoices_deleted}")

        conn.commit()

        # Verify
        cursor.execute("SELECT COUNT(*) FROM GSVAI_INVOICES")
        invoice_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM GSVAI_INVOICE_LINES")
        line_count = cursor.fetchone()[0]

        print()
        print("=" * 60)
        print("CLEANUP COMPLETE")
        print("=" * 60)
        print(f"GSVAI_INVOICES      : {invoice_count}")
        print(f"GSVAI_INVOICE_LINES : {line_count}")
        print("=" * 60)

    except Exception as e:
        conn.rollback()
        print()
        print("ERROR - ROLLBACK PERFORMED")
        print(str(e))
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()