import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Header, HTTPException, status
from services.oracle_db_service import get_connection


# ============================================================
# 1. PERMISSION DEFINITIONS
# ============================================================

ALL_PERMISSIONS = {
    # User Management
    "USER_VIEW": "View user accounts and profiles",
    "USER_MANAGE": "Create, edit, and deactivate user accounts",

    # Role & Permission Management
    "ROLE_VIEW": "View roles and assigned permission matrices",
    "ROLE_MANAGE": "Create and modify roles and permissions",

    # Oracle Fusion Connections Management
    "FUSION_CONNECTION_VIEW": "View configured Oracle Fusion environments",
    "FUSION_CONNECTION_CREATE": "Create new Oracle Fusion connections",
    "FUSION_CONNECTION_EDIT": "Modify Oracle Fusion connection configuration",
    "FUSION_CONNECTION_TEST": "Execute connectivity and health tests on Fusion endpoints",
    "FUSION_CONNECTION_DISABLE": "Disable or enable Fusion connections",

    # Invoice Workflow Permissions
    "INVOICE_VIEW": "View invoice list and processing telemetry",
    "INVOICE_UPLOAD": "Upload invoice PDFs for extraction",
    "INVOICE_REVIEW": "Access invoice review workspace and audit comparisons",
    "INVOICE_EDIT": "Edit and correct extracted invoice header and line items",
    "INVOICE_APPROVE": "Approve reviewed invoices for ERP submission",
    "INVOICE_REJECT": "Reject invoices with required justification",

    # Fusion Mapping & Submission
    "FUSION_MAPPING_VIEW": "View field mapping between GSVAI schema and Fusion REST API",
    "FUSION_MAPPING_EDIT": "Modify field mapping overrides for Fusion connections",
    "FUSION_SUBMIT": "Submit approved invoices directly to Oracle Fusion Cloud ERP",

    # Audit & Security
    "AUDIT_VIEW": "View system-wide activity, security, and submission audit logs",
}


# ============================================================
# 2. USER & ROLE REPOSITORY (ORACLE DB PERSISTED)
# ============================================================

def get_users() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                USER_ID,
                USERNAME,
                EMAIL,
                FULL_NAME,
                ROLE,
                STATUS,
                CREATED_AT,
                UPDATED_AT
            FROM GSVAI_USERS
            ORDER BY CREATED_AT ASC
            """
        )
        cols = [d[0].lower() for d in cursor.description]
        results = []
        for row in cursor.fetchall():
            rec = dict(zip(cols, row))
            if rec.get("created_at"):
                rec["created_at"] = rec["created_at"].isoformat() + "Z" if isinstance(rec["created_at"], datetime) else str(rec["created_at"])
            if rec.get("updated_at"):
                rec["updated_at"] = rec["updated_at"].isoformat() + "Z" if isinstance(rec["updated_at"], datetime) else str(rec["updated_at"])
            results.append(rec)
        return results
    finally:
        cursor.close()
        conn.close()


def get_user_by_id(user_identifier: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                u.USER_ID,
                u.USERNAME,
                u.EMAIL,
                u.FULL_NAME,
                u.ROLE,
                u.STATUS,
                r.PERMISSIONS_JSON
            FROM GSVAI_USERS u
            LEFT JOIN GSVAI_ROLES r ON u.ROLE = r.ROLE_NAME
            WHERE u.USER_ID = :user_id OR u.USERNAME = :username
            """,
            {"user_id": user_identifier, "username": user_identifier},
        )
        row = cursor.fetchone()
        if not row:
            return None

        perms_raw = row[6]
        perms = []
        if perms_raw:
            try:
                perms = json.loads(perms_raw) if isinstance(perms_raw, str) else perms_raw
            except Exception:
                perms = []

        return {
            "user_id": row[0],
            "username": row[1],
            "email": row[2],
            "full_name": row[3],
            "role": row[4],
            "status": row[5],
            "permissions": perms,
        }
    finally:
        cursor.close()
        conn.close()


def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    new_id = f"usr_{uuid.uuid4().hex[:12]}"
    try:
        cursor.execute(
            """
            INSERT INTO GSVAI_USERS (
                USER_ID,
                USERNAME,
                EMAIL,
                FULL_NAME,
                ROLE,
                STATUS,
                CREATED_AT,
                UPDATED_AT
            )
            VALUES (
                :user_id,
                :username,
                :email,
                :full_name,
                :role,
                :status,
                SYSTIMESTAMP,
                SYSTIMESTAMP
            )
            """,
            {
                "user_id": new_id,
                "username": user_data["username"].strip().lower(),
                "email": user_data["email"].strip().lower(),
                "full_name": user_data.get("full_name", "").strip(),
                "role": user_data.get("role", "USER"),
                "status": user_data.get("status", "ACTIVE"),
            },
        )
        conn.commit()
        return {"status": "SUCCESS", "user_id": new_id, "message": f"User {user_data['username']} created."}
    except oracledb.IntegrityError:
        raise ValueError(f"User with username '{user_data['username']}' already exists.")
    finally:
        cursor.close()
        conn.close()


def update_user(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE GSVAI_USERS
            SET
                EMAIL       = COALESCE(:email, EMAIL),
                FULL_NAME   = COALESCE(:full_name, FULL_NAME),
                ROLE        = COALESCE(:role, ROLE),
                STATUS      = COALESCE(:status, STATUS),
                UPDATED_AT  = SYSTIMESTAMP
            WHERE USER_ID = :user_id OR USERNAME = :username
            """,
            {
                "email": updates.get("email"),
                "full_name": updates.get("full_name"),
                "role": updates.get("role"),
                "status": updates.get("status"),
                "user_id": user_id,
                "username": user_id,
            },
        )
        conn.commit()
        return {"status": "SUCCESS", "message": "User updated successfully."}
    finally:
        cursor.close()
        conn.close()


def get_roles() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                ROLE_NAME,
                DESCRIPTION,
                PERMISSIONS_JSON,
                IS_SYSTEM
            FROM GSVAI_ROLES
            ORDER BY ROLE_NAME ASC
            """
        )
        results = []
        for row in cursor.fetchall():
            perms_raw = row[2]
            perms = []
            if perms_raw:
                try:
                    perms = json.loads(perms_raw) if isinstance(perms_raw, str) else perms_raw
                except Exception:
                    perms = []
            results.append({
                "role_name": row[0],
                "description": row[1],
                "permissions": perms,
                "is_system": bool(row[3]),
            })
        return results
    finally:
        cursor.close()
        conn.close()


def update_role_permissions(role_name: str, permissions: List[str]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE GSVAI_ROLES
            SET
                PERMISSIONS_JSON = :perms_json,
                UPDATED_AT       = SYSTIMESTAMP
            WHERE ROLE_NAME = :role_name
            """,
            {
                "perms_json": json.dumps(permissions),
                "role_name": role_name,
            },
        )
        conn.commit()
        return {"status": "SUCCESS", "message": f"Permissions for role {role_name} updated."}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# 3. AUDIT LOGGING
# ============================================================

def log_audit_event(
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = "admin",
    details: Optional[Dict[str, Any]] = None,
    status: str = "SUCCESS",
) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO GSVAI_AUDIT_LOGS (
                USER_ID,
                ACTION,
                RESOURCE_TYPE,
                RESOURCE_ID,
                DETAILS_JSON,
                STATUS,
                CREATED_AT
            )
            VALUES (
                :user_id,
                :action,
                :resource_type,
                :resource_id,
                :details_json,
                :status,
                SYSTIMESTAMP
            )
            """,
            {
                "user_id": user_id or "system",
                "action": action,
                "resource_type": resource_type,
                "resource_id": str(resource_id) if resource_id is not None else None,
                "details_json": json.dumps(details, default=str) if details else None,
                "status": status,
            },
        )
        conn.commit()
    except Exception as e:
        print(f"Warning: Audit log error: {e}")
    finally:
        cursor.close()
        conn.close()


def get_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            SELECT
                LOG_ID,
                USER_ID,
                ACTION,
                RESOURCE_TYPE,
                RESOURCE_ID,
                DETAILS_JSON,
                STATUS,
                CREATED_AT
            FROM GSVAI_AUDIT_LOGS
            ORDER BY LOG_ID DESC
            FETCH FIRST {int(limit)} ROWS ONLY
            """
        )
        cols = [d[0].lower() for d in cursor.description]
        results = []
        for row in cursor.fetchall():
            rec = dict(zip(cols, row))
            if rec.get("created_at"):
                rec["created_at"] = rec["created_at"].isoformat() + "Z" if isinstance(rec["created_at"], datetime) else str(rec["created_at"])
            dt_raw = rec.get("details_json")
            if dt_raw:
                try:
                    rec["details"] = json.loads(dt_raw) if isinstance(dt_raw, str) else dt_raw
                except Exception:
                    rec["details"] = dt_raw
            else:
                rec["details"] = {}
            rec.pop("details_json", None)
            results.append(rec)
        return results
    finally:
        cursor.close()
        conn.close()


# ============================================================
# 4. FASTAPI DEPENDENCY: GET CURRENT USER & AUTHORIZATION
# ============================================================

def get_current_user_context(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> Dict[str, Any]:
    """
    Resolves the requesting user and their assigned permissions.
    Defaults to 'admin' (ADMIN role) for local development/demonstration
    if no specific identity header is passed.
    """
    user_key = x_user_id or "admin"
    user = get_user_by_id(user_key)

    if not user:
        # Fallback if admin not yet in DB or custom user
        role = x_user_role or "ADMIN"
        roles = {r["role_name"]: r["permissions"] for r in get_roles()}
        perms = roles.get(role, list(ALL_PERMISSIONS.keys()))
        return {
            "user_id": user_key,
            "username": user_key,
            "role": role,
            "status": "ACTIVE",
            "permissions": perms,
        }

    if user["status"] != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account '{user['username']}' is inactive or disabled.",
        )

    return user


def require_permission(required_permission: str):
    """
    Decorator/dependency factory enforcing that current_user possesses required_permission.
    Raises HTTP 403 Forbidden with descriptive detail if missing.
    """
    def permission_checker(current_user: Dict[str, Any] = None) -> Dict[str, Any]:
        # If used directly without FastAPI DI, current_user can be passed
        if current_user is None:
            current_user = get_current_user_context()

        user_perms = current_user.get("permissions", [])
        if required_permission not in user_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access Denied: Role '{current_user.get('role')}' requires permission "
                    f"'{required_permission}' to perform this operation."
                ),
            )
        return current_user

    return permission_checker
