from typing import Any, Dict, Optional

from services.invoice_db_service import save_invoice
from services.invoice_validation_service import validate_invoice
from services.invoice_matching_service import three_way_match
from services.invoice_exception_service import detect_exceptions


def process_invoice_workflow(
    invoice_result: Dict[str, Any],
    document_name: str,
    purchase_order: Optional[Dict[str, Any]] = None,
    goods_receipt: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    # ========================================================
    # 4C - Persist invoice
    # ========================================================

    invoice_id = save_invoice(
        invoice_result=invoice_result,
        document_name=document_name,
    )

    invoice = dict(
        invoice_result.get("invoice") or {}
    )

    invoice["invoice_id"] = invoice_id

    invoice["line_items"] = (
        invoice_result.get(
            "line_items"
        ) or []
    )

    # ========================================================
    # Step 5 - Validation
    # ========================================================

    validation_result = validate_invoice(
        invoice_result
    )

    # ========================================================
    # Step 6 - Three-way matching
    # ========================================================

    matching_result = three_way_match(
        invoice=invoice,
        purchase_order=purchase_order,
        goods_receipt=goods_receipt,
    )

    # ========================================================
    # Step 7 - Exception detection
    # ========================================================

    exception_result = detect_exceptions(
        invoice=invoice,
        validation_result=validation_result,
        matching_result=matching_result,
    )

    return {
        "invoice_id": invoice_id,
        "invoice": invoice,
        "validation": validation_result,
        "matching": matching_result,
        "exceptions": exception_result,
    }