from typing import Any, Dict, List


def detect_exceptions(
    invoice: Dict[str, Any],
    validation_result: Dict[str, Any],
    matching_result: Dict[str, Any],
) -> Dict[str, Any]:

    exceptions: List[
        Dict[str, Any]
    ] = []

    # ========================================================
    # Validation errors
    # ========================================================

    for item in validation_result.get(
        "errors",
        [],
    ):

        exceptions.append(
            {
                "category": "VALIDATION",
                "severity": "HIGH",
                "code": item.get(
                    "code"
                ),
                "message": item.get(
                    "message"
                ),
                "details": item,
            }
        )

    # ========================================================
    # Validation warnings
    # ========================================================

    for item in validation_result.get(
        "warnings",
        [],
    ):

        exceptions.append(
            {
                "category": "VALIDATION",
                "severity": "MEDIUM",
                "code": item.get(
                    "code"
                ),
                "message": item.get(
                    "message"
                ),
                "details": item,
            }
        )

    # ========================================================
    # Matching exceptions
    # ========================================================

    for item in matching_result.get(
        "exceptions",
        [],
    ):

        exceptions.append(
            {
                "category": "THREE_WAY_MATCH",
                "severity": (
                    "HIGH"
                    if matching_result.get(
                        "status"
                    ) == "MISMATCH"
                    else "MEDIUM"
                ),
                "code": item.get(
                    "code"
                ),
                "message": item.get(
                    "message"
                ),
                "details": item,
            }
        )

    # ========================================================
    # Overall decision
    # ========================================================

    if not exceptions:

        overall_status = (
            "NO_EXCEPTION"
        )

        recommended_action = (
            "CONTINUE_PROCESSING"
        )

    elif any(
        exception.get(
            "severity"
        ) == "HIGH"
        for exception in exceptions
    ):

        overall_status = (
            "EXCEPTION"
        )

        recommended_action = (
            "HUMAN_REVIEW"
        )

    else:

        overall_status = (
            "WARNING"
        )

        recommended_action = (
            "REVIEW"
        )

    return {
        "status": overall_status,
        "recommended_action": (
            recommended_action
        ),
        "exception_count": len(
            exceptions
        ),
        "exceptions": exceptions,
        "invoice_id": invoice.get(
            "invoice_id"
        ),
        "invoice_number": invoice.get(
            "invoice_number"
        ),
        "vendor_name": invoice.get(
            "vendor_name"
        ),
    }