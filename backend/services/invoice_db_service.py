import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from services.oracle_db_service import get_connection


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    text = str(value).strip()
    text = re.sub(r"[₹$€£,\s]", "", text)
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _to_date(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    # Handle ISO YYYY-MM-DD
    iso_match = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if iso_match:
        y, m, d = iso_match.groups()
        return datetime(int(y), int(m), int(d))

    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%m-%y",
        "%d/%m/%y",
        "%d-%b-%Y",
        "%d %b %Y",
        "%b %d, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _read_lob(val: Any) -> Any:
    if val is None:
        return None
    if hasattr(val, "read"):
        return val.read()
    return val


def _format_date(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    return str(val)[:10]


def _format_timestamp(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat() + "Z"
    return str(val)


# ============================================================
# 1. SAVE INVOICE (PERSIST OCI EXTRACTION + ORIGINAL SNAPSHOT)
# ============================================================

def save_invoice(
    invoice_result: Dict[str, Any],
    document_name: str,
) -> int:
    invoice = invoice_result.get("invoice") or {}
    line_items = invoice_result.get("line_items") or []
    field_mapping = invoice_result.get("field_mapping") or []
    raw_result = invoice_result.get("raw_result")

    # Capture original extraction snapshot for permanent audit
    original_snapshot = {
        "invoice": dict(invoice),
        "line_items": [dict(l) for l in line_items],
        "field_mapping": field_mapping,
        "job_id": invoice_result.get("job_id"),
        "extracted_at": datetime.utcnow().isoformat() + "Z",
    }

    conn = get_connection()
    cursor = conn.cursor()

    try:
        invoice_id_var = cursor.var(int)

        cursor.execute(
            """
            INSERT INTO GSVAI_INVOICES (
                DOCUMENT_NAME,
                VENDOR_NAME,
                INVOICE_NUMBER,
                INVOICE_DATE,
                DUE_DATE,
                PO_NUMBER,
                CURRENCY,
                SUBTOTAL,
                TAX_AMOUNT,
                TOTAL_AMOUNT,
                PAYMENT_TERMS,
                STATUS,
                VALIDATION_STATUS,
                OCI_JOB_ID,
                RAW_RESULT,
                ORIGINAL_DATA,
                CREATED_AT
            )
            VALUES (
                :document_name,
                :vendor_name,
                :invoice_number,
                :invoice_date,
                :due_date,
                :po_number,
                :currency,
                :subtotal,
                :tax_amount,
                :total_amount,
                :payment_terms,
                :status,
                :validation_status,
                :oci_job_id,
                :raw_result,
                :original_data,
                SYSTIMESTAMP
            )
            RETURNING INVOICE_ID INTO :invoice_id
            """,
            {
                "document_name": document_name,
                "vendor_name": invoice.get("vendor_name"),
                "invoice_number": invoice.get("invoice_number"),
                "invoice_date": _to_date(invoice.get("invoice_date")),
                "due_date": _to_date(invoice.get("due_date")),
                "po_number": invoice.get("po_number"),
                "currency": invoice.get("currency"),
                "subtotal": _to_decimal(invoice.get("subtotal")),
                "tax_amount": _to_decimal(invoice.get("tax_amount")),
                "total_amount": _to_decimal(invoice.get("total_amount")),
                "payment_terms": invoice.get("payment_terms"),
                "status": "REVIEW_REQUIRED",
                "validation_status": "PENDING",
                "oci_job_id": invoice_result.get("job_id"),
                "raw_result": json.dumps(raw_result, ensure_ascii=False, default=str),
                "original_data": json.dumps(original_snapshot, ensure_ascii=False, default=str),
                "invoice_id": invoice_id_var,
            },
        )

        invoice_id = invoice_id_var.getvalue()
        if isinstance(invoice_id, list):
            invoice_id = invoice_id[0]
        invoice_id = int(invoice_id)

        for index, line in enumerate(line_items, start=1):
            cursor.execute(
                """
                INSERT INTO GSVAI_INVOICE_LINES (
                    INVOICE_ID,
                    LINE_NUMBER,
                    DESCRIPTION,
                    ITEM_NUMBER,
                    QUANTITY,
                    UNIT_PRICE,
                    TAX_AMOUNT,
                    LINE_AMOUNT,
                    CREATED_AT
                )
                VALUES (
                    :invoice_id,
                    :line_number,
                    :description,
                    :item_number,
                    :quantity,
                    :unit_price,
                    :tax_amount,
                    :line_amount,
                    SYSTIMESTAMP
                )
                """,
                {
                    "invoice_id": invoice_id,
                    "line_number": line.get("line_number", index),
                    "description": line.get("description"),
                    "item_number": line.get("item_number"),
                    "quantity": _to_decimal(line.get("quantity")),
                    "unit_price": _to_decimal(line.get("unit_price")),
                    "tax_amount": _to_decimal(line.get("tax_amount")),
                    "line_amount": _to_decimal(line.get("line_amount")),
                },
            )

        conn.commit()
        return invoice_id

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# ============================================================
# 2. REVIEW QUEUE LIST
# ============================================================

def get_review_queue(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        sql = """
            SELECT
                INVOICE_ID,
                DOCUMENT_NAME,
                VENDOR_NAME,
                INVOICE_NUMBER,
                INVOICE_DATE,
                DUE_DATE,
                PO_NUMBER,
                CURRENCY,
                SUBTOTAL,
                TAX_AMOUNT,
                TOTAL_AMOUNT,
                STATUS,
                VALIDATION_STATUS,
                REVIEWED_BY,
                REVIEWED_AT,
                FUSION_STATUS,
                FUSION_INVOICE_ID,
                CREATED_AT
            FROM GSVAI_INVOICES
        """
        params = {}
        if status_filter:
            sql += " WHERE STATUS = :status_filter"
            params["status_filter"] = status_filter
        sql += " ORDER BY INVOICE_ID DESC"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        columns = [d[0].lower() for d in cursor.description]

        results = []
        for row in rows:
            record = dict(zip(columns, row))
            record["invoice_date"] = _format_date(record.get("invoice_date"))
            record["due_date"] = _format_date(record.get("due_date"))
            record["created_at"] = _format_timestamp(record.get("created_at"))
            record["reviewed_at"] = _format_timestamp(record.get("reviewed_at"))
            if record.get("total_amount") is not None:
                record["total_amount"] = float(record["total_amount"])
            if record.get("subtotal") is not None:
                record["subtotal"] = float(record["subtotal"])
            if record.get("tax_amount") is not None:
                record["tax_amount"] = float(record["tax_amount"])
            results.append(record)

        return results

    finally:
        cursor.close()
        conn.close()


# ============================================================
# 3. GET INVOICE FOR DETAILED REVIEW
# ============================================================

def get_invoice_for_review(invoice_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                INVOICE_ID,
                DOCUMENT_NAME,
                VENDOR_NAME,
                INVOICE_NUMBER,
                INVOICE_DATE,
                DUE_DATE,
                PO_NUMBER,
                CURRENCY,
                SUBTOTAL,
                TAX_AMOUNT,
                TOTAL_AMOUNT,
                PAYMENT_TERMS,
                STATUS,
                VALIDATION_STATUS,
                OCI_JOB_ID,
                RAW_RESULT,
                ORIGINAL_DATA,
                REVIEWED_BY,
                REVIEWED_AT,
                REVIEW_COMMENTS,
                FUSION_INVOICE_ID,
                FUSION_STATUS,
                FUSION_SUBMITTED_AT,
                CREATED_AT
            FROM GSVAI_INVOICES
            WHERE INVOICE_ID = :invoice_id
            """,
            {"invoice_id": invoice_id},
        )

        row = cursor.fetchone()
        if not row:
            return None

        columns = [d[0].lower() for d in cursor.description]
        invoice_data = dict(zip(columns, row))

        # Format dates & numbers
        invoice_data["invoice_date"] = _format_date(invoice_data.get("invoice_date"))
        invoice_data["due_date"] = _format_date(invoice_data.get("due_date"))
        invoice_data["created_at"] = _format_timestamp(invoice_data.get("created_at"))
        invoice_data["reviewed_at"] = _format_timestamp(invoice_data.get("reviewed_at"))
        invoice_data["fusion_submitted_at"] = _format_timestamp(invoice_data.get("fusion_submitted_at"))
        if invoice_data.get("total_amount") is not None:
            invoice_data["total_amount"] = float(invoice_data["total_amount"])
        if invoice_data.get("subtotal") is not None:
            invoice_data["subtotal"] = float(invoice_data["subtotal"])
        if invoice_data.get("tax_amount") is not None:
            invoice_data["tax_amount"] = float(invoice_data["tax_amount"])

        # Parse original data snapshot
        original_data_raw = _read_lob(invoice_data.pop("original_data", None))
        original_data = {}
        if original_data_raw:
            try:
                original_data = json.loads(original_data_raw) if isinstance(original_data_raw, str) else original_data_raw
            except Exception:
                original_data = {}
        invoice_data["original_snapshot"] = original_data

        # Clean up raw_result LOB object
        invoice_data.pop("raw_result", None)
        cursor.execute(
            """
            SELECT
                LINE_ID,
                LINE_NUMBER,
                DESCRIPTION,
                ITEM_NUMBER,
                QUANTITY,
                UNIT_PRICE,
                TAX_AMOUNT,
                LINE_AMOUNT,
                CREATED_AT
            FROM GSVAI_INVOICE_LINES
            WHERE INVOICE_ID = :invoice_id
            ORDER BY LINE_NUMBER, LINE_ID
            """,
            {"invoice_id": invoice_id},
        )
        line_cols = [d[0].lower() for d in cursor.description]
        line_rows = cursor.fetchall()
        lines = []
        for line in line_rows:
            l_dict = dict(zip(line_cols, line))
            if l_dict.get("quantity") is not None:
                l_dict["quantity"] = float(l_dict["quantity"])
            if l_dict.get("unit_price") is not None:
                l_dict["unit_price"] = float(l_dict["unit_price"])
            if l_dict.get("tax_amount") is not None:
                l_dict["tax_amount"] = float(l_dict["tax_amount"])
            if l_dict.get("line_amount") is not None:
                l_dict["line_amount"] = float(l_dict["line_amount"])
            lines.append(l_dict)

        invoice_data["line_items"] = lines

        # Clean up huge raw_result string for lightweight transfer
        raw_res_str = invoice_data.pop("raw_result", None)
        invoice_data["has_raw_result"] = bool(raw_res_str)

        return invoice_data

    finally:
        cursor.close()
        conn.close()


# ============================================================
# 4. UPDATE INVOICE REVIEW (HUMAN CORRECTIONS)
# ============================================================

def update_invoice_review(
    invoice_id: int,
    header_fields: Dict[str, Any],
    line_items: Optional[List[Dict[str, Any]]] = None,
    reviewer: str = "Human Reviewer",
    comments: Optional[str] = None,
) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Update header fields
        cursor.execute(
            """
            UPDATE GSVAI_INVOICES
            SET
                VENDOR_NAME     = :vendor_name,
                INVOICE_NUMBER  = :invoice_number,
                INVOICE_DATE    = :invoice_date,
                DUE_DATE        = :due_date,
                PO_NUMBER       = :po_number,
                CURRENCY        = :currency,
                SUBTOTAL        = :subtotal,
                TAX_AMOUNT      = :tax_amount,
                TOTAL_AMOUNT    = :total_amount,
                PAYMENT_TERMS   = :payment_terms,
                REVIEWED_BY     = :reviewed_by,
                REVIEWED_AT     = SYSTIMESTAMP,
                REVIEW_COMMENTS = :comments
            WHERE INVOICE_ID = :invoice_id
            """,
            {
                "vendor_name": header_fields.get("vendor_name"),
                "invoice_number": header_fields.get("invoice_number"),
                "invoice_date": _to_date(header_fields.get("invoice_date")),
                "due_date": _to_date(header_fields.get("due_date")),
                "po_number": header_fields.get("po_number"),
                "currency": header_fields.get("currency"),
                "subtotal": _to_decimal(header_fields.get("subtotal")),
                "tax_amount": _to_decimal(header_fields.get("tax_amount")),
                "total_amount": _to_decimal(header_fields.get("total_amount")),
                "payment_terms": header_fields.get("payment_terms"),
                "reviewed_by": reviewer,
                "comments": comments,
                "invoice_id": invoice_id,
            },
        )

        # 2. Update line items if supplied
        if line_items is not None:
            cursor.execute(
                "DELETE FROM GSVAI_INVOICE_LINES WHERE INVOICE_ID = :invoice_id",
                {"invoice_id": invoice_id},
            )
            for idx, line in enumerate(line_items, start=1):
                cursor.execute(
                    """
                    INSERT INTO GSVAI_INVOICE_LINES (
                        INVOICE_ID,
                        LINE_NUMBER,
                        DESCRIPTION,
                        ITEM_NUMBER,
                        QUANTITY,
                        UNIT_PRICE,
                        TAX_AMOUNT,
                        LINE_AMOUNT,
                        CREATED_AT
                    )
                    VALUES (
                        :invoice_id,
                        :line_number,
                        :description,
                        :item_number,
                        :quantity,
                        :unit_price,
                        :tax_amount,
                        :line_amount,
                        SYSTIMESTAMP
                    )
                    """,
                    {
                        "invoice_id": invoice_id,
                        "line_number": line.get("line_number", idx),
                        "description": line.get("description"),
                        "item_number": line.get("item_number"),
                        "quantity": _to_decimal(line.get("quantity")),
                        "unit_price": _to_decimal(line.get("unit_price")),
                        "tax_amount": _to_decimal(line.get("tax_amount")),
                        "line_amount": _to_decimal(line.get("line_amount")),
                    },
                )

        conn.commit()
        return {"status": "SUCCESS", "message": "Invoice corrections saved successfully."}

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# ============================================================
# 5. APPROVE INVOICE
# ============================================================

def approve_invoice(
    invoice_id: int,
    reviewer: str = "Human Reviewer",
    comments: Optional[str] = "Approved by reviewer",
) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT STATUS FROM GSVAI_INVOICES WHERE INVOICE_ID = :invoice_id",
            {"invoice_id": invoice_id},
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Invoice ID {invoice_id} not found.")

        current_status = row[0]
        if current_status not in ("REVIEW_REQUIRED", "EXTRACTED", "PROCESSED", "PENDING"):
            raise ValueError(
                f"Invoice cannot be approved from status '{current_status}'. Must be REVIEW_REQUIRED."
            )

        cursor.execute(
            """
            UPDATE GSVAI_INVOICES
            SET
                STATUS          = 'APPROVED',
                REVIEWED_BY     = :reviewed_by,
                REVIEWED_AT     = SYSTIMESTAMP,
                REVIEW_COMMENTS = :comments
            WHERE INVOICE_ID = :invoice_id
            """,
            {
                "reviewed_by": reviewer,
                "comments": comments or "Approved",
                "invoice_id": invoice_id,
            },
        )
        conn.commit()
        return {
            "status": "APPROVED",
            "invoice_id": invoice_id,
            "message": "Invoice approved successfully and is eligible for Oracle Fusion submission.",
        }

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# ============================================================
# 6. REJECT INVOICE
# ============================================================

def reject_invoice(
    invoice_id: int,
    reviewer: str = "Human Reviewer",
    comments: str = "Rejected by reviewer",
) -> Dict[str, Any]:
    if not comments or not comments.strip():
        raise ValueError("A reason / comment is required when rejecting an invoice.")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT STATUS FROM GSVAI_INVOICES WHERE INVOICE_ID = :invoice_id",
            {"invoice_id": invoice_id},
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Invoice ID {invoice_id} not found.")

        current_status = row[0]
        if current_status not in ("REVIEW_REQUIRED", "EXTRACTED", "PROCESSED", "PENDING"):
            raise ValueError(
                f"Invoice cannot be rejected from status '{current_status}'. Must be REVIEW_REQUIRED."
            )

        cursor.execute(
            """
            UPDATE GSVAI_INVOICES
            SET
                STATUS          = 'REJECTED',
                REVIEWED_BY     = :reviewed_by,
                REVIEWED_AT     = SYSTIMESTAMP,
                REVIEW_COMMENTS = :comments
            WHERE INVOICE_ID = :invoice_id
            """,
            {
                "reviewed_by": reviewer,
                "comments": comments.strip(),
                "invoice_id": invoice_id,
            },
        )
        conn.commit()
        return {
            "status": "REJECTED",
            "invoice_id": invoice_id,
            "message": "Invoice rejected.",
        }

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# ============================================================
# 7. UPDATE FUSION STATUS & RECORD SUBMISSION
# ============================================================

def update_fusion_submission(
    invoice_id: int,
    status: str,
    fusion_invoice_id: Optional[str] = None,
    request_payload: Optional[Any] = None,
    response_payload: Optional[Any] = None,
    error_message: Optional[str] = None,
) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Update GSVAI_INVOICES
        cursor.execute(
            """
            UPDATE GSVAI_INVOICES
            SET
                STATUS              = :status,
                FUSION_STATUS       = :fusion_status,
                FUSION_INVOICE_ID   = :fusion_invoice_id,
                FUSION_SUBMITTED_AT = SYSTIMESTAMP
            WHERE INVOICE_ID = :invoice_id
            """,
            {
                "status": status,
                "fusion_status": status,
                "fusion_invoice_id": fusion_invoice_id,
                "invoice_id": invoice_id,
            },
        )

        # 2. Insert into GSVAI_FUSION_SUBMISSIONS
        cursor.execute(
            """
            INSERT INTO GSVAI_FUSION_SUBMISSIONS (
                INVOICE_ID,
                FUSION_INVOICE_ID,
                STATUS,
                REQUEST_PAYLOAD,
                RESPONSE_PAYLOAD,
                ERROR_MESSAGE,
                SUBMITTED_AT,
                UPDATED_AT
            )
            VALUES (
                :invoice_id,
                :fusion_invoice_id,
                :status,
                :request_payload,
                :response_payload,
                :error_message,
                SYSTIMESTAMP,
                SYSTIMESTAMP
            )
            """,
            {
                "invoice_id": invoice_id,
                "fusion_invoice_id": fusion_invoice_id,
                "status": status,
                "request_payload": json.dumps(request_payload, default=str) if request_payload else None,
                "response_payload": json.dumps(response_payload, default=str) if response_payload else None,
                "error_message": error_message,
            },
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()