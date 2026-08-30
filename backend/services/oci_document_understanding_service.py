# pyrefly: ignore [missing-import]

import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

# pyrefly: ignore [missing-import]
import oci

from dotenv import load_dotenv


# =========================================================
# Load Environment Variables
# =========================================================

load_dotenv()


# =========================================================
# OCI Configuration
# =========================================================

config = oci.config.from_file()

OCI_COMPARTMENT_ID = os.getenv(
    "OCI_COMPARTMENT_ID"
)

OCI_OBJECT_STORAGE_NAMESPACE = os.getenv(
    "OCI_OBJECT_STORAGE_NAMESPACE"
)

OCI_DOCUMENT_BUCKET = os.getenv(
    "OCI_DOCUMENT_BUCKET"
)


# =========================================================
# OCI Clients
# =========================================================

object_storage_client = (
    oci.object_storage.ObjectStorageClient(
        config
    )
)

document_client = (
    oci.ai_document.AIServiceDocumentClient(
        config
    )
)


# =========================================================
# Validate Configuration
# =========================================================

def validate_configuration():

    if not OCI_COMPARTMENT_ID:
        raise ValueError(
            "OCI_COMPARTMENT_ID is not configured."
        )

    if not OCI_OBJECT_STORAGE_NAMESPACE:
        raise ValueError(
            "OCI_OBJECT_STORAGE_NAMESPACE "
            "is not configured."
        )

    if not OCI_DOCUMENT_BUCKET:
        raise ValueError(
            "OCI_DOCUMENT_BUCKET is not configured."
        )


# =========================================================
# Upload Document to OCI Object Storage
# =========================================================

def upload_to_object_storage(
    file_path: str
) -> str:

    validate_configuration()

    if not os.path.exists(file_path):

        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    object_name = (
        "gsvai-document-intelligence/input/"
        f"{uuid.uuid4()}-"
        f"{os.path.basename(file_path)}"
    )

    print()
    print(
        "Uploading document to OCI Object Storage: "
        f"{object_name}"
    )

    with open(
        file_path,
        "rb"
    ) as file:

        object_storage_client.put_object(

            namespace_name=(
                OCI_OBJECT_STORAGE_NAMESPACE
            ),

            bucket_name=(
                OCI_DOCUMENT_BUCKET
            ),

            object_name=object_name,

            put_object_body=file
        )

    print(
        "Document uploaded to OCI Object Storage."
    )

    return object_name


# =========================================================
# Build OCI Object Storage Input Location
# =========================================================

def build_input_location(
    object_name: str
):

    object_location = (
        oci.ai_document.models.ObjectLocation(

            namespace_name=(
                OCI_OBJECT_STORAGE_NAMESPACE
            ),

            bucket_name=(
                OCI_DOCUMENT_BUCKET
            ),

            object_name=object_name
        )
    )

    input_location = (
        oci.ai_document.models.ObjectStorageLocations(

            object_locations=[
                object_location
            ]
        )
    )

    return input_location


# =========================================================
# Build OCI Object Storage Output Location
# =========================================================

def build_output_location():

    output_prefix = (
        "gsvai-document-intelligence/output/"
        f"{uuid.uuid4()}/"
    )

    output_location = (
        oci.ai_document.models.OutputLocation(

            namespace_name=(
                OCI_OBJECT_STORAGE_NAMESPACE
            ),

            bucket_name=(
                OCI_DOCUMENT_BUCKET
            ),

            prefix=output_prefix
        )
    )

    return output_location


# =========================================================
# Build OCI Document Understanding Processor Config
# =========================================================
#
# OCI SDK 2.184.2 confirmed models:
#
# DocumentTextExtractionFeature
# DocumentKeyValueExtractionFeature
# DocumentTableExtractionFeature
#
# =========================================================

def build_processor_config():

    # -----------------------------------------------------
    # 1. Text / OCR
    # -----------------------------------------------------

    text_feature = (
        oci.ai_document.models.DocumentTextExtractionFeature()
    )

    # -----------------------------------------------------
    # 2. Key-Value Extraction
    # -----------------------------------------------------

    key_value_feature = (
        oci.ai_document.models.DocumentKeyValueExtractionFeature()
    )

    # -----------------------------------------------------
    # 3. Table Extraction
    # -----------------------------------------------------

    table_feature = (
        oci.ai_document.models.DocumentTableExtractionFeature()
    )

    # -----------------------------------------------------
    # 4. General Processor
    # -----------------------------------------------------

    processor_config = (
        oci.ai_document.models.GeneralProcessorConfig(

            features=[
                text_feature,
                key_value_feature,
                table_feature
            ],

            is_zip_output_enabled=False
        )
    )

    return processor_config


# =========================================================
# Create OCI Document Understanding Processor Job
# =========================================================

def create_processor_job(
    object_name: str
):

    input_location = (
        build_input_location(
            object_name
        )
    )

    output_location = (
        build_output_location()
    )

    processor_config = (
        build_processor_config()
    )

    job_details = (
        oci.ai_document.models.CreateProcessorJobDetails(

            compartment_id=(
                OCI_COMPARTMENT_ID
            ),

            input_location=(
                input_location
            ),

            output_location=(
                output_location
            ),

            processor_config=(
                processor_config
            ),

            display_name=(
                "GSVAI Document Intelligence"
            )
        )
    )

    print()
    print("=" * 60)
    print("OCI DOCUMENT UNDERSTANDING")
    print("=" * 60)

    print(
        "Creating asynchronous processor job..."
    )

    # -----------------------------------------------------
    # Debug Information
    # -----------------------------------------------------

    print()
    print(
        "========== OCI PROCESSOR JOB DEBUG =========="
    )

    print(
        "Compartment ID:",
        OCI_COMPARTMENT_ID
    )

    print(
        "Input Object:",
        object_name
    )

    print(
        "Namespace:",
        OCI_OBJECT_STORAGE_NAMESPACE
    )

    print(
        "Bucket:",
        OCI_DOCUMENT_BUCKET
    )

    print(
        "Input Location:",
        input_location
    )

    print(
        "Output Location:",
        output_location
    )

    print(
        "Processor Config:",
        processor_config
    )

    print(
        "=============================================="
    )

    try:

        response = (
            document_client.create_processor_job(

                create_processor_job_details=(
                    job_details
                )
            )
        )

        job = response.data

        print()
        print(
            f"Processor job created: {job.id}"
        )

        print(
            f"Initial job status: "
            f"{job.lifecycle_state}"
        )

        return job

    except oci.exceptions.ServiceError as e:

        print()
        print(
            "OCI Document Understanding ERROR"
        )

        print(
            f"Status Code : {e.status}"
        )

        print(
            f"Error Code  : {e.code}"
        )

        print(
            f"Message     : {e.message}"
        )

        print(
            f"Request ID  : {getattr(e, 'request_id', 'N/A')}"
        )

        raise


# =========================================================
# Wait for Processor Job
# =========================================================

def wait_for_processor_job(
    job_id: str,
    max_wait_seconds: int = 1800,
    poll_interval_seconds: int = 10
):

    print()
    print(
        "Waiting for OCI Document Understanding..."
    )

    start_time = time.time()

    while True:

        response = (
            document_client.get_processor_job(
                processor_job_id=job_id
            )
        )

        job = response.data

        state = (
            job.lifecycle_state
        )

        percent = getattr(
            job,
            "percent_complete",
            None
        )

        if percent is not None:

            print(
                f"Job status: {state} "
                f"({percent}% complete)"
            )

        else:

            print(
                f"Job status: {state}"
            )

        # -------------------------------------------------
        # Successful Completion
        # -------------------------------------------------

        if state == "SUCCEEDED":

            print(
                "OCI Document Understanding "
                "completed successfully."
            )

            return job

        # -------------------------------------------------
        # Failed States
        # -------------------------------------------------

        if state in (
            "FAILED",
            "CANCELED"
        ):

            lifecycle_details = getattr(
                job,
                "lifecycle_details",
                None
            )

            raise RuntimeError(
                "OCI Document Understanding "
                f"job failed. "
                f"State: {state}. "
                f"Details: {lifecycle_details}"
            )

        # -------------------------------------------------
        # Timeout
        # -------------------------------------------------

        elapsed = (
            time.time() - start_time
        )

        if elapsed >= max_wait_seconds:

            raise TimeoutError(
                "OCI Document Understanding "
                "job timed out after "
                f"{max_wait_seconds} seconds."
            )

        time.sleep(
            poll_interval_seconds
        )


# =========================================================
# Download OCI Analysis Results
# =========================================================

def download_analysis_results(
    job
):

    output_location = (
        job.output_location
    )

    namespace_name = (
        output_location.namespace_name
    )

    bucket_name = (
        output_location.bucket_name
    )

    prefix = (
        output_location.prefix
    )

    print()
    print(
        "Searching OCI Object Storage "
        "for analysis results..."
    )

    response = (
        object_storage_client.list_objects(

            namespace_name=namespace_name,

            bucket_name=bucket_name,

            prefix=prefix
        )
    )

    objects = (
        response.data.objects
    )

    if not objects:

        raise RuntimeError(
            "OCI Document Understanding completed "
            "but no output files were found."
        )

    print(
        f"Found {len(objects)} output object(s)."
    )

    results = []

    for obj in objects:

        object_name = (
            obj.name
        )

        # -------------------------------------------------
        # Skip directory marker
        # -------------------------------------------------

        if object_name.endswith("/"):

            print(
                f"Skipping directory marker: "
                f"{object_name}"
            )

            continue

        print(
            f"Reading output: "
            f"{object_name}"
        )

        object_response = (
            object_storage_client.get_object(

                namespace_name=(
                    namespace_name
                ),

                bucket_name=(
                    bucket_name
                ),

                object_name=(
                    object_name
                )
            )
        )

        content = (
            object_response.data.content
        )

        if isinstance(
            content,
            bytes
        ):

            content = (
                content.decode(
                    "utf-8"
                )
            )

        # -------------------------------------------------
        # Parse JSON output
        # -------------------------------------------------

        try:

            parsed = (
                json.loads(
                    content
                )
            )

            results.append({

                "object_name":
                    object_name,

                "data":
                    parsed
            })

        except json.JSONDecodeError:

            results.append({

                "object_name":
                    object_name,

                "data":
                    content
            })

    if not results:

        raise RuntimeError(
            "OCI Document Understanding completed "
            "but no JSON analysis result was found."
        )

    return results


# =========================================================
# Recursive Text Extraction
# =========================================================

def _extract_text_recursive(
    value,
    text_parts=None
):

    if text_parts is None:

        text_parts = []

    # -----------------------------------------------------
    # String
    # -----------------------------------------------------

    if isinstance(
        value,
        str
    ):

        text = value.strip()

        if text:

            text_parts.append(
                text
            )

        return text_parts

    # -----------------------------------------------------
    # Dictionary
    # -----------------------------------------------------

    if isinstance(
        value,
        dict
    ):

        priority_keys = [

            "text",

            "content",

            "value",

            "textContent"
        ]

        for key in priority_keys:

            if key in value:

                candidate = (
                    value[key]
                )

                if isinstance(
                    candidate,
                    str
                ):

                    text = (
                        candidate.strip()
                    )

                    if text:

                        text_parts.append(
                            text
                        )

        for key, item in value.items():

            if key in priority_keys:

                continue

            _extract_text_recursive(
                item,
                text_parts
            )

        return text_parts

    # -----------------------------------------------------
    # List
    # -----------------------------------------------------

    if isinstance(
        value,
        list
    ):

        for item in value:

            _extract_text_recursive(
                item,
                text_parts
            )

    return text_parts


# =========================================================
# Extract Page Information
# =========================================================

def extract_page_text(
    data
):

    pages = []

    page_collection = None

    # -----------------------------------------------------
    # Locate page collection
    # -----------------------------------------------------

    if isinstance(
        data,
        dict
    ):

        for key in (
            "pages",
            "documentPages",
            "pageResults"
        ):

            if isinstance(
                data.get(key),
                list
            ):

                page_collection = (
                    data.get(key)
                )

                break

    # -----------------------------------------------------
    # Pages found
    # -----------------------------------------------------

    if page_collection:

        for index, page in enumerate(
            page_collection,
            start=1
        ):

            text_parts = []

            _extract_text_recursive(
                page,
                text_parts
            )

            unique_parts = []

            for text in text_parts:

                if text not in unique_parts:

                    unique_parts.append(
                        text
                    )

            page_text = (
                "\n".join(
                    unique_parts
                ).strip()
            )

            pages.append({

                "page_number":
                    index,

                "text":
                    page_text
            })

        return pages

    # -----------------------------------------------------
    # Fallback
    # -----------------------------------------------------

    text_parts = []

    _extract_text_recursive(
        data,
        text_parts
    )

    unique_parts = []

    for text in text_parts:

        if text not in unique_parts:

            unique_parts.append(
                text
            )

    if unique_parts:

        pages.append({

            "page_number":
                1,

            "text":
                "\n".join(
                    unique_parts
                )
        })

    return pages


# =========================================================
# Build OCR Text
# =========================================================

def build_ocr_text(
    results
):

    all_pages = []

    for result in results:

        data = result.get(
            "data"
        )

        if isinstance(
            data,
            dict
        ):

            pages = (
                extract_page_text(
                    data
                )
            )

        else:

            text_parts = []

            _extract_text_recursive(
                data,
                text_parts
            )

            pages = [

                {
                    "page_number": 1,

                    "text":
                        "\n".join(
                            text_parts
                        )
                }

            ] if text_parts else []

        for page in pages:

            all_pages.append(
                page
            )

    # -----------------------------------------------------
    # Normalize page numbers
    # -----------------------------------------------------

    normalized_pages = []

    for index, page in enumerate(
        all_pages,
        start=1
    ):

        normalized_pages.append({

            "page_number":
                index,

            "text":
                page.get(
                    "text",
                    ""
                ).strip()
        })

    # -----------------------------------------------------
    # Build complete text
    # -----------------------------------------------------

    text_blocks = []

    for page in normalized_pages:

        page_number = (
            page["page_number"]
        )

        page_text = (
            page["text"]
        )

        if page_text:

            text_blocks.append(

                f"--- [Page {page_number}] ---\n"
                f"{page_text}"
            )

    full_text = (
        "\n\n".join(
            text_blocks
        )
    )

    return (
        normalized_pages,
        full_text
    )


# =========================================================
# Build OCR Preview
# =========================================================

def build_text_preview(
    full_text: str,
    max_characters: int = 1200
):

    if not full_text:

        return (
            "No OCR text was returned "
            "by OCI Document Understanding."
        )

    if len(full_text) <= max_characters:

        return full_text

    return (
        full_text[
            :max_characters
        ]
        + "\n\n"
        + "... [Content truncated for preview]"
    )


# =========================================================
# Utility: Get First Existing Value
# =========================================================

def _first_value(
    data: Dict[str, Any],
    keys: List[str]
):

    for key in keys:

        if key in data:

            value = data[key]

            if value is not None:

                return value

    return None


# =========================================================
# Utility: Convert OCI Value to Text
# =========================================================

def _value_to_text(
    value
):

    if value is None:

        return ""

    if isinstance(
        value,
        str
    ):

        return value.strip()

    if isinstance(
        value,
        (int, float, bool)
    ):

        return str(value)

    if isinstance(
        value,
        dict
    ):

        candidate = _first_value(

            value,

            [
                "text",
                "content",
                "value",
                "textContent",
                "normalizedValue"
            ]
        )

        if candidate is not None:

            return _value_to_text(
                candidate
            )

        return json.dumps(
            value,
            ensure_ascii=False
        )

    if isinstance(
        value,
        list
    ):

        values = []

        for item in value:

            text = _value_to_text(
                item
            )

            if text:

                values.append(
                    text
                )

        return " ".join(
            values
        )

    return str(value)


# =========================================================
# Extract Key-Value Entities
# =========================================================

def extract_key_value_entities(
    results
):

    entities = []

    # -----------------------------------------------------
    # Recursive processor
    # -----------------------------------------------------

    def process(
        value,
        page_number=None
    ):

        if isinstance(
            value,
            list
        ):

            for item in value:

                process(
                    item,
                    page_number
                )

            return

        if not isinstance(
            value,
            dict
        ):

            return

        # -------------------------------------------------
        # Detect common OCI field structures
        # -------------------------------------------------

        field_name = _first_value(

            value,

            [
                "fieldName",
                "field_name",
                "fieldLabel",
                "label",
                "key",
                "name"
            ]
        )

        field_value = _first_value(

            value,

            [
                "fieldValue",
                "field_value",
                "value",
                "valueText",
                "text",
                "content"
            ]
        )

        confidence = _first_value(

            value,

            [
                "confidence",
                "confidenceScore",
                "confidence_score"
            ]
        )

        current_page = _first_value(

            value,

            [
                "pageNumber",
                "page_number",
                "page"
            ]
        )

        if current_page is None:

            current_page = page_number

        # -------------------------------------------------
        # Add actual field
        # -------------------------------------------------

        if (
            field_name is not None
            and field_value is not None
        ):

            field_name_text = (
                _value_to_text(
                    field_name
                )
            )

            field_value_text = (
                _value_to_text(
                    field_value
                )
            )

            if (
                field_name_text
                and field_value_text
            ):

                entities.append({

                    "field_name":
                        field_name_text,

                    "value":
                        field_value_text,

                    "confidence":
                        confidence,

                    "page_number":
                        current_page,

                    "validation_status":
                        "pending"
                })

        # -------------------------------------------------
        # Special key/value dictionaries
        #
        # Handles structures such as:
        #
        # {
        #     "Invoice Number": "INV-001"
        # }
        # -------------------------------------------------

        reserved_keys = {

            "pages",
            "documentPages",
            "pageResults",

            "tables",
            "tableRows",
            "rows",
            "cells",

            "fieldName",
            "field_name",
            "fieldLabel",
            "fieldValue",
            "field_value",

            "label",
            "key",
            "name",

            "value",
            "valueText",
            "text",
            "content",

            "confidence",
            "confidenceScore",
            "confidence_score",

            "pageNumber",
            "page_number",
            "page"
        }

        for key, item in value.items():

            if key in reserved_keys:

                continue

            # ---------------------------------------------
            # If dictionary item looks like a scalar,
            # treat it as possible key-value pair.
            # ---------------------------------------------

            if isinstance(
                item,
                (str, int, float, bool)
            ):

                text = _value_to_text(
                    item
                )

                if text:

                    entities.append({

                        "field_name":
                            str(key),

                        "value":
                            text,

                        "confidence":
                            None,

                        "page_number":
                            page_number,

                        "validation_status":
                            "pending"
                    })

            else:

                process(
                    item,
                    current_page
                )

    # -----------------------------------------------------
    # Process each OCI result
    # -----------------------------------------------------

    for result in results:

        data = result.get(
            "data"
        )

        process(
            data
        )

    # -----------------------------------------------------
    # Remove duplicates
    # -----------------------------------------------------

    unique_entities = []

    seen = set()

    for entity in entities:

        key = (

            entity.get(
                "field_name"
            ),

            entity.get(
                "value"
            ),

            entity.get(
                "page_number"
            )
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        unique_entities.append(
            entity
        )

    return unique_entities


# =========================================================
# Extract Tables
# =========================================================

def extract_tables(
    results
):

    tables = []

    # -----------------------------------------------------
    # Normalize table cell
    # -----------------------------------------------------

    def normalize_cell(
        cell
    ):

        if cell is None:

            return ""

        if isinstance(
            cell,
            str
        ):

            return cell.strip()

        if isinstance(
            cell,
            (int, float, bool)
        ):

            return str(cell)

        if isinstance(
            cell,
            dict
        ):

            value = _first_value(

                cell,

                [
                    "text",
                    "content",
                    "value",
                    "textContent"
                ]
            )

            if value is not None:

                return _value_to_text(
                    value
                )

            return ""

        return _value_to_text(
            cell
        )

    # -----------------------------------------------------
    # Recursive table finder
    # -----------------------------------------------------

    def find_tables(
        value,
        page_number=None
    ):

        if isinstance(
            value,
            list
        ):

            for item in value:

                find_tables(
                    item,
                    page_number
                )

            return

        if not isinstance(
            value,
            dict
        ):

            return

        current_page = _first_value(

            value,

            [
                "pageNumber",
                "page_number",
                "page"
            ]
        )

        if current_page is None:

            current_page = page_number

        # -------------------------------------------------
        # Find table collections
        # -------------------------------------------------

        table_collection = None

        for key in (
            "tables",
            "documentTables",
            "tableResults"
        ):

            candidate = value.get(
                key
            )

            if isinstance(
                candidate,
                list
            ):

                table_collection = candidate

                break

        if table_collection:

            for table in table_collection:

                if not isinstance(
                    table,
                    dict
                ):

                    continue

                rows_data = (
                    table.get("rows")
                    or table.get("tableRows")
                    or []
                )

                normalized_rows = []

                if isinstance(
                    rows_data,
                    list
                ):

                    for row in rows_data:

                        if isinstance(
                            row,
                            dict
                        ):

                            cells = (
                                row.get("cells")
                                or row.get("tableCells")
                                or []
                            )

                        elif isinstance(
                            row,
                            list
                        ):

                            cells = row

                        else:

                            cells = [row]

                        normalized_row = [

                            normalize_cell(
                                cell
                            )

                            for cell in cells
                        ]

                        if any(
                            normalized_row
                        ):

                            normalized_rows.append(
                                normalized_row
                            )

                if normalized_rows:

                    tables.append({

                        "table_number":
                            len(tables) + 1,

                        "page_number":
                            current_page,

                        "headers":
                            [],

                        "rows":
                            normalized_rows,

                        "row_count":
                            len(
                                normalized_rows
                            ),

                        "column_count":
                            max(

                                (
                                    len(row)
                                    for row
                                    in normalized_rows
                                ),

                                default=0
                            )
                    })

        # -------------------------------------------------
        # Continue recursive search
        # -------------------------------------------------

        for key, item in value.items():

            if key in (
                "tables",
                "documentTables",
                "tableResults"
            ):

                continue

            find_tables(
                item,
                current_page
            )

    # -----------------------------------------------------
    # Process results
    # -----------------------------------------------------

    for result in results:

        data = result.get(
            "data"
        )

        find_tables(
            data
        )

    return tables


# =========================================================
# Normalize Entity Name
# =========================================================

def normalize_field_name(
    field_name: str
) -> str:

    if not field_name:

        return ""

    normalized = (
        field_name
        .strip()
        .lower()
    )

    normalized = (
        normalized
        .replace(
            "-",
            "_"
        )
        .replace(
            " ",
            "_"
        )
    )

    return normalized


# =========================================================
# Validate Entity
# =========================================================

def validate_entity(
    entity: Dict[str, Any]
):

    field_name = (
        entity.get(
            "field_name",
            ""
        )
    )

    value = (
        entity.get(
            "value",
            ""
        )
    )

    confidence = (
        entity.get(
            "confidence"
        )
    )

    # -----------------------------------------------------
    # Empty value
    # -----------------------------------------------------

    if not field_name:

        return "INVALID"

    if not value:

        return "INVALID"

    # -----------------------------------------------------
    # Confidence validation
    # -----------------------------------------------------

    if confidence is not None:

        try:

            confidence_value = float(
                confidence
            )

            if confidence_value < 0:

                return "INVALID"

            if confidence_value > 1:

                # Some OCI responses may represent
                # confidence as 0-100.

                if confidence_value <= 100:

                    confidence_value = (
                        confidence_value / 100
                    )

                else:

                    return "INVALID"

            if confidence_value < 0.50:

                return "LOW_CONFIDENCE"

        except (
            ValueError,
            TypeError
        ):

            pass

    return "VALID"


# =========================================================
# Normalize and Validate Entities
# =========================================================

def normalize_and_validate_entities(
    entities
):

    normalized_entities = []

    for entity in entities:

        field_name = (
            entity.get(
                "field_name",
                ""
            )
        )

        normalized_name = (
            normalize_field_name(
                field_name
            )
        )

        normalized_entity = {

            "field_name":
                field_name,

            "normalized_field_name":
                normalized_name,

            "value":
                entity.get(
                    "value",
                    ""
                ),

            "confidence":
                entity.get(
                    "confidence"
                ),

            "page_number":
                entity.get(
                    "page_number"
                ),

            "validation_status":
                "pending"
        }

        normalized_entity[
            "validation_status"
        ] = validate_entity(
            normalized_entity
        )

        normalized_entities.append(
            normalized_entity
        )

    return normalized_entities


# =========================================================
# Calculate Overall Confidence
# =========================================================

def calculate_overall_confidence(
    entities
):

    confidence_values = []

    for entity in entities:

        confidence = (
            entity.get(
                "confidence"
            )
        )

        if confidence is None:

            continue

        try:

            value = float(
                confidence
            )

            if value > 1:

                value = value / 100

            if (
                0 <= value <= 1
            ):

                confidence_values.append(
                    value
                )

        except (
            ValueError,
            TypeError
        ):

            continue

    if not confidence_values:

        return None

    return round(

        (
            sum(
                confidence_values
            )
            /
            len(
                confidence_values
            )
        )
        * 100,

        1
    )


# =========================================================
# Complete OCI Document Intelligence Flow
# =========================================================

def analyze_document_with_oci(
    file_path: str
):

    validate_configuration()

    # -----------------------------------------------------
    # Validate Local File
    # -----------------------------------------------------

    if not os.path.exists(
        file_path
    ):

        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    filename = (
        os.path.basename(
            file_path
        )
    )

    # -----------------------------------------------------
    # 1. Upload Document
    # -----------------------------------------------------

    object_name = (
        upload_to_object_storage(
            file_path
        )
    )

    # -----------------------------------------------------
    # 2. Create OCI Processor Job
    # -----------------------------------------------------

    job = (
        create_processor_job(
            object_name
        )
    )

    # -----------------------------------------------------
    # 3. Wait for Completion
    # -----------------------------------------------------

    completed_job = (
        wait_for_processor_job(
            job.id
        )
    )

    # -----------------------------------------------------
    # 4. Download OCI Results
    # -----------------------------------------------------

    results = (
        download_analysis_results(
            completed_job
        )
    )

    # -----------------------------------------------------
    # 5. Extract OCR Text
    # -----------------------------------------------------

    pages, full_text = (
        build_ocr_text(
            results
        )
    )

    # -----------------------------------------------------
    # 6. Build OCR Preview
    # -----------------------------------------------------

    extracted_text_preview = (
        build_text_preview(
            full_text
        )
    )

    # -----------------------------------------------------
    # 7. Extract Key-Value Entities
    # -----------------------------------------------------

    raw_entities = (
        extract_key_value_entities(
            results
        )
    )

    # -----------------------------------------------------
    # 8. Normalize and Validate Entities
    # -----------------------------------------------------

    entities = (
        normalize_and_validate_entities(
            raw_entities
        )
    )

    # -----------------------------------------------------
    # 9. Extract Tables
    # -----------------------------------------------------

    tables = (
        extract_tables(
            results
        )
    )

    # -----------------------------------------------------
    # 10. Calculate Page Metrics
    # -----------------------------------------------------

    page_count = len(
        pages
    )

    pages_with_text = sum(

        1

        for page in pages

        if page.get(
            "text",
            ""
        ).strip()
    )

    ocr_required_pages = (
        max(
            page_count
            - pages_with_text,
            0
        )
    )

    # -----------------------------------------------------
    # 11. OCR Status
    # -----------------------------------------------------

    if full_text:

        ocr_status = (
            "completed"
        )

        text_extraction_status = (
            "completed"
        )

    else:

        ocr_status = (
            "completed_no_text"
        )

        text_extraction_status = (
            "no_text_returned"
        )

    # -----------------------------------------------------
    # 12. Structured Extraction Status
    # -----------------------------------------------------

    if entities:

        entity_extraction_status = (
            "completed"
        )

    else:

        entity_extraction_status = (
            "no_entities_detected"
        )

    if tables:

        table_extraction_status = (
            "completed"
        )

    else:

        table_extraction_status = (
            "no_tables_detected"
        )

    # -----------------------------------------------------
    # 13. Validation Status
    # -----------------------------------------------------

    if entities:

        invalid_count = sum(

            1

            for entity in entities

            if entity.get(
                "validation_status"
            ) == "INVALID"
        )

        if invalid_count > 0:

            validation_status = (
                "completed_with_errors"
            )

        else:

            validation_status = (
                "completed"
            )

    else:

        validation_status = (
            "no_entities_to_validate"
        )

    # -----------------------------------------------------
    # 14. Overall Confidence
    # -----------------------------------------------------

    overall_confidence = (
        calculate_overall_confidence(
            entities
        )
    )

    # -----------------------------------------------------
    # 15. Print Summary
    # -----------------------------------------------------

    print()
    print("=" * 60)
    print("GSVAI DOCUMENT INTELLIGENCE COMPLETED")
    print("=" * 60)

    print(
        f"Filename              : {filename}"
    )

    print(
        f"Processor Job ID      : "
        f"{completed_job.id}"
    )

    print(
        f"Job Status            : "
        f"{completed_job.lifecycle_state}"
    )

    print(
        f"Pages Detected        : "
        f"{page_count}"
    )

    print(
        f"Pages With Text       : "
        f"{pages_with_text}"
    )

    print(
        f"OCR Required Pages    : "
        f"{ocr_required_pages}"
    )

    print(
        f"OCR Text Length       : "
        f"{len(full_text)} characters"
    )

    print(
        f"Key-Value Entities    : "
        f"{len(entities)}"
    )

    print(
        f"Tables                : "
        f"{len(tables)}"
    )

    print(
        f"OCR Status            : "
        f"{ocr_status}"
    )

    print(
        f"Entity Extraction     : "
        f"{entity_extraction_status}"
    )

    print(
        f"Table Extraction      : "
        f"{table_extraction_status}"
    )

    print(
        f"Validation            : "
        f"{validation_status}"
    )

    print(
        f"Overall Confidence    : "
        f"{overall_confidence}"
    )

    print("=" * 60)

    # -----------------------------------------------------
    # 16. Return GSVAI Normalized Response
    # -----------------------------------------------------

    return {

        "status":
            "success",

        "filename":
            filename,

        "document_type":
            "PDF",

        "job_id":
            completed_job.id,

        "job_status":
            completed_job.lifecycle_state,

        "pages":
            page_count,

        "text_pages":
            pages_with_text,

        "ocr_required_pages":
            ocr_required_pages,

        "ocr_status":
            ocr_status,

        "text_extraction_status":
            text_extraction_status,

        "extracted_text_preview":
            extracted_text_preview,

        "full_text":
            full_text,

        "pages_text":
            pages,

        # -------------------------------------------------
        # Structured extraction
        # -------------------------------------------------

        "entities":
            entities,

        "tables":
            tables,

        # -------------------------------------------------
        # Confidence
        # -------------------------------------------------

        "confidence":
            overall_confidence,

        # -------------------------------------------------
        # Pipeline
        # -------------------------------------------------

        "pipeline": {

            "document_ingestion":
                "completed",

            "text_extraction":
                text_extraction_status,

            "ocr":
                ocr_status,

            "key_value_extraction":
                entity_extraction_status,

            "table_extraction":
                table_extraction_status,

            "entity_normalization":
                "completed"
                if entities
                else "no_entities_to_normalize",

            "validation":
                validation_status
        },

        # -------------------------------------------------
        # OCI Information
        # -------------------------------------------------

        "oci": {

            "input_object":
                object_name,

            "output_location": {

                "namespace":
                    completed_job
                    .output_location
                    .namespace_name,

                "bucket":
                    completed_job
                    .output_location
                    .bucket_name,

                "prefix":
                    completed_job
                    .output_location
                    .prefix
            }
        },

        # -------------------------------------------------
        # Raw OCI Result
        # -------------------------------------------------

        "raw_results":
            results
    }