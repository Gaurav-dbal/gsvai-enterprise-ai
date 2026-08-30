from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List


def _decimal(value: Any):

    if value is None or value == "":
        return None

    if isinstance(value, Decimal):
        return value

    text = str(value).strip()

    for symbol in [
        ",",
        "₹",
        "$",
        "€",
        "£",
    ]:
        text = text.replace(
            symbol,
            "",
        )

    try:
        return Decimal(text)

    except (
        InvalidOperation,
        ValueError,
    ):
        return None


def validate_invoice(
    invoice_result: Dict[str, Any],
) -> Dict[str, Any]:

    invoice = (
        invoice_result.get(
            "invoice"
        ) or {}
    )

    lines = (
        invoice_result.get(
            "line_items"
        ) or []
    )

    errors: List[Dict[str, Any]] = []

    warnings: List[Dict[str, Any]] = []

    # ========================================================
    # Mandatory fields
    # ========================================================

    required_fields = {
        "vendor_name": "Vendor name",
        "invoice_number": "Invoice number",
        "invoice_date": "Invoice date",
        "currency": "Currency",
        "total_amount": "Total amount",
    }

    for field, label in required_fields.items():

        value = invoice.get(field)

        if value in (
            None,
            "",
        ):

            errors.append(
                {
                    "code": (
                        f"MISSING_{field.upper()}"
                    ),
                    "message": (
                        f"{label} is missing."
                    ),
                    "field": field,
                }
            )

    # ========================================================
    # Numeric validation
    # ========================================================

    subtotal = _decimal(
        invoice.get(
            "subtotal"
        )
    )

    tax = _decimal(
        invoice.get(
            "tax_amount"
        )
    )

    total = _decimal(
        invoice.get(
            "total_amount"
        )
    )

    if subtotal is not None and subtotal < 0:

        errors.append(
            {
                "code": "NEGATIVE_SUBTOTAL",
                "message": (
                    "Invoice subtotal "
                    "cannot be negative."
                ),
                "field": "subtotal",
            }
        )

    if tax is not None and tax < 0:

        errors.append(
            {
                "code": "NEGATIVE_TAX",
                "message": (
                    "Tax amount cannot "
                    "be negative."
                ),
                "field": "tax_amount",
            }
        )

    if total is not None and total < 0:

        errors.append(
            {
                "code": "NEGATIVE_TOTAL",
                "message": (
                    "Invoice total "
                    "cannot be negative."
                ),
                "field": "total_amount",
            }
        )

    # ========================================================
    # Header total reconciliation
    # ========================================================

    if (
        subtotal is not None
        and tax is not None
        and total is not None
    ):

        expected_total = (
            subtotal + tax
        )

        difference = abs(
            expected_total - total
        )

        if difference > Decimal("0.02"):

            errors.append(
                {
                    "code": (
                        "TOTAL_RECONCILIATION_FAILED"
                    ),
                    "message": (
                        f"Subtotal + tax = "
                        f"{expected_total}, "
                        f"but invoice total = "
                        f"{total}."
                    ),
                    "field": "total_amount",
                    "difference": float(
                        difference
                    ),
                }
            )

    # ========================================================
    # Line validation
    # ========================================================

    line_total = Decimal("0")

    line_amount_count = 0

    for line in lines:

        quantity = _decimal(
            line.get(
                "quantity"
            )
        )

        unit_price = _decimal(
            line.get(
                "unit_price"
            )
        )

        line_amount = _decimal(
            line.get(
                "line_amount"
            )
        )

        if quantity is not None:

            if quantity < 0:

                errors.append(
                    {
                        "code": (
                            "NEGATIVE_QUANTITY"
                        ),
                        "message": (
                            "Line quantity "
                            "cannot be negative."
                        ),
                        "line_number": (
                            line.get(
                                "line_number"
                            )
                        ),
                    }
                )

        if unit_price is not None:

            if unit_price < 0:

                errors.append(
                    {
                        "code": (
                            "NEGATIVE_UNIT_PRICE"
                        ),
                        "message": (
                            "Line unit price "
                            "cannot be negative."
                        ),
                        "line_number": (
                            line.get(
                                "line_number"
                            )
                        ),
                    }
                )

        if line_amount is not None:

            line_total += line_amount

            line_amount_count += 1

    # ========================================================
    # Line total warning
    # ========================================================

    if (
        total is not None
        and line_amount_count > 0
    ):

        difference = abs(
            line_total - total
        )

        if difference > Decimal("0.02"):

            warnings.append(
                {
                    "code": (
                        "LINE_TOTAL_DIFFERENCE"
                    ),
                    "message": (
                        f"Line total = "
                        f"{line_total}, "
                        f"invoice total = "
                        f"{total}."
                    ),
                    "difference": float(
                        difference
                    ),
                }
            )

    # ========================================================
    # Overall result
    # ========================================================

    status = (
        "INVALID"
        if errors
        else "VALID"
    )

    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "checked_fields": len(
            required_fields
        ),
        "line_items_checked": len(
            lines
        ),
    }