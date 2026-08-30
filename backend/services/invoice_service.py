import datetime
import json
import os
import re
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

import oci

from services.oci_document_understanding_service import (
    document_client,
    object_storage_client,
    OCI_COMPARTMENT_ID,
    OCI_OBJECT_STORAGE_NAMESPACE,
    OCI_DOCUMENT_BUCKET,
)
from services.invoice_state_service import invoice_state_manager


# ============================================================
# Invoice Automation Service
# ============================================================

INVOICE_INPUT_PREFIX = "gsvai-invoice-automation/input/"
INVOICE_OUTPUT_PREFIX = "gsvai-invoice-automation/output/"


# ============================================================
# OCI MODEL SERIALIZATION & NORMALIZATION UTILS
# ============================================================

def _safe_value(value: Any) -> Any:
    """
    Convert OCI SDK objects recursively into JSON-compatible Python values.
    """
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, list):
        return [_safe_value(item) for item in value]

    if isinstance(value, dict):
        return {str(key): _safe_value(val) for key, val in value.items()}

    if hasattr(value, "swagger_types"):
        result = {}
        for field_name in value.swagger_types:
            try:
                field_value = getattr(value, field_name)
            except Exception:
                continue
            result[field_name] = _safe_value(field_value)
        return result

    return str(value)


def _normalize_date(value: Any) -> Optional[str]:
    """
    Deterministically normalizes dates from OCI to standard ISO YYYY-MM-DD.
    Handles ISO timestamps (e.g. 2025-11-13T00:00:00.000Z), DD-MM-YYYY, DD/MM/YYYY, etc.
    """
    if value is None or value == "":
        return None

    text = str(value).strip()

    # YYYY-MM-DD or YYYY/MM/DD prefix (e.g. 2025-11-13T00:00:00.000Z)
    iso_match = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if iso_match:
        year, month, day = iso_match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    # DD-MM-YYYY or DD/MM/YYYY
    dmy_match = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})", text)
    if dmy_match:
        day, month, year = dmy_match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    # Named month patterns (e.g. 13-Nov-2025, 13 November 2025)
    for fmt in ("%d-%b-%Y", "%d %b %Y", "%b %d, %Y", "%d-%B-%Y", "%B %d, %Y"):
        try:
            dt = datetime.datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return text


def _normalize_number(val: Any, text_fallback: Any = None) -> Any:
    """
    Prefers numeric fieldValue.value over formatted display text.
    Fallback to cleaned text if value is missing.
    """
    if val is not None and isinstance(val, (int, float)):
        return val

    candidate = val if val is not None else text_fallback
    if candidate is None or candidate == "":
        return None

    if isinstance(candidate, (int, float)):
        return candidate

    cleaned = str(candidate).strip()
    cleaned = re.sub(r"[₹$€£,\s]", "", cleaned)
    try:
        if "." in cleaned:
            return float(cleaned)
        return int(cleaned)
    except (ValueError, TypeError):
        return candidate


# ============================================================
# UPLOAD INVOICE TO OCI OBJECT STORAGE
# ============================================================

def upload_invoice_to_object_storage(
    file_path: str,
    original_filename: Optional[str] = None,
) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Invoice file not found: {file_path}")

    filename = original_filename or os.path.basename(file_path)
    unique_id = str(uuid.uuid4())
    object_name = f"{INVOICE_INPUT_PREFIX}{unique_id}-{filename}"

    print()
    print("=" * 60)
    print("GSVAI INVOICE AUTOMATION: UPLOAD TO OBJECT STORAGE")
    print("=" * 60)
    print(f"Uploading invoice object: {object_name}")

    with open(file_path, "rb") as file:
        object_storage_client.put_object(
            namespace_name=OCI_OBJECT_STORAGE_NAMESPACE,
            bucket_name=OCI_DOCUMENT_BUCKET,
            object_name=object_name,
            put_object_body=file,
        )

    print("Invoice uploaded successfully to OCI Object Storage.")
    return object_name


# ============================================================
# CREATE OCI INVOICE PROCESSOR JOB
# ============================================================

def create_invoice_processor_job(object_name: str):
    from oci.ai_document.models import (
        ObjectLocation,
        ObjectStorageLocations,
        OutputLocation,
        CreateProcessorJobDetails,
        GeneralProcessorConfig,
        DocumentKeyValueExtractionFeature,
    )

    object_location = ObjectLocation(
        namespace_name=OCI_OBJECT_STORAGE_NAMESPACE,
        bucket_name=OCI_DOCUMENT_BUCKET,
        object_name=object_name,
    )

    input_location = ObjectStorageLocations(
        object_locations=[object_location]
    )

    output_prefix = f"{INVOICE_OUTPUT_PREFIX}{uuid.uuid4()}/"

    output_location = OutputLocation(
        namespace_name=OCI_OBJECT_STORAGE_NAMESPACE,
        bucket_name=OCI_DOCUMENT_BUCKET,
        prefix=output_prefix,
    )

    # GeneralProcessorConfig with document_type="INVOICE" and KEY_VALUE_EXTRACTION
    key_value_feature = DocumentKeyValueExtractionFeature(
        feature_type="KEY_VALUE_EXTRACTION"
    )

    processor_config = GeneralProcessorConfig(
        processor_type="GENERAL",
        document_type="INVOICE",
        features=[key_value_feature],
    )

    job_details = CreateProcessorJobDetails(
        compartment_id=OCI_COMPARTMENT_ID,
        input_location=input_location,
        output_location=output_location,
        processor_config=processor_config,
        display_name="GSVAI Invoice Automation",
    )

    print()
    print("=" * 60)
    print("OCI INVOICE PROCESSOR: CREATING JOB")
    print("=" * 60)
    print(f"Compartment: {OCI_COMPARTMENT_ID}")
    print(f"Input: {object_name}")
    print(f"Output Prefix: {output_prefix}")

    try:
        response = document_client.create_processor_job(
            create_processor_job_details=job_details
        )
        job = response.data
        print(f"Invoice processor job created: {job.id}")
        print(f"Initial job status: {job.lifecycle_state}")
        return job, output_prefix

    except oci.exceptions.ServiceError as exc:
        print()
        print("OCI Invoice Document Understanding ERROR")
        print(f"Status Code: {exc.status}, Error Code: {exc.code}, Message: {exc.message}")
        raise


# ============================================================
# WAIT / POLL FOR OCI JOB COMPLETION
# ============================================================

def wait_for_invoice_processor(
    job_id: str,
    max_wait_seconds: int = 1800,
    poll_interval_seconds: int = 4,
    progress_callback: Optional[Callable[[str, int, str], None]] = None,
):
    print()
    print("Waiting for OCI Invoice Document Understanding...")
    start_time = time.time()

    while True:
        response = document_client.get_processor_job(processor_job_id=job_id)
        job = response.data
        state = job.lifecycle_state
        percent = getattr(job, "percent_complete", None)

        if percent is not None:
            print(f"Invoice job status: {state} ({percent}% complete)")
            if progress_callback:
                calc_progress = 20 + int(float(percent) * 0.6)  # Maps 0-100% OCI to 20-80% pipeline
                progress_callback("OCI_DOCUMENT_UNDERSTANDING", calc_progress, f"OCI analyzing document ({percent}% complete)")
        else:
            print(f"Invoice job status: {state}")
            if progress_callback:
                progress_callback("OCI_DOCUMENT_UNDERSTANDING", 50, f"OCI processing status: {state}")

        if state == "SUCCEEDED":
            print("OCI Invoice Document Understanding completed successfully.")
            if progress_callback:
                progress_callback("DOWNLOADING_RESULT", 85, "OCI analysis succeeded. Downloading results...")
            return job

        if state in ("FAILED", "CANCELED"):
            lifecycle_details = getattr(job, "lifecycle_details", None)
            raise RuntimeError(
                f"OCI Invoice Document Understanding job failed. State: {state}. Details: {lifecycle_details}"
            )

        elapsed = time.time() - start_time
        if elapsed >= max_wait_seconds:
            raise TimeoutError(
                f"OCI Invoice Document Understanding job timed out after {max_wait_seconds} seconds."
            )

        time.sleep(poll_interval_seconds)


# ============================================================
# DOWNLOAD OCI RESULTS
# ============================================================

def download_invoice_results(job) -> List[Dict[str, Any]]:
    output_location = job.output_location
    namespace_name = output_location.namespace_name
    bucket_name = output_location.bucket_name
    prefix = output_location.prefix

    print()
    print("Searching OCI Object Storage for invoice analysis results...")
    response = object_storage_client.list_objects(
        namespace_name=namespace_name,
        bucket_name=bucket_name,
        prefix=prefix,
    )

    objects = response.data.objects
    if not objects:
        raise RuntimeError("OCI Invoice Document Understanding completed but no output files were found.")

    print(f"Found {len(objects)} output object(s).")
    results = []

    for obj in objects:
        object_name = obj.name
        if object_name.endswith("/"):
            continue

        print(f"Reading invoice output: {object_name}")
        object_response = object_storage_client.get_object(
            namespace_name=namespace_name,
            bucket_name=bucket_name,
            object_name=object_name,
        )

        content = object_response.data.content
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")

        try:
            parsed = json.loads(content)
            results.append({"object_name": object_name, "data": parsed})
        except json.JSONDecodeError:
            results.append({"object_name": object_name, "data": content})

    if not results:
        raise RuntimeError("OCI Invoice Document Understanding returned only directory markers and no result JSON.")

    return results


# ============================================================
# EXACT OCI DOCUMENT FIELDS & LINE ITEMS PARSER
# ============================================================

HEADER_MAPPINGS = [
    # (OCI Label Name, Application Field, Display Label, Data Type)
    ("VendorName", "vendor_name", "Vendor Name", "string"),
    ("InvoiceId", "invoice_number", "Invoice Number", "string"),
    ("InvoiceDate", "invoice_date", "Invoice Date", "date"),
    ("DueDate", "due_date", "Due Date", "date"),
    ("PurchaseOrder", "po_number", "Purchase Order", "string"),
    ("Currency", "currency", "Currency", "string"),
    ("SubTotal", "subtotal", "Subtotal", "number"),
    ("TotalTax", "tax_amount", "Tax Amount", "number"),
    ("InvoiceTotal", "total_amount", "Total Amount", "number"),
    ("PaymentTerms", "payment_terms", "Payment Terms", "string"),
]


def _extract_header_fields_and_mapping(data: Any) -> Dict[str, Any]:
    """
    Parses OCI documentFields with fieldType == 'KEY_VALUE'.
    Extracts raw values and confidence scores, de-duplicates by highest confidence,
    and produces normalized application fields + field mapping metadata.
    """
    extracted_fields: Dict[str, Dict[str, Any]] = {}

    pages = data.get("pages", []) if isinstance(data, dict) else []
    for page in pages:
        if not isinstance(page, dict):
            continue

        document_fields = page.get("documentFields", [])
        for field in document_fields:
            if not isinstance(field, dict):
                continue

            field_type = field.get("fieldType")
            if field_type != "KEY_VALUE":
                continue

            # Read label name
            label_info = field.get("fieldLabel") or {}
            label_name = label_info.get("name") or field.get("fieldName", {}).get("name")
            if not label_name:
                continue

            confidence = label_info.get("confidence")
            if confidence is not None:
                try:
                    confidence = float(confidence)
                except (ValueError, TypeError):
                    confidence = None

            # Read value (prefer value, fallback to text)
            field_value_obj = field.get("fieldValue") or {}
            raw_val = field_value_obj.get("value")
            raw_text = field_value_obj.get("text")

            val = raw_val if raw_val is not None else raw_text
            if val is None or val == "":
                continue

            # Normalized storage
            norm_key = label_name.strip()
            prev = extracted_fields.get(norm_key)

            # Keep entry with highest confidence, or first non-empty
            if prev is None:
                extracted_fields[norm_key] = {
                    "raw_val": raw_val,
                    "raw_text": raw_text,
                    "confidence": confidence,
                }
            else:
                prev_conf = prev.get("confidence") or 0.0
                curr_conf = confidence or 0.0
                if curr_conf > prev_conf:
                    extracted_fields[norm_key] = {
                        "raw_val": raw_val,
                        "raw_text": raw_text,
                        "confidence": confidence,
                    }

    # Map to application fields
    invoice_header: Dict[str, Any] = {
        "vendor_name": None,
        "invoice_number": None,
        "invoice_date": None,
        "due_date": None,
        "po_number": None,
        "currency": None,
        "subtotal": None,
        "tax_amount": None,
        "total_amount": None,
        "payment_terms": None,
    }

    field_mapping_list: List[Dict[str, Any]] = []

    for oci_label, app_field, display_label, data_type in HEADER_MAPPINGS:
        match_info = extracted_fields.get(oci_label)
        if match_info:
            raw_val = match_info["raw_val"]
            raw_text = match_info["raw_text"]
            conf = match_info["confidence"]

            if data_type == "date":
                normalized_val = _normalize_date(raw_val if raw_val is not None else raw_text)
            elif data_type == "number":
                normalized_val = _normalize_number(raw_val, raw_text)
            else:
                normalized_val = str(raw_val if raw_val is not None else raw_text).strip()

            invoice_header[app_field] = normalized_val

            field_mapping_list.append({
                "application_field": app_field,
                "display_name": display_label,
                "oci_field": oci_label,
                "value": normalized_val,
                "confidence": conf,
            })
        else:
            field_mapping_list.append({
                "application_field": app_field,
                "display_name": display_label,
                "oci_field": oci_label,
                "value": None,
                "confidence": None,
            })

    return {
        "invoice": invoice_header,
        "field_mapping": field_mapping_list,
    }


def _extract_line_items_from_oci(data: Any) -> List[Dict[str, Any]]:
    """
    Correctly parses OCI line item structure:
    documentFields[] -> fieldType == 'LINE_ITEM_GROUP' -> fieldValue.items[] (LINE_ITEM)
    Each LINE_ITEM contains fieldValue.items[] (LINE_ITEM_FIELD).
    """
    line_items: List[Dict[str, Any]] = []
    line_counter = 1

    pages = data.get("pages", []) if isinstance(data, dict) else []
    for page in pages:
        if not isinstance(page, dict):
            continue

        document_fields = page.get("documentFields", [])
        for field in document_fields:
            if not isinstance(field, dict):
                continue

            field_type = field.get("fieldType")
            if field_type != "LINE_ITEM_GROUP":
                continue

            # Get the line items container
            field_value_obj = field.get("fieldValue") or {}
            raw_lines = field_value_obj.get("items") or []

            for line_obj in raw_lines:
                if not isinstance(line_obj, dict):
                    continue

                # Each LINE_ITEM has its fields in fieldValue.items
                line_val_obj = line_obj.get("fieldValue") or {}
                line_fields = line_val_obj.get("items") or []
                if not line_fields and isinstance(line_obj.get("items"), list):
                    line_fields = line_obj.get("items")

                # Extract line item fields
                field_map = {}
                for lf in line_fields:
                    if not isinstance(lf, dict):
                        continue
                    lbl = lf.get("fieldLabel") or {}
                    name = lbl.get("name") or lf.get("fieldName", {}).get("name")
                    if not name:
                        continue

                    f_val_obj = lf.get("fieldValue") or {}
                    f_val = f_val_obj.get("value")
                    f_txt = f_val_obj.get("text")
                    field_map[name.strip().lower()] = {
                        "value": f_val if f_val is not None else f_txt,
                        "text": f_txt,
                    }

                desc = field_map.get("description", {}).get("value")
                item_code = field_map.get("productcode", {}).get("value") or field_map.get("name", {}).get("value")
                qty = _normalize_number(
                    field_map.get("quantity", {}).get("value"),
                    field_map.get("quantity", {}).get("text")
                )
                unit_price = _normalize_number(
                    field_map.get("unitprice", {}).get("value"),
                    field_map.get("unitprice", {}).get("text")
                )
                tax_amt = _normalize_number(
                    field_map.get("tax", {}).get("value") or field_map.get("taxamount", {}).get("value"),
                    field_map.get("tax", {}).get("text") or field_map.get("taxamount", {}).get("text")
                )
                amount = _normalize_number(
                    field_map.get("amount", {}).get("value") or field_map.get("lineamount", {}).get("value"),
                    field_map.get("amount", {}).get("text") or field_map.get("lineamount", {}).get("text")
                )
                unit = field_map.get("unit", {}).get("value")

                # Skip completely empty lines
                if not any([desc, item_code, qty is not None, unit_price is not None, amount is not None]):
                    continue

                line_items.append({
                    "line_number": line_counter,
                    "description": str(desc).strip() if desc else None,
                    "item_number": str(item_code).strip() if item_code else None,
                    "quantity": qty,
                    "unit": str(unit).strip() if unit else None,
                    "unit_price": unit_price,
                    "tax_amount": tax_amt,
                    "line_amount": amount,
                })
                line_counter += 1

    return line_items


def extract_invoice_data(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parses and normalizes results from OCI Document Understanding.
    Returns structured header, field mappings with confidence, and line items.
    """
    invoice_header = {
        "vendor_name": None,
        "invoice_number": None,
        "invoice_date": None,
        "due_date": None,
        "po_number": None,
        "currency": None,
        "subtotal": None,
        "tax_amount": None,
        "total_amount": None,
        "payment_terms": None,
    }
    field_mapping: List[Dict[str, Any]] = []
    line_items: List[Dict[str, Any]] = []

    for result in results:
        data = result.get("data")
        if not isinstance(data, dict):
            continue

        extracted = _extract_header_fields_and_mapping(data)
        extracted_hdr = extracted["invoice"]
        extracted_map = extracted["field_mapping"]

        # Merge headers
        for k, v in extracted_hdr.items():
            if v is not None:
                invoice_header[k] = v

        # Set field mapping
        if extracted_map:
            field_mapping = extracted_map

        # Extract lines
        lines = _extract_line_items_from_oci(data)
        if lines:
            line_items.extend(lines)

    # Re-index line numbers
    for idx, item in enumerate(line_items, start=1):
        item["line_number"] = idx

    return {
        "invoice": invoice_header,
        "field_mapping": field_mapping,
        "line_items": line_items,
        "raw_result": results,
    }


# ============================================================
# SYNCHRONOUS INVOICE PROCESSING PIPELINE
# ============================================================

def process_invoice(
    file_path: str,
    filename: Optional[str] = None,
    progress_callback: Optional[Callable[[str, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Processes an invoice PDF synchronously:
    Upload -> OCI Job -> Poll -> Download -> Parse -> Return Structured Output.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Invoice file not found: {file_path}")

    original_filename = filename or os.path.basename(file_path)

    # 1. Upload to Object Storage
    if progress_callback:
        progress_callback("UPLOADING", 10, f"Uploading '{original_filename}' to OCI Object Storage...")
    object_name = upload_invoice_to_object_storage(
        file_path=file_path,
        original_filename=original_filename,
    )
    if progress_callback:
        progress_callback("UPLOADED", 15, "Invoice uploaded to Object Storage.")

    # 2. Create OCI Processor Job
    if progress_callback:
        progress_callback("CREATING_JOB", 20, "Creating OCI Document Understanding processor job...")
    job, output_prefix = create_invoice_processor_job(object_name=object_name)

    # 3. Wait for OCI Job
    completed_job = wait_for_invoice_processor(
        job_id=job.id,
        progress_callback=progress_callback,
    )

    # 4. Download Results
    if progress_callback:
        progress_callback("DOWNLOADING_RESULT", 85, "Downloading OCI analysis JSON...")
    results = download_invoice_results(completed_job)

    # 5. Extract & Normalize Fields
    if progress_callback:
        progress_callback("EXTRACTING_FIELDS", 95, "Extracting invoice fields and line items...")
    extracted = extract_invoice_data(results)

    response = {
        "status": "success",
        "document_name": original_filename,
        "processor_type": "INVOICE",
        "job_id": job.id,
        "processor_job_id": job.id,
        "job_status": completed_job.lifecycle_state,
        "oci_input_object": object_name,
        "oci_output_prefix": output_prefix,
        "invoice": extracted["invoice"],
        "field_mapping": extracted["field_mapping"],
        "line_items": extracted["line_items"],
        "raw_result": extracted["raw_result"],
    }

    print()
    print("=" * 60)
    print("GSVAI INVOICE PROCESSING COMPLETED")
    print("=" * 60)
    print(f"Filename: {original_filename}")
    print(f"Job ID: {job.id}")
    print(f"Job Status: {completed_job.lifecycle_state}")
    print(f"Invoice Number: {response['invoice']['invoice_number']}")
    print(f"Vendor: {response['invoice']['vendor_name']}")
    print(f"Invoice Date: {response['invoice']['invoice_date']}")
    print(f"Total: {response['invoice']['total_amount']}")
    print(f"Line Items: {len(response['line_items'])}")
    print("=" * 60)

    if progress_callback:
        progress_callback("COMPLETED", 100, "Invoice processed and normalized successfully.")

    return response


# ============================================================
# ASYNCHRONOUS BACKGROUND WORKER
# ============================================================

def run_invoice_background_job(
    processing_id: str,
    file_path: str,
    original_filename: str,
):
    """
    Background worker executed via FastAPI BackgroundTasks.
    Safely executes process_invoice, continuously updates state manager,
    and guarantees temporary file cleanup.
    """
    print(f"[processing_id={processing_id}] Starting background invoice worker for: {original_filename}")

    def on_progress(stage: str, progress: int, message: str):
        invoice_state_manager.update_task(
            processing_id=processing_id,
            stage=stage,
            status="PROCESSING" if stage != "COMPLETED" else "COMPLETED",
            progress=progress,
            message=message,
        )
        print(f"[processing_id={processing_id}] Stage={stage}, Progress={progress}%, Message='{message}'")

    try:
        result = process_invoice(
            file_path=file_path,
            filename=original_filename,
            progress_callback=on_progress,
        )

        # Persist extracted invoice into Oracle Database
        invoice_id = None
        try:
            from services.invoice_db_service import save_invoice
            invoice_id = save_invoice(
                invoice_result=result,
                document_name=original_filename,
            )
            print(f"[processing_id={processing_id}] Invoice persisted to Oracle DB (INVOICE_ID = {invoice_id})")
        except Exception as db_err:
            print(f"[processing_id={processing_id}] Warning: Oracle DB persistence error: {db_err}")

        invoice_state_manager.update_task(
            processing_id=processing_id,
            stage="COMPLETED",
            status="COMPLETED",
            progress=100,
            message="Invoice processed and persisted to Oracle DB successfully.",
            job_id=result.get("job_id"),
            object_name=result.get("oci_input_object"),
            result={
                "processing_id": processing_id,
                "invoice_id": invoice_id,
                "status": "COMPLETED",
                "document_name": original_filename,
                "processor_type": "INVOICE",
                "job_id": result.get("job_id"),
                "invoice": result["invoice"],
                "field_mapping": result["field_mapping"],
                "line_items": result["line_items"],
            },
        )
        print(f"[processing_id={processing_id}] Pipeline completed successfully.")

    except Exception as e:
        print()
        print(f"[processing_id={processing_id}] BACKGROUND INVOICE PROCESSING ERROR: {e}")
        invoice_state_manager.update_task(
            processing_id=processing_id,
            stage="FAILED",
            status="FAILED",
            error=str(e),
            message=f"Processing failed: {e}",
        )

    finally:
        # Cleanup temporary file and its enclosing directory
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        parent_dir = os.path.dirname(file_path)
        if os.path.exists(parent_dir) and "tmp" in parent_dir.lower():
            try:
                os.rmdir(parent_dir)
            except Exception:
                pass