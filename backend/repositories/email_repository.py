import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from services.oracle_db_service import get_connection


class EmailRepository:
    """Database operations for email automation."""

    def create_email(
        self,
        email_id: str,
        message_id: Optional[str],
        sender_email: str,
        recipient_email: Optional[str],
        cc_email: Optional[str],
        subject: Optional[str],
        body: Optional[str],
        received_date: Optional[datetime],
        status: str = "RECEIVED",
    ) -> None:
        """Insert an incoming email into EMAIL table."""
        connection = get_connection()
        cursor = connection.cursor()

        try:
            sql = """
                INSERT INTO EMAIL (
                    EMAIL_ID,
                    MESSAGE_ID,
                    SENDER_EMAIL,
                    RECIPIENT_EMAIL,
                    CC_EMAIL,
                    SUBJECT,
                    BODY,
                    RECEIVED_DATE,
                    STATUS
                )
                VALUES (
                    :email_id,
                    :message_id,
                    :sender_email,
                    :recipient_email,
                    :cc_email,
                    :subject,
                    :body,
                    :received_date,
                    :status
                )
            """

            cursor.execute(
                sql,
                {
                    "email_id": email_id,
                    "message_id": message_id,
                    "sender_email": sender_email,
                    "recipient_email": recipient_email,
                    "cc_email": cc_email,
                    "subject": subject,
                    "body": body,
                    "received_date": received_date,
                    "status": status,
                },
            )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            cursor.close()
            connection.close()

    def _row_to_dict(self, row: tuple) -> dict:
        """Helper to convert row tuple into dictionary."""
        def _read_lob(val):
            if val is None:
                return None
            if hasattr(val, "read"):
                return val.read()
            return str(val)

        def _parse_json(val):
            text = _read_lob(val)
            if not text:
                return None
            try:
                return json.loads(text)
            except Exception:
                return text

        return {
            "email_id": row[0],
            "message_id": row[1],
            "sender_email": row[2],
            "recipient_email": row[3],
            "cc_email": row[4],
            "subject": row[5],
            "body": _read_lob(row[6]),
            "received_date": row[7],
            "status": row[8],
            "routed_agent": row[9],
            "routing_action": row[10],
            "suggested_reply": _read_lob(row[11]),
            "rag_sources": _parse_json(row[12]),
            "trace_data": _parse_json(row[13]),
            "error_message": _read_lob(row[14]),
            "reply_text": _read_lob(row[15]),
            "reply_sent_at": row[16],
            "created_date": row[17],
            "updated_date": row[18],
        }

    def get_email(self, email_id: str) -> Optional[dict]:
        """Retrieve an email by EMAIL_ID."""
        connection = get_connection()
        cursor = connection.cursor()

        try:
            sql = """
                SELECT
                    EMAIL_ID,
                    MESSAGE_ID,
                    SENDER_EMAIL,
                    RECIPIENT_EMAIL,
                    CC_EMAIL,
                    SUBJECT,
                    BODY,
                    RECEIVED_DATE,
                    STATUS,
                    ROUTED_AGENT,
                    ROUTING_ACTION,
                    SUGGESTED_REPLY,
                    RAG_SOURCES,
                    TRACE_DATA,
                    ERROR_MESSAGE,
                    REPLY_TEXT,
                    REPLY_SENT_AT,
                    CREATED_DATE,
                    UPDATED_DATE
                FROM EMAIL
                WHERE EMAIL_ID = :email_id
            """

            cursor.execute(sql, {"email_id": email_id})
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_dict(row)

        finally:
            cursor.close()
            connection.close()

    def get_email_by_message_id(self, message_id: str) -> Optional[dict]:
        """Retrieve an email by Microsoft Graph MESSAGE_ID."""
        if not message_id:
            return None

        connection = get_connection()
        cursor = connection.cursor()

        try:
            sql = """
                SELECT
                    EMAIL_ID,
                    MESSAGE_ID,
                    SENDER_EMAIL,
                    RECIPIENT_EMAIL,
                    CC_EMAIL,
                    SUBJECT,
                    BODY,
                    RECEIVED_DATE,
                    STATUS,
                    ROUTED_AGENT,
                    ROUTING_ACTION,
                    SUGGESTED_REPLY,
                    RAG_SOURCES,
                    TRACE_DATA,
                    ERROR_MESSAGE,
                    REPLY_TEXT,
                    REPLY_SENT_AT,
                    CREATED_DATE,
                    UPDATED_DATE
                FROM EMAIL
                WHERE MESSAGE_ID = :message_id
                FETCH FIRST 1 ROW ONLY
            """

            cursor.execute(sql, {"message_id": message_id})
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_dict(row)

        finally:
            cursor.close()
            connection.close()

    def list_emails(self, limit: int = 100) -> List[dict]:
        """List all emails ordered by received date descending."""
        connection = get_connection()
        cursor = connection.cursor()

        try:
            sql = """
                SELECT
                    EMAIL_ID,
                    MESSAGE_ID,
                    SENDER_EMAIL,
                    RECIPIENT_EMAIL,
                    CC_EMAIL,
                    SUBJECT,
                    BODY,
                    RECEIVED_DATE,
                    STATUS,
                    ROUTED_AGENT,
                    ROUTING_ACTION,
                    SUGGESTED_REPLY,
                    RAG_SOURCES,
                    TRACE_DATA,
                    ERROR_MESSAGE,
                    REPLY_TEXT,
                    REPLY_SENT_AT,
                    CREATED_DATE,
                    UPDATED_DATE
                FROM EMAIL
                ORDER BY NVL(RECEIVED_DATE, CREATED_DATE) DESC, CREATED_DATE DESC
                FETCH FIRST :limit ROWS ONLY
            """

            cursor.execute(sql, {"limit": limit})
            rows = cursor.fetchall()

            return [self._row_to_dict(row) for row in rows]

        finally:
            cursor.close()
            connection.close()

    def update_email(self, email_id: str, **kwargs) -> None:
        """Dynamically update columns on an email record."""
        if not kwargs:
            return

        connection = get_connection()
        cursor = connection.cursor()

        try:
            set_clauses = []
            params = {"email_id": email_id}

            allowed_cols = {
                "message_id": "MESSAGE_ID",
                "status": "STATUS",
                "routed_agent": "ROUTED_AGENT",
                "routing_action": "ROUTING_ACTION",
                "suggested_reply": "SUGGESTED_REPLY",
                "rag_sources": "RAG_SOURCES",
                "trace_data": "TRACE_DATA",
                "error_message": "ERROR_MESSAGE",
                "reply_text": "REPLY_TEXT",
                "reply_sent_at": "REPLY_SENT_AT",
            }

            for key, val in kwargs.items():
                col = allowed_cols.get(key.lower())
                if col:
                    # If dict or list, serialize to JSON
                    if isinstance(val, (dict, list)):
                        val = json.dumps(val)
                    set_clauses.append(f"{col} = :{key}")
                    params[key] = val

            set_clauses.append("UPDATED_DATE = SYSTIMESTAMP")

            sql = f"""
                UPDATE EMAIL
                SET {", ".join(set_clauses)}
                WHERE EMAIL_ID = :email_id
            """

            cursor.execute(sql, params)
            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            cursor.close()
            connection.close()

    def get_email_counts(self) -> dict:
        """Returns aggregated telemetry metrics for Email Inbox."""
        connection = get_connection()
        cursor = connection.cursor()

        try:
            sql = """
                SELECT
                    COUNT(*) AS total_count,
                    NVL(SUM(CASE WHEN STATUS IN ('RECEIVED', 'UNREAD') THEN 1 ELSE 0 END), 0) AS unread_count,
                    NVL(SUM(CASE WHEN STATUS IN ('ANALYZED', 'ROUTED', 'PROCESSING', 'AWAITING_APPROVAL', 'APPROVED', 'REPLIED') THEN 1 ELSE 0 END), 0) AS processed_count,
                    NVL(SUM(CASE WHEN STATUS = 'AWAITING_APPROVAL' THEN 1 ELSE 0 END), 0) AS awaiting_approval_count,
                    NVL(SUM(CASE WHEN STATUS = 'REPLIED' THEN 1 ELSE 0 END), 0) AS replies_sent_count,
                    NVL(SUM(CASE WHEN STATUS IN ('AI_THROTTLED', 'FAILED') THEN 1 ELSE 0 END), 0) AS throttled_count
                FROM EMAIL
            """

            cursor.execute(sql)
            row = cursor.fetchone()

            if not row:
                return {
                    "total_count": 0,
                    "unread_count": 0,
                    "processed_count": 0,
                    "awaiting_approval_count": 0,
                    "replies_sent_count": 0,
                    "throttled_count": 0,
                }

            return {
                "total_count": int(row[0] or 0),
                "unread_count": int(row[1] or 0),
                "processed_count": int(row[2] or 0),
                "awaiting_approval_count": int(row[3] or 0),
                "replies_sent_count": int(row[4] or 0),
                "throttled_count": int(row[5] or 0),
            }

        finally:
            cursor.close()
            connection.close()