import json
import os
from typing import Any, Dict, List, Optional

# pyrefly: ignore [missing-import]
import oracledb

from services.oracle_db_service import get_connection


# =========================================================
# Document Intelligence Database Persistence Service
# =========================================================

def save_document_intelligence_result(result_dict: dict) -> int:
    """
    Persists the completed Document Intelligence analysis result into
    the GSVAI_DOCUMENT_INTELLIGENCE Oracle table.

    Returns the generated ANALYSIS_ID.
    """
    if not result_dict:
        raise ValueError("No Document Intelligence result provided for persistence.")

    print()
    print("=" * 60)
    print("PERSISTING DOCUMENT INTELLIGENCE RESULT")
    print("=" * 60)

    filename = result_dict.get("filename", "document.pdf")
    job_id = result_dict.get("job_id")
    job_status = result_dict.get("job_status")
    document_type = result_dict.get("document_type", "PDF")
    page_count = result_dict.get("pages", 0)
    text_page_count = result_dict.get("text_pages", 0)
    ocr_required_pages = result_dict.get("ocr_required_pages", 0)
    ocr_status = result_dict.get("ocr_status")
    text_extraction_status = result_dict.get("text_extraction_status")
    confidence = result_dict.get("confidence")
    extracted_text_preview = result_dict.get("extracted_text_preview")
    full_text = result_dict.get("full_text")

    # Serialize JSON structures
    entities_json = json.dumps(result_dict.get("entities", []), ensure_ascii=False)
    tables_json = json.dumps(result_dict.get("tables", []), ensure_ascii=False)
    pipeline_json = json.dumps(result_dict.get("pipeline", {}), ensure_ascii=False)

    oci_info = result_dict.get("oci") or {}
    oci_input_object = oci_info.get("input_object")
    output_loc = oci_info.get("output_location") or {}
    oci_output_prefix = output_loc.get("prefix")

    print(f"Document Name          : {filename}")
    print(f"OCI Job ID             : {job_id}")
    print(f"Job Status             : {job_status}")
    print(f"Pages                  : {page_count}")
    print(f"Text Pages             : {text_page_count}")
    print(f"OCR Required Pages     : {ocr_required_pages}")
    print(f"OCR Status             : {ocr_status}")
    print(f"Text Extraction Status : {text_extraction_status}")
    print(f"Confidence             : {confidence}")

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        analysis_id_var = cursor.var(oracledb.NUMBER)

        sql = """
        INSERT INTO GSVAI_DOCUMENT_INTELLIGENCE (
            JOB_ID,
            JOB_STATUS,
            DOCUMENT_NAME,
            DOCUMENT_TYPE,
            PAGE_COUNT,
            TEXT_PAGE_COUNT,
            OCR_REQUIRED_PAGES,
            OCR_STATUS,
            TEXT_EXTRACTION_STATUS,
            CONFIDENCE,
            EXTRACTED_TEXT_PREVIEW,
            FULL_TEXT,
            ENTITIES_JSON,
            TABLES_JSON,
            PIPELINE_JSON,
            OCI_INPUT_OBJECT,
            OCI_OUTPUT_PREFIX,
            CREATED_AT
        ) VALUES (
            :job_id,
            :job_status,
            :document_name,
            :document_type,
            :page_count,
            :text_page_count,
            :ocr_required_pages,
            :ocr_status,
            :text_extraction_status,
            :confidence,
            :extracted_text_preview,
            :full_text,
            :entities_json,
            :tables_json,
            :pipeline_json,
            :oci_input_object,
            :oci_output_prefix,
            SYSTIMESTAMP
        )
        RETURNING ANALYSIS_ID INTO :analysis_id_out
        """

        cursor.execute(
            sql,
            job_id=job_id,
            job_status=job_status,
            document_name=filename,
            document_type=document_type,
            page_count=page_count,
            text_page_count=text_page_count,
            ocr_required_pages=ocr_required_pages,
            ocr_status=ocr_status,
            text_extraction_status=text_extraction_status,
            confidence=confidence,
            extracted_text_preview=extracted_text_preview,
            full_text=full_text,
            entities_json=entities_json,
            tables_json=tables_json,
            pipeline_json=pipeline_json,
            oci_input_object=oci_input_object,
            oci_output_prefix=oci_output_prefix,
            analysis_id_out=analysis_id_var,
        )

        analysis_id = int(analysis_id_var.getvalue()[0])
        connection.commit()

        print(f"Document Intelligence result saved successfully. ANALYSIS_ID = {analysis_id}")
        print("=" * 60)

        return analysis_id

    except Exception as e:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
        print(f"ERROR: Failed to persist Document Intelligence result: {e}")
        raise RuntimeError(f"Database persistence failed: {e}") from e

    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if connection:
            try:
                connection.close()
            except Exception:
                pass


# =========================================================
# Document Intelligence Retrieval Functions
# =========================================================

def get_document_intelligence_records() -> List[Dict[str, Any]]:
    """
    Retrieves recent Document Intelligence analysis records ordered by CREATED_AT DESC.
    Does not include FULL_TEXT in the list payload for efficiency.
    """
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = """
        SELECT
            ANALYSIS_ID,
            JOB_ID,
            JOB_STATUS,
            DOCUMENT_NAME,
            DOCUMENT_TYPE,
            PAGE_COUNT,
            TEXT_PAGE_COUNT,
            OCR_REQUIRED_PAGES,
            OCR_STATUS,
            TEXT_EXTRACTION_STATUS,
            CONFIDENCE,
            EXTRACTED_TEXT_PREVIEW,
            CREATED_AT
        FROM GSVAI_DOCUMENT_INTELLIGENCE
        ORDER BY CREATED_AT DESC, ANALYSIS_ID DESC
        """

        cursor.execute(sql)
        rows = cursor.fetchall()

        records = []
        for row in rows:
            created_at_str = row[12].isoformat() if row[12] else None

            records.append({
                "analysis_id": row[0],
                "job_id": row[1],
                "job_status": row[2],
                "document_name": row[3],
                "document_type": row[4],
                "page_count": row[5],
                "text_page_count": row[6],
                "ocr_required_pages": row[7],
                "ocr_status": row[8],
                "text_extraction_status": row[9],
                "confidence": row[10],
                "extracted_text_preview": row[11],
                "created_at": created_at_str,
            })

        return records

    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if connection:
            try:
                connection.close()
            except Exception:
                pass


def get_document_intelligence_result(analysis_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single complete Document Intelligence analysis record by ANALYSIS_ID.
    Deserializes ENTITIES_JSON, TABLES_JSON, and PIPELINE_JSON back into Python objects.
    """
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = """
        SELECT
            ANALYSIS_ID,
            JOB_ID,
            JOB_STATUS,
            DOCUMENT_NAME,
            DOCUMENT_TYPE,
            PAGE_COUNT,
            TEXT_PAGE_COUNT,
            OCR_REQUIRED_PAGES,
            OCR_STATUS,
            TEXT_EXTRACTION_STATUS,
            CONFIDENCE,
            EXTRACTED_TEXT_PREVIEW,
            FULL_TEXT,
            ENTITIES_JSON,
            TABLES_JSON,
            PIPELINE_JSON,
            OCI_INPUT_OBJECT,
            OCI_OUTPUT_PREFIX,
            CREATED_AT
        FROM GSVAI_DOCUMENT_INTELLIGENCE
        WHERE ANALYSIS_ID = :analysis_id
        """

        cursor.execute(sql, analysis_id=analysis_id)
        row = cursor.fetchone()

        if not row:
            return None

        # Read CLOB fields safely
        full_text = row[12].read() if hasattr(row[12], "read") else (row[12] or "")
        entities_raw = row[13].read() if hasattr(row[13], "read") else (row[13] or "")
        tables_raw = row[14].read() if hasattr(row[14], "read") else (row[14] or "")
        pipeline_raw = row[15].read() if hasattr(row[15], "read") else (row[15] or "")

        # Deserialize JSON structures
        try:
            entities = json.loads(entities_raw) if entities_raw else []
        except Exception:
            entities = []

        try:
            tables = json.loads(tables_raw) if tables_raw else []
        except Exception:
            tables = []

        try:
            pipeline = json.loads(pipeline_raw) if pipeline_raw else {}
        except Exception:
            pipeline = {}

        created_at_str = row[18].isoformat() if row[18] else None

        return {
            "analysis_id": row[0],
            "job_id": row[1],
            "job_status": row[2],
            "document_name": row[3],
            "document_type": row[4],
            "page_count": row[5],
            "text_page_count": row[6],
            "ocr_required_pages": row[7],
            "ocr_status": row[8],
            "text_extraction_status": row[9],
            "confidence": row[10],
            "extracted_text_preview": row[11],
            "full_text": full_text,
            "entities": entities,
            "tables": tables,
            "pipeline": pipeline,
            "oci_input_object": row[16],
            "oci_output_prefix": row[17],
            "created_at": created_at_str,
        }

    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if connection:
            try:
                connection.close()
            except Exception:
                pass
