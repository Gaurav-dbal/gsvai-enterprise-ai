import os
import shutil
import tempfile

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Header, Depends
import uuid

# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

# pyrefly: ignore [missing-import]
import oracledb

from services.rag_service import answer_question
from services.document_ingestion_service import ingest_pdf, ingest_document_pages
from services.oci_document_understanding_service import (
    analyze_document_with_oci,
)
from services.document_intelligence_db_service import (
    save_document_intelligence_result,
    get_document_intelligence_records,
    get_document_intelligence_result,
)
from services.ai_workspace_service import (
    process_workspace_document,
    query_ai_workspace,
    get_workspace_documents_list,
)
from services.invoice_service import (
    process_invoice,
    run_invoice_background_job,
)
from services.invoice_state_service import invoice_state_manager
from services.invoice_workflow_service import process_invoice_workflow
from services.invoice_db_service import (
    save_invoice,
    get_review_queue,
    get_invoice_for_review,
    update_invoice_review,
    approve_invoice,
    reject_invoice,
    get_invoice_counts,
    get_invoice_ai_trace,
)
from services.oracle_fusion_service import (
    get_fusion_connections,
    get_fusion_connection_by_id,
    create_fusion_connection,
    update_fusion_connection,
    test_fusion_connection,
    disable_fusion_connection,
    get_fusion_invoice_metadata,
    get_invoice_field_mapping,
    save_invoice_field_mapping,
    generate_fusion_payload,
    submit_invoice_to_fusion,
    get_fusion_submission_history,
)
from services.auth_rbac_service import (
    get_current_user_context,
    require_permission,
    get_users,
    create_user,
    update_user,
    get_roles,
    update_role_permissions,
    get_audit_logs,
    log_audit_event,
)
from services.oracle_db_service import (
    get_database_sources,
    test_database_connectivity,
    get_connection,
)
from services.data_assistant_service import (
    discover_schema,
    process_data_assistant_query,
)
from services.dashboard_service import (
    get_dashboard_overview,
)

from services.email_service import EmailService

from models.email_models import (
    EmailCreateRequest,
    EmailResponse,
)

# =========================================================
# FastAPI Application
# =========================================================

app = FastAPI(
    title="GSVAI Enterprise AI Platform API",
    version="1.0.0",
    description="Backend API for GSVAI Enterprise AI Platform: OCI GenAI, Document Intelligence, Oracle Vector DB RAG, Invoice Automation, RBAC, and Oracle Fusion Cloud ERP Integration.",
)


# =========================================================
# CORS Configuration
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# Request Model
# =========================================================

class ChatRequest(BaseModel):
    question: str
    document_id: Optional[int] = None


class AIWorkspaceChatRequest(BaseModel):
    question: str
    document_id: Optional[int] = None
    scope: Optional[str] = "all"
    query_mode: Optional[str] = None
    date_filter: Optional[str] = None


# =========================================================
# Health Check
# =========================================================

@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "service": "GSVAI",
        "version": "0.1.0",
    }


# =========================================================
# Unified AI Workspace Endpoints
# =========================================================

@app.get("/ai-workspace/documents")
def ai_workspace_documents():
    """
    Returns all available indexed documents with Document Intelligence and RAG metadata.
    """
    try:
        documents = get_workspace_documents_list()
        return {
            "status": "success",
            "count": len(documents),
            "documents": documents,
        }
    except Exception as e:
        print()
        print("=" * 60)
        print("AI WORKSPACE DOCUMENTS LIST ERROR")
        print("=" * 60)
        print(str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve workspace documents: {e}",
        )


@app.post("/ai-workspace/chat")
def ai_workspace_chat(request: AIWorkspaceChatRequest):
    """
    Unified AI Workspace chat endpoint routing intelligently between
    General AI, Selected Document RAG, All Documents RAG, Document Summaries, and Date-based Summaries.
    """
    try:
        result = query_ai_workspace(
            question=request.question,
            document_id=request.document_id,
            scope=request.scope or "all",
            query_mode=request.query_mode,
        )
        return result
    except Exception as e:
        print()
        print("=" * 60)
        print("AI WORKSPACE CHAT ERROR")
        print("=" * 60)
        print(str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate answer: {e}",
        )


@app.post("/ai-workspace/upload")
async def ai_workspace_upload(
    file: UploadFile = File(...)
):
    """
    Unified AI Workspace document processing endpoint:
    Runs OCI Document Understanding OCR -> Persists to Oracle GSVAI_DOCUMENT_INTELLIGENCE ->
    Indexes into GSVAI_DOCUMENTS and GSVAI_DOCUMENT_CHUNKS with OCI Embeddings.
    """
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are currently supported for AI Workspace.",
        )

    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = process_workspace_document(
            file_path=temp_path,
            filename=file.filename
        )
        return result

    except Exception as e:
        print()
        print("=" * 60)
        print("AI WORKSPACE UPLOAD ERROR")
        print("=" * 60)
        print(str(e))
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass


# =========================================================
# Invoice Automation API (Asynchronous Lifecycle & Results)
# =========================================================

@app.post("/api/invoices/upload")
async def upload_invoice_api(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Accepts an invoice PDF, validates it, queues asynchronous OCI processing,
    and immediately returns a unique processing_id for progress polling.
    """
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files (.pdf) are supported for invoice processing.",
        )

    processing_id = str(uuid.uuid4())
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)

    file_size = 0
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = os.path.getsize(temp_path)
    except Exception as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Failed to save temporary invoice file: {e}")

    # Enforce maximum 50MB file size limit
    if file_size > 50 * 1024 * 1024:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="File size exceeds maximum 50MB limit.")

    # Initialize tracking state
    invoice_state_manager.create_task(
        processing_id=processing_id,
        filename=file.filename,
        file_size=file_size,
    )

    # Queue asynchronous background job
    background_tasks.add_task(
        run_invoice_background_job,
        processing_id=processing_id,
        file_path=temp_path,
        original_filename=file.filename,
    )

    return {
        "processing_id": processing_id,
        "status": "UPLOADED",
        "stage": "UPLOADING",
        "progress": 10,
        "filename": file.filename,
        "file_size": file_size,
        "message": "Invoice uploaded successfully. Processing queued.",
    }


@app.get("/api/invoices/{processing_id}/status")
def get_invoice_status_api(processing_id: str):
    """
    Returns the real-time processing status, active pipeline stage, and progress (0-100%).
    """
    status_data = invoice_state_manager.get_status(processing_id)
    if not status_data:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice processing job with ID '{processing_id}' not found.",
        )
    return status_data


@app.get("/api/invoices/{processing_id}/result")
def get_invoice_result_api(processing_id: str):
    """
    Returns the normalized invoice header, field mapping with confidence, and line items.
    """
    task = invoice_state_manager.get_task(processing_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice processing job with ID '{processing_id}' not found.",
        )

    if task["status"] == "FAILED":
        raise HTTPException(
            status_code=500,
            detail=f"Invoice processing failed: {task.get('error', 'Unknown error')}",
        )

    if task["status"] != "COMPLETED":
        return {
            "processing_id": processing_id,
            "status": task["status"],
            "stage": task["stage"],
            "progress": task["progress"],
            "message": task.get("message", "Invoice is currently being processed."),
        }

    return task["result"]


@app.post("/invoice/process")
async def process_invoice_endpoint(
    file: UploadFile = File(...)
):
    """
    Synchronous processing endpoint for direct testing and backward compatibility.
    """
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files (.pdf) are currently supported for Invoice Processing.",
        )

    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = process_invoice(
            file_path=temp_path,
            filename=file.filename,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process invoice: {e}",
        )

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass


# =========================================================
# RBAC & Authentication API
# =========================================================

class UserCreateRequest(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = ""
    role: Optional[str] = "USER"
    status: Optional[str] = "ACTIVE"


class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None


class RolePermissionsUpdateRequest(BaseModel):
    permissions: List[str]


@app.get("/api/auth/me")
def get_current_user_profile(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Returns the current authenticated user's profile and active permissions.
    """
    return get_current_user_context(x_user_id, x_user_role)


@app.get("/api/admin/users")
def list_users_api(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Admin: Lists all users in the system.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("USER_VIEW")(user)
    return get_users()


@app.post("/api/admin/users")
def create_user_api(
    req: UserCreateRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Admin: Creates a new user.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("USER_MANAGE")(user)
    try:
        res = create_user(req.dict())
        log_audit_event(
            action="USER_CREATED",
            resource_type="USER",
            resource_id=req.username,
            user_id=user["username"],
            details={"username": req.username, "role": req.role},
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.put("/api/admin/users/{user_id}")
def update_user_api(
    user_id: str,
    req: UserUpdateRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Admin: Updates user profile, role, or status.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("USER_MANAGE")(user)
    res = update_user(user_id, req.dict(exclude_unset=True))
    log_audit_event(
        action="USER_UPDATED",
        resource_type="USER",
        resource_id=user_id,
        user_id=user["username"],
        details=req.dict(exclude_unset=True),
    )
    return res


@app.get("/api/admin/roles")
def list_roles_api(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Admin: Lists all roles and permission matrices.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("ROLE_VIEW")(user)
    return get_roles()


@app.put("/api/admin/roles/{role_name}")
def update_role_permissions_api(
    role_name: str,
    req: RolePermissionsUpdateRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Admin: Modifies assigned permissions for a role.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("ROLE_MANAGE")(user)
    res = update_role_permissions(role_name, req.permissions)
    log_audit_event(
        action="ROLE_PERMISSIONS_UPDATED",
        resource_type="ROLE",
        resource_id=role_name,
        user_id=user["username"],
        details={"permissions": req.permissions},
    )
    return res


@app.get("/api/admin/audit-logs")
def list_audit_logs_api(
    limit: int = 100,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Admin: Returns recent system audit and security event logs.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("AUDIT_VIEW")(user)
    return get_audit_logs(limit=limit)


# =========================================================
# Oracle Fusion Connection Management API
# =========================================================

class FusionConnectionCreateRequest(BaseModel):
    connection_name: str
    base_url: str
    environment: Optional[str] = "TEST"
    authentication_type: Optional[str] = "BASIC"
    username: Optional[str] = ""
    password_secret: Optional[str] = ""
    business_unit: Optional[str] = "US1 Business Unit"
    default_currency: Optional[str] = "USD"


class FusionConnectionUpdateRequest(BaseModel):
    connection_name: Optional[str] = None
    base_url: Optional[str] = None
    environment: Optional[str] = None
    authentication_type: Optional[str] = None
    username: Optional[str] = None
    password_secret: Optional[str] = None
    business_unit: Optional[str] = None
    default_currency: Optional[str] = None


@app.get("/api/fusion/connections")
def list_fusion_connections_api(
    active_only: bool = False,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Lists all configured Oracle Fusion connections.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("FUSION_CONNECTION_VIEW")(user)
    return get_fusion_connections(active_only=active_only)


@app.post("/api/fusion/connections")
def create_fusion_connection_api(
    req: FusionConnectionCreateRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Admin: Creates a new Oracle Fusion connection with status NOT_TESTED.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("FUSION_CONNECTION_CREATE")(user)
    try:
        res = create_fusion_connection(req.dict())
        log_audit_event(
            action="FUSION_CONNECTION_CREATED",
            resource_type="FUSION_CONNECTION",
            resource_id=str(res.get("connection_id")),
            user_id=user["username"],
            details={"name": req.connection_name, "env": req.environment},
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/fusion/connections/{connection_id}")
def update_fusion_connection_api(
    connection_id: int,
    req: FusionConnectionUpdateRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Admin: Updates an existing Oracle Fusion connection.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("FUSION_CONNECTION_EDIT")(user)
    try:
        res = update_fusion_connection(connection_id, req.dict(exclude_unset=True))
        log_audit_event(
            action="FUSION_CONNECTION_UPDATED",
            resource_type="FUSION_CONNECTION",
            resource_id=str(connection_id),
            user_id=user["username"],
            details={"connection_id": connection_id},
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/fusion/connections/{connection_id}/test")
def test_fusion_connection_api(
    connection_id: int,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Performs a safe read-only connectivity test to Oracle Fusion.
    Updates status to CONNECTED or FAILED.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("FUSION_CONNECTION_TEST")(user)
    try:
        res = test_fusion_connection(connection_id)
        log_audit_event(
            action="FUSION_CONNECTION_TESTED",
            resource_type="FUSION_CONNECTION",
            resource_id=str(connection_id),
            user_id=user["username"],
            details={"status": res["status"], "message": res["message"]},
            status=res["status"],
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/fusion/connections/{connection_id}/disable")
def disable_fusion_connection_api(
    connection_id: int,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Admin: Enables or disables an Oracle Fusion connection.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("FUSION_CONNECTION_DISABLE")(user)
    try:
        res = disable_fusion_connection(connection_id)
        log_audit_event(
            action="FUSION_CONNECTION_TOGGLED",
            resource_type="FUSION_CONNECTION",
            resource_id=str(connection_id),
            user_id=user["username"],
            details=res,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/fusion/connections/{connection_id}/metadata")
def get_fusion_connection_metadata_api(
    connection_id: int,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Returns discovered schema metadata for a specific Oracle Fusion connection.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("FUSION_CONNECTION_VIEW")(user)
    return get_fusion_invoice_metadata(connection_id=connection_id)


@app.get("/api/fusion/metadata")
def get_generic_fusion_metadata_api():
    """
    Returns general Oracle Fusion metadata schema.
    """
    return get_fusion_invoice_metadata()


@app.get("/api/fusion/submissions")
def get_fusion_submissions_api(
    invoice_id: Optional[int] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Returns Oracle Fusion submission audit history.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("INVOICE_VIEW")(user)
    return get_fusion_submission_history(invoice_id=invoice_id)


# =========================================================
# Invoice Review & Human Approval API
# =========================================================

class InvoiceReviewCorrectionRequest(BaseModel):
    header_fields: Dict[str, Any]
    line_items: Optional[List[Dict[str, Any]]] = None
    reviewer: Optional[str] = "Human Reviewer"
    comments: Optional[str] = None


class InvoiceApprovalRequest(BaseModel):
    reviewer: Optional[str] = "Human Reviewer"
    comments: Optional[str] = "Approved"


class InvoiceRejectionRequest(BaseModel):
    reviewer: Optional[str] = "Human Reviewer"
    comments: str


class InvoiceFieldMappingSaveRequest(BaseModel):
    mappings: List[Dict[str, Any]]
    connection_id: Optional[int] = None


class FusionSubmissionRequest(BaseModel):
    connection_id: int
    force: Optional[bool] = False


@app.get("/api/invoices/review-queue")
def get_invoice_review_queue_api(
    status: Optional[str] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Returns all invoices in the system, optionally filtered by status.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("INVOICE_VIEW")(user)
    try:
        return get_review_queue(status_filter=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch review queue: {e}")


@app.get("/api/invoices/stats")
def get_invoice_stats_api(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Returns real invoice and document aggregate counters from Oracle DB.
    """
    try:
        return get_invoice_counts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch invoice stats: {e}")


@app.get("/api/invoices/{invoice_id}/trace")
def get_invoice_trace_api(
    invoice_id: int,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Returns complete end-to-end AI/ML/OCR processing trace for an invoice.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("INVOICE_VIEW")(user)
    try:
        trace = get_invoice_ai_trace(invoice_id)
        if not trace:
            raise HTTPException(status_code=404, detail=f"Invoice #{invoice_id} trace not found.")
        return trace
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch invoice AI trace: {e}")


@app.get("/api/invoices/{invoice_id}/review")
def get_invoice_for_review_api(
    invoice_id: int,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Returns comprehensive details for human review.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("INVOICE_REVIEW")(user)
    try:
        invoice = get_invoice_for_review(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail=f"Invoice #{invoice_id} not found.")
        return invoice
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load invoice review data: {e}")


@app.put("/api/invoices/{invoice_id}/review")
def update_invoice_review_api(
    invoice_id: int,
    request: InvoiceReviewCorrectionRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Saves human corrections while preserving original OCI extraction snapshot.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("INVOICE_EDIT")(user)
    try:
        reviewer_name = request.reviewer or user["username"] or "Human Reviewer"
        res = update_invoice_review(
            invoice_id=invoice_id,
            header_fields=request.header_fields,
            line_items=request.line_items,
            reviewer=reviewer_name,
            comments=request.comments,
        )
        log_audit_event(
            action="INVOICE_CORRECTIONS_SAVED",
            resource_type="INVOICE",
            resource_id=str(invoice_id),
            user_id=reviewer_name,
            details={"invoice_id": invoice_id, "comments": request.comments},
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save corrections: {e}")


@app.post("/api/invoices/{invoice_id}/approve")
def approve_invoice_api(
    invoice_id: int,
    request: Optional[InvoiceApprovalRequest] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Approves an invoice in REVIEW_REQUIRED state.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("INVOICE_APPROVE")(user)
    reviewer = (request.reviewer if request and request.reviewer else None) or user["username"] or "Human Reviewer"
    comments = request.comments if request else "Approved"
    try:
        res = approve_invoice(invoice_id=invoice_id, reviewer=reviewer, comments=comments)
        log_audit_event(
            action="INVOICE_APPROVED",
            resource_type="INVOICE",
            resource_id=str(invoice_id),
            user_id=reviewer,
            details={"invoice_id": invoice_id, "comments": comments},
        )
        return res
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approval failed: {e}")


@app.post("/api/invoices/{invoice_id}/reject")
def reject_invoice_api(
    invoice_id: int,
    request: InvoiceRejectionRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Rejects an invoice in REVIEW_REQUIRED state with mandatory comments.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("INVOICE_REJECT")(user)
    if not request.comments or not request.comments.strip():
        raise HTTPException(status_code=400, detail="Rejection comments are required.")
    try:
        res = reject_invoice(
            invoice_id=invoice_id,
            reviewer=user["username"] or request.reviewer or "Human Reviewer",
            comments=request.comments,
        )
        log_audit_event(
            action="INVOICE_REJECTED",
            resource_type="INVOICE",
            resource_id=str(invoice_id),
            user_id=user["username"],
            details={"invoice_id": invoice_id, "reason": request.comments},
        )
        return res
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rejection failed: {e}")


@app.get("/api/invoices/{invoice_id}/fusion-mapping")
def get_invoice_fusion_mapping_api(
    invoice_id: int,
    connection_id: Optional[int] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Returns visual field mapping for an invoice scoped to a specific Fusion connection.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("FUSION_MAPPING_VIEW")(user)
    try:
        return get_invoice_field_mapping(invoice_id, connection_id=connection_id)
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load field mappings: {e}")


@app.put("/api/invoices/{invoice_id}/fusion-mapping")
def save_invoice_fusion_mapping_api(
    invoice_id: int,
    request: InvoiceFieldMappingSaveRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Persists custom field mapping overrides for an invoice on a specific connection.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("FUSION_MAPPING_EDIT")(user)
    try:
        return save_invoice_field_mapping(invoice_id, request.mappings, connection_id=request.connection_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save field mapping: {e}")


@app.get("/api/invoices/{invoice_id}/fusion-preview")
def get_fusion_payload_preview_api(
    invoice_id: int,
    connection_id: Optional[int] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Generates exact Oracle Fusion REST JSON payload for the specified connection.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("FUSION_MAPPING_VIEW")(user)
    try:
        return generate_fusion_payload(invoice_id, connection_id=connection_id)
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Fusion payload: {e}")


@app.post("/api/invoices/{invoice_id}/fusion-submit")
def submit_invoice_to_fusion_api(
    invoice_id: int,
    request: FusionSubmissionRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Submits an approved invoice to the selected Oracle Fusion connection with idempotency.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    require_permission("FUSION_SUBMIT")(user)
    try:
        res = submit_invoice_to_fusion(
            invoice_id=invoice_id,
            connection_id=request.connection_id,
            force=request.force or False,
        )
        log_audit_event(
            action="INVOICE_SUBMITTED_TO_FUSION",
            resource_type="INVOICE",
            resource_id=str(invoice_id),
            user_id=user["username"],
            details={
                "connection_id": request.connection_id,
                "fusion_invoice_id": res.get("fusion_invoice_id"),
                "status": res.get("status"),
            },
        )
        return res
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fusion submission failed: {e}")


# =========================================================
# Chat API - RAG & General
# =========================================================

@app.post("/chat")
def chat(request: ChatRequest):

    result = query_ai_workspace(
        question=request.question,
        document_id=request.document_id,
    )

    return result


# =========================================================
# Document Ingestion API
# =========================================================

@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...)
):

    # -----------------------------------------------------
    # 1. Validate file
    # -----------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )

    if not file.filename.lower().endswith(".pdf"):

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    # -----------------------------------------------------
    # 2. Create temporary directory
    # -----------------------------------------------------

    temp_dir = tempfile.mkdtemp()

    temp_path = os.path.join(
        temp_dir,
        file.filename,
    )

    try:

        # -------------------------------------------------
        # 3. Save uploaded PDF
        # -------------------------------------------------

        with open(
            temp_path,
            "wb",
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

        print()
        print("=" * 60)
        print("PDF UPLOAD")
        print("=" * 60)

        print(
            f"Filename : {file.filename}"
        )

        print(
            f"Temp path: {temp_path}"
        )

        # -------------------------------------------------
        # 4. Ingest PDF
        # -------------------------------------------------

        result = ingest_pdf(
            temp_path
        )

        # -------------------------------------------------
        # 5. Return ingestion result
        # -------------------------------------------------

        print(
            "PDF ingestion completed successfully."
        )

        return {

            "status": "success",

            "filename": file.filename,

            "document_id":
                result["document_id"],

            "pages":
                result["pages"],

            "chunks":
                result["chunks"],

            "message":
                "Document uploaded and indexed successfully.",
        }

    except Exception as e:

        print()
        print("=" * 60)
        print("DOCUMENT INGESTION ERROR")
        print("=" * 60)

        print(
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    finally:

        # -------------------------------------------------
        # 6. Cleanup temporary PDF
        # -------------------------------------------------

        if os.path.exists(temp_path):

            try:

                os.remove(
                    temp_path
                )

            except Exception:

                pass

        if os.path.exists(temp_dir):

            try:

                os.rmdir(
                    temp_dir
                )

            except Exception:

                pass


# =========================================================
# DOCUMENT INTELLIGENCE - OCR API
# =========================================================

@app.post("/document-intelligence/analyze")
async def analyze_document_endpoint(
    file: UploadFile = File(...)
):

    """
    Analyze an uploaded PDF using OCI Document Understanding.

    Processing flow:

        React UI
            ↓
        FastAPI
            ↓
        Temporary PDF
            ↓
        OCI Object Storage
            ↓
        OCI Document Understanding
            ↓
        OCR
            ↓
        Normalized OCR response
            ↓
        React UI
    """

    # -----------------------------------------------------
    # 1. Validate file
    # -----------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )

    if not file.filename.lower().endswith(".pdf"):

        raise HTTPException(
            status_code=400,
            detail=(
                "Only PDF files are currently supported "
                "for Document Intelligence."
            ),
        )

    # -----------------------------------------------------
    # 2. Create temporary directory
    # -----------------------------------------------------

    temp_dir = tempfile.mkdtemp()

    temp_path = os.path.join(
        temp_dir,
        file.filename,
    )

    try:

        # -------------------------------------------------
        # 3. Save uploaded PDF
        # -------------------------------------------------

        with open(
            temp_path,
            "wb",
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

        print()
        print("=" * 60)
        print("GSVAI DOCUMENT INTELLIGENCE")
        print("=" * 60)

        print(
            f"Filename : {file.filename}"
        )

        print(
            f"Temp path: {temp_path}"
        )

        # -------------------------------------------------
        # 4. OCI Document Understanding
        # -------------------------------------------------

        print()
        print(
            "Starting OCI Document Understanding..."
        )

        result = analyze_document_with_oci(
            file_path=temp_path,
        )

        # -------------------------------------------------
        # 5. Persist Document Intelligence to Oracle DB
        # -------------------------------------------------

        print()
        print(
            "Persisting Document Intelligence result to Oracle..."
        )

        analysis_id = save_document_intelligence_result(
            result
        )

        result["analysis_id"] = analysis_id

        # -------------------------------------------------
        # 6. Index Extracted Text into Knowledge Base (RAG)
        # -------------------------------------------------

        print()
        print(
            "Indexing extracted text into Knowledge Base (Oracle Vector DB)..."
        )

        pages_text = result.get("pages_text")
        if pages_text and len(pages_text) > 0:
            ingest_result = ingest_document_pages(
                filename=file.filename,
                pages=pages_text,
                document_type=result.get("document_type", "PDF")
            )
        else:
            ingest_result = ingest_pdf(temp_path)

        result["document_id"] = ingest_result.get("document_id")
        result["indexing_status"] = ingest_result.get("status", "INDEXED")
        result["chunks"] = ingest_result.get("chunks", 1)

        # -------------------------------------------------
        # 7. Return OCR result
        # -------------------------------------------------

        print()
        print(
            f"OCI Document Understanding completed, persisted (ANALYSIS_ID = {analysis_id}) and indexed (DOCUMENT_ID = {result['document_id']})."
        )

        return result

    except Exception as e:

        print()
        print("=" * 60)
        print("DOCUMENT INTELLIGENCE ERROR")
        print("=" * 60)

        print(
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    finally:

        # -------------------------------------------------
        # 6. Cleanup temporary PDF
        # -------------------------------------------------

        if os.path.exists(temp_path):

            try:

                os.remove(
                    temp_path
                )

            except Exception:

                pass

        if os.path.exists(temp_dir):

            try:

                os.rmdir(
                    temp_dir
                )

            except Exception:

                pass


# =========================================================
# Document Intelligence Retrieval APIs
# =========================================================

@app.get("/document-intelligence")
def get_document_intelligence_list_endpoint():
    """
    Retrieves recent Document Intelligence analysis records.
    """
    try:
        records = get_document_intelligence_records()
        return {
            "status": "success",
            "count": len(records),
            "documents": records,
        }
    except Exception as e:
        print()
        print("=" * 60)
        print("GET DOCUMENT INTELLIGENCE LIST ERROR")
        print("=" * 60)
        print(str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve Document Intelligence records.",
        )


@app.get("/document-intelligence/{analysis_id}")
def get_document_intelligence_single_endpoint(analysis_id: int):
    """
    Retrieves a single Document Intelligence analysis result by ID.
    """
    try:
        analysis = get_document_intelligence_result(analysis_id)
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Document Intelligence record with ID {analysis_id} not found.",
            )
        return {
            "status": "success",
            "analysis": analysis,
        }
    except HTTPException:
        raise
    except Exception as e:
        print()
        print("=" * 60)
        print("GET DOCUMENT INTELLIGENCE RECORD ERROR")
        print("=" * 60)
        print(str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve Document Intelligence record.",
        )


# =========================================================
# Get Indexed Documents API
# =========================================================

@app.get("/documents")
def get_documents():

    connection = None
    cursor = None

    try:

        # -------------------------------------------------
        # 1. Load Oracle configuration
        # -------------------------------------------------

        db_user = os.getenv(
            "DB_USER"
        )

        db_password = os.getenv(
            "DB_PASSWORD"
        )

        db_dsn = os.getenv(
            "DB_DSN"
        )

        db_wallet_dir = os.getenv(
            "DB_WALLET_DIR"
        )

        db_wallet_password = os.getenv(
            "DB_WALLET_PASSWORD"
        )

        # -------------------------------------------------
        # 2. Validate configuration
        # -------------------------------------------------

        if not db_user:

            raise Exception(
                "DB_USER environment variable is not configured."
            )

        if not db_password:

            raise Exception(
                "DB_PASSWORD environment variable is not configured."
            )

        if not db_dsn:

            raise Exception(
                "DB_DSN environment variable is not configured."
            )

        # -------------------------------------------------
        # 3. Build connection parameters
        # -------------------------------------------------

        connection_params = {

            "user":
                db_user,

            "password":
                db_password,

            "dsn":
                db_dsn,
        }

        if db_wallet_dir:

            connection_params[
                "config_dir"
            ] = db_wallet_dir

            connection_params[
                "wallet_location"
            ] = db_wallet_dir

        if db_wallet_password:

            connection_params[
                "wallet_password"
            ] = db_wallet_password

        # -------------------------------------------------
        # 4. Connect to Oracle
        # -------------------------------------------------

        connection = oracledb.connect(
            **connection_params
        )

        print(
            "Oracle database connection successful."
        )

        cursor = connection.cursor()

        # -------------------------------------------------
        # 5. Query documents
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                d.DOCUMENT_ID,
                d.DOCUMENT_NAME,
                d.DOCUMENT_TYPE,
                d.SOURCE,
                d.CREATED_AT,
                d.STATUS,
                COUNT(c.CHUNK_ID) AS CHUNK_COUNT
            FROM GSVAI_DOCUMENTS d
            LEFT JOIN GSVAI_DOCUMENT_CHUNKS c
                ON d.DOCUMENT_ID = c.DOCUMENT_ID
            GROUP BY
                d.DOCUMENT_ID,
                d.DOCUMENT_NAME,
                d.DOCUMENT_TYPE,
                d.SOURCE,
                d.CREATED_AT,
                d.STATUS
            ORDER BY
                d.DOCUMENT_ID
            """
        )

        rows = cursor.fetchall()

        # -------------------------------------------------
        # 6. Convert to JSON
        # -------------------------------------------------

        documents = []

        for row in rows:

            documents.append({

                "document_id":
                    row[0],

                "document_name":
                    row[1],

                "document_type":
                    row[2],

                "source":
                    row[3],

                "created_at":
                    row[4].isoformat()
                    if row[4]
                    else None,

                "status":
                    row[5],

                "chunks":
                    row[6],
            })

        print(
            f"Documents returned: {len(documents)}"
        )

        # -------------------------------------------------
        # 7. Return
        # -------------------------------------------------

        return {

            "status":
                "success",

            "count":
                len(documents),

            "documents":
                documents,
        }

    except Exception as e:

        print()
        print("=" * 60)
        print("GET DOCUMENTS ERROR")
        print("=" * 60)

        print(
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

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
# Email Automation API
# =========================================================

email_service = EmailService()


@app.post(
    "/api/emails",
    response_model=EmailResponse,
    status_code=201,
)
def create_email(request: EmailCreateRequest):
    """
    Receives and stores an incoming email.
    """
    try:
        return email_service.create_email(request)

    except Exception as e:
        print()
        print("=" * 60)
        print("EMAIL CREATE ERROR")
        print("=" * 60)
        print(str(e))

        raise HTTPException(
            status_code=500,
            detail=f"Failed to create email: {e}",
        )


@app.get(
    "/api/emails/{email_id}",
    response_model=EmailResponse,
)
def get_email(email_id: str):
    """
    Retrieves an email by EMAIL_ID.
    """
    try:
        return email_service.get_email(email_id)

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except Exception as e:
        print()
        print("=" * 60)
        print("EMAIL RETRIEVAL ERROR")
        print("=" * 60)
        print(str(e))

        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve email: {str(e)}",
        )
@app.post(
    "/api/emails/{email_id}/analyze"
)
def analyze_email_endpoint(email_id: str):
    """
    Analyze an email using OCI Generative AI.
    """

    try:
        return email_service.analyze_email_by_id(
            email_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except Exception as e:
        print()
        print("=" * 60)
        print("EMAIL ANALYSIS ERROR")
        print("=" * 60)
        print(str(e))

        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze email: {e}",
        )


@app.post(
    "/api/emails/{email_id}/route"
)
def route_email_endpoint(email_id: str):
    """
    Analyze an email and route it to the
    appropriate AI agent.
    """

    try:
        return email_service.route_email_by_id(
            email_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except Exception as e:
        print()
        print("=" * 60)
        print("EMAIL ROUTING ERROR")
        print("=" * 60)
        print(str(e))

        raise HTTPException(
            status_code=500,
            detail=f"Failed to route email: {e}",
        )
# =========================================================
# Data Assistant & Text-to-SQL Endpoints
# =========================================================

class DataAssistantQueryRequest(BaseModel):
    question: str
    connection_id: Optional[int] = None
    max_rows: Optional[int] = 100


@app.get("/api/data-assistant/sources")
def get_data_assistant_sources_api():
    """
    Returns available real database sources for Data Assistant query execution.
    """
    return get_database_sources(active_only=True)


@app.get("/api/data-assistant/schema")
def get_data_assistant_schema_api(connection_id: Optional[int] = None):
    """
    Returns discovered tables, columns, and dynamic recommended queries from Oracle Data Dictionary.
    """
    return discover_schema(connection_id=connection_id)


@app.post("/api/data-assistant/query")
def execute_data_assistant_query_api(
    request: DataAssistantQueryRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Executes a natural language analytical question against the configured Oracle Database schema.
    Flow: User Question -> Real Schema Context -> OCI GenAI SQL -> SQL Safety Check -> Oracle DB Execution -> Results.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Query question cannot be empty.")

    return process_data_assistant_query(
        question=request.question.strip(),
        connection_id=request.connection_id,
        max_rows=request.max_rows or 100,
        user_id=user.get("username", "user_admin"),
    )


# =========================================================
# Database Connections Management API (Settings)
# =========================================================

@app.get("/api/database/connections")
def list_database_connections_api(
    active_only: bool = False,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Admin: Lists all configured Oracle Database connections.
    """
    return get_database_sources(active_only=active_only)


@app.post("/api/database/connections/{connection_id}/test")
def test_database_connection_api(
    connection_id: int,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Safely tests database connectivity and metadata accessibility without executing user SQL.
    """
    user = get_current_user_context(x_user_id, x_user_role)
    res = test_database_connectivity(connection_id)
    log_audit_event(
        action="DATABASE_CONNECTION_TESTED",
        resource_type="DATABASE_CONNECTION",
        resource_id=str(connection_id),
        user_id=user.get("username", "user_admin"),
        details={"status": res.get("status"), "message": res.get("message")},
        status=res.get("status"),
    )
    return res


# =========================================================
# Dashboard Operational Telemetry API
# =========================================================
@app.get("/api/dashboard/stats")
@app.get("/api/dashboard/overview")
def get_dashboard_stats_api(period: str = "today"):
    """
    Returns live aggregated counts, real AI model throughput, document processing pipelines,
    workflow health, and verified audit history from Oracle Autonomous Database for the Overview Dashboard.
    Zero demo data or mock fallbacks.
    """
    return get_dashboard_overview(period=period)