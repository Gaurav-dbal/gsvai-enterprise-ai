import json
from services.invoice_service import extract_invoice_data

test_data = {
    "documentMetadata": {"pageCount": 1},
    "pages": [
        {
            "pageNumber": 1,
            "documentFields": [
                {
                    "fieldType": "KEY_VALUE",
                    "fieldLabel": {
                        "name": "VendorName",
                        "confidence": 0.9935568
                    },
                    "fieldValue": {
                        "valueType": "STRING",
                        "text": "AADIFIDELIS SOLUTIONS PRIVATE LIMITED",
                        "value": "AADIFIDELIS SOLUTIONS PRIVATE LIMITED"
                    }
                },
                {
                    "fieldType": "KEY_VALUE",
                    "fieldLabel": {
                        "name": "InvoiceId",
                        "confidence": 0.82151884
                    },
                    "fieldValue": {
                        "valueType": "STRING",
                        "text": "1025/BL/DL/0889",
                        "value": "1025/BL/DL/0889"
                    }
                },
                {
                    "fieldType": "KEY_VALUE",
                    "fieldLabel": {
                        "name": "InvoiceDate",
                        "confidence": 0.961
                    },
                    "fieldValue": {
                        "valueType": "DATE",
                        "text": "13-11-2025",
                        "value": "2025-11-13T00:00:00.000Z"
                    }
                },
                {
                    "fieldType": "KEY_VALUE",
                    "fieldLabel": {
                        "name": "DueDate",
                        "confidence": 0.835
                    },
                    "fieldValue": {
                        "valueType": "DATE",
                        "text": "13-11-2025",
                        "value": "2025-11-13T00:00:00.000Z"
                    }
                },
                {
                    "fieldType": "KEY_VALUE",
                    "fieldLabel": {
                        "name": "SubTotal",
                        "confidence": 0.809
                    },
                    "fieldValue": {
                        "valueType": "NUMBER",
                        "text": "3,79,08,719",
                        "value": 37908720
                    }
                },
                {
                    "fieldType": "KEY_VALUE",
                    "fieldLabel": {
                        "name": "TotalTax",
                        "confidence": 0.643
                    },
                    "fieldValue": {
                        "valueType": "NUMBER",
                        "text": "12,71,307.10",
                        "value": 1271307.1
                    }
                },
                {
                    "fieldType": "KEY_VALUE",
                    "fieldLabel": {
                        "name": "InvoiceTotal",
                        "confidence": 0.889
                    },
                    "fieldValue": {
                        "valueType": "NUMBER",
                        "text": "15,00,142",
                        "value": 1500142
                    }
                },
                {
                    "fieldType": "LINE_ITEM_GROUP",
                    "fieldLabel": {
                        "name": "Items",
                        "confidence": 0.95
                    },
                    "fieldValue": {
                        "valueType": "ARRAY",
                        "items": [
                            {
                                "fieldType": "LINE_ITEM",
                                "fieldLabel": {
                                    "name": "Item",
                                    "confidence": 0.95
                                },
                                "fieldValue": {
                                    "valueType": "ARRAY",
                                    "items": [
                                        {
                                            "fieldType": "LINE_ITEM_FIELD",
                                            "fieldLabel": {
                                                "name": "Description",
                                                "confidence": 0.95
                                            },
                                            "fieldValue": {
                                                "valueType": "STRING",
                                                "text": "Referral : Payouts for Business Loan the Month of Oct, 2025",
                                                "value": "Referral : Payouts for Business Loan the Month of Oct, 2025"
                                            }
                                        },
                                        {
                                            "fieldType": "LINE_ITEM_FIELD",
                                            "fieldLabel": {
                                                "name": "ProductCode",
                                                "confidence": 0.95
                                            },
                                            "fieldValue": {
                                                "valueType": "STRING",
                                                "text": "997159",
                                                "value": "997159"
                                            }
                                        },
                                        {
                                            "fieldType": "LINE_ITEM_FIELD",
                                            "fieldLabel": {
                                                "name": "Quantity",
                                                "confidence": 0.95
                                            },
                                            "fieldValue": {
                                                "valueType": "NUMBER",
                                                "text": "0",
                                                "value": 0
                                            }
                                        },
                                        {
                                            "fieldType": "LINE_ITEM_FIELD",
                                            "fieldLabel": {
                                                "name": "UnitPrice",
                                                "confidence": 0.95
                                            },
                                            "fieldValue": {
                                                "valueType": "NUMBER",
                                                "text": "12,71,307.14",
                                                "value": 1271307.14
                                            }
                                        },
                                        {
                                            "fieldType": "LINE_ITEM_FIELD",
                                            "fieldLabel": {
                                                "name": "Amount",
                                                "confidence": 0.95
                                            },
                                            "fieldValue": {
                                                "valueType": "NUMBER",
                                                "text": "15,00,142",
                                                "value": 1500142
                                            }
                                        },
                                        {
                                            "fieldType": "LINE_ITEM_FIELD",
                                            "fieldLabel": {
                                                "name": "Unit",
                                                "confidence": 0.95
                                            },
                                            "fieldValue": {
                                                "valueType": "STRING",
                                                "text": "OTH",
                                                "value": "OTH"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            ]
        }
    ]
}

res = extract_invoice_data([{"object_name": "test.json", "data": test_data}])

print("=" * 60)
print("EXTRACTED INVOICE HEADER:")
print("=" * 60)
print(json.dumps(res["invoice"], indent=2))

print("\n" + "=" * 60)
print(f"EXTRACTED LINE ITEMS ({len(res['line_items'])} items):")
print("=" * 60)
for item in res["line_items"]:
    print(json.dumps(item, indent=2))

print("\n" + "=" * 60)
print(f"FIELD MAPPINGS ({len(res['field_mapping'])} mapped fields):")
print("=" * 60)
for m in res["field_mapping"]:
    conf_str = f"{round(m['confidence'] * 100, 1)}%" if m["confidence"] is not None else "N/A"
    print(f"  {m['display_name']:<18} ({m['oci_field']:<15}) -> {str(m['value']):<42} [Confidence: {conf_str}]")

# Assertions matching Part 23 exact requirements
assert res["invoice"]["vendor_name"] == "AADIFIDELIS SOLUTIONS PRIVATE LIMITED", "VendorName mismatch"
assert res["invoice"]["invoice_number"] == "1025/BL/DL/0889", "InvoiceId mismatch"
assert res["invoice"]["invoice_date"] == "2025-11-13", "InvoiceDate mismatch"
assert res["invoice"]["due_date"] == "2025-11-13", "DueDate mismatch"
assert res["invoice"]["subtotal"] == 37908720, "Subtotal mismatch"
assert res["invoice"]["tax_amount"] == 1271307.1, "TaxAmount mismatch"
assert res["invoice"]["total_amount"] == 1500142, "InvoiceTotal mismatch"
assert len(res["line_items"]) == 1, f"Expected 1 line item, got {len(res['line_items'])}"
assert res["line_items"][0]["item_number"] == "997159"
assert res["line_items"][0]["line_amount"] == 1500142
assert res["line_items"][0]["unit_price"] == 1271307.14

print("\n>>> ALL OCI PARSER ASSERTIONS PASSED WITH 100% ACCURACY! <<<")
