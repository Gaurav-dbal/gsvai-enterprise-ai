from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional


def _decimal(
    value: Any,
) -> Optional[Decimal]:

    if value is None or value == "":
        return None

    try:

        return Decimal(
            str(value)
            .replace(",", "")
            .replace("₹", "")
        )

    except (
        InvalidOperation,
        ValueError,
    ):

        return None


def _compare_value(
    field_name: str,
    invoice_value: Any,
    po_value: Any,
    grn_value: Any = None,
    tolerance: Decimal = Decimal("0.01"),
) -> Dict[str, Any]:

    invoice_decimal = _decimal(
        invoice_value
    )

    po_decimal = _decimal(
        po_value
    )

    grn_decimal = _decimal(
        grn_value
    )

    result = {
        "field": field_name,
        "invoice": invoice_value,
        "po": po_value,
        "grn": grn_value,
        "status": "NOT_CHECKED",
        "difference_invoice_po": None,
        "difference_invoice_grn": None,
    }

    if (
        invoice_decimal is None
        or po_decimal is None
    ):

        result["status"] = (
            "DATA_MISSING"
        )

        return result

    difference_po = abs(
        invoice_decimal
        - po_decimal
    )

    result[
        "difference_invoice_po"
    ] = float(
        difference_po
    )

    if difference_po > tolerance:

        result["status"] = (
            "MISMATCH"
        )

        return result

    if grn_decimal is not None:

        difference_grn = abs(
            invoice_decimal
            - grn_decimal
        )

        result[
            "difference_invoice_grn"
        ] = float(
            difference_grn
        )

        if difference_grn > tolerance:

            result["status"] = (
                "MISMATCH"
            )

            return result

    result["status"] = "MATCH"

    return result


def three_way_match(
    invoice: Dict[str, Any],
    purchase_order: Optional[
        Dict[str, Any]
    ],
    goods_receipt: Optional[
        Dict[str, Any]
    ],
    amount_tolerance: Decimal = Decimal(
        "0.01"
    ),
    quantity_tolerance: Decimal = Decimal(
        "0.01"
    ),
) -> Dict[str, Any]:

    # ========================================================
    # PO not yet available
    # ========================================================

    if not purchase_order:

        return {
            "status": "PENDING_PO",
            "message": (
                "Purchase order data "
                "is not available."
            ),
            "checks": [],
            "exceptions": [
                {
                    "code": "PO_NOT_FOUND",
                    "message": (
                        "No purchase order "
                        "supplied for matching."
                    ),
                }
            ],
        }

    # ========================================================
    # GRN not yet available
    # ========================================================

    if not goods_receipt:

        return {
            "status": "PENDING_GRN",
            "message": (
                "Goods receipt data "
                "is not available."
            ),
            "checks": [],
            "exceptions": [
                {
                    "code": "GRN_NOT_FOUND",
                    "message": (
                        "No goods receipt "
                        "supplied for matching."
                    ),
                }
            ],
        }

    checks: List[
        Dict[str, Any]
    ] = []

    # ========================================================
    # Invoice total vs PO total
    # ========================================================

    checks.append(
        _compare_value(
            "total_amount",
            invoice.get(
                "total_amount"
            ),
            purchase_order.get(
                "total_amount"
            ),
            tolerance=amount_tolerance,
        )
    )

    # ========================================================
    # Vendor comparison
    # ========================================================

    invoice_vendor = str(
        invoice.get(
            "vendor_name"
        ) or ""
    ).strip().lower()

    po_vendor = str(
        purchase_order.get(
            "vendor_name"
        ) or ""
    ).strip().lower()

    if (
        invoice_vendor
        and po_vendor
    ):

        checks.append(
            {
                "field": "vendor_name",
                "invoice": invoice.get(
                    "vendor_name"
                ),
                "po": purchase_order.get(
                    "vendor_name"
                ),
                "status": (
                    "MATCH"
                    if invoice_vendor
                    == po_vendor
                    else "MISMATCH"
                ),
            }
        )

    else:

        checks.append(
            {
                "field": "vendor_name",
                "status": "DATA_MISSING",
            }
        )

    # ========================================================
    # Line-level comparison
    # ========================================================

    invoice_lines = (
        invoice.get(
            "line_items"
        ) or []
    )

    po_lines = (
        purchase_order.get(
            "line_items"
        ) or []
    )

    grn_lines = (
        goods_receipt.get(
            "line_items"
        ) or []
    )

    for invoice_line in invoice_lines:

        item_number = invoice_line.get(
            "item_number"
        )

        if item_number is None:
            continue

        po_line = next(
            (
                line
                for line in po_lines
                if str(
                    line.get(
                        "item_number"
                    )
                )
                == str(
                    item_number
                )
            ),
            None,
        )

        grn_line = next(
            (
                line
                for line in grn_lines
                if str(
                    line.get(
                        "item_number"
                    )
                )
                == str(
                    item_number
                )
            ),
            None,
        )

        # Quantity

        checks.append(
            _compare_value(
                f"quantity:item:{item_number}",
                invoice_line.get(
                    "quantity"
                ),
                (
                    po_line.get(
                        "quantity"
                    )
                    if po_line
                    else None
                ),
                (
                    grn_line.get(
                        "quantity"
                    )
                    if grn_line
                    else None
                ),
                tolerance=quantity_tolerance,
            )
        )

        # Unit price

        checks.append(
            _compare_value(
                f"unit_price:item:{item_number}",
                invoice_line.get(
                    "unit_price"
                ),
                (
                    po_line.get(
                        "unit_price"
                    )
                    if po_line
                    else None
                ),
                tolerance=amount_tolerance,
            )
        )

    # ========================================================
    # Final status
    # ========================================================

    mismatches = [
        check
        for check in checks
        if check.get(
            "status"
        ) == "MISMATCH"
    ]

    missing = [
        check
        for check in checks
        if check.get(
            "status"
        ) == "DATA_MISSING"
    ]

    if mismatches:

        status = "MISMATCH"

    elif missing:

        status = "INCOMPLETE"

    else:

        status = "MATCHED"

    return {
        "status": status,
        "checks": checks,
        "exceptions": [
            {
                "code": "MATCH_MISMATCH",
                "message": (
                    f"{check['field']} "
                    "does not match."
                ),
                "check": check,
            }
            for check in mismatches
        ],
    }