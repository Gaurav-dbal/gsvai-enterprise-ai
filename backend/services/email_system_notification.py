"""
services/email_system_notification.py

Deterministic detection for Microsoft 365 Exchange Non-Delivery Reports (NDRs),
delivery failure notifications, and mailer-daemon bounce messages.

Evaluates multiple correlated signals (sender address, display name, subject prefix,
and diagnostic body indicators) to prevent automated mail delivery failures
from entering the Groq LLM analysis, RAG, or autonomous business agent pipelines.

Preserves normal business emails that happen to discuss delivery or shipments.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Correlated Detection Signals & Patterns
# ============================================================

# Definite System Sender Patterns
SYSTEM_SENDER_PATTERNS = [
    re.compile(r"^microsoftexchange[0-9a-f_-]*@", re.IGNORECASE),
    re.compile(r"^postmaster@", re.IGNORECASE),
    re.compile(r"^mailer[-_]daemon@", re.IGNORECASE),
    re.compile(r"^daemon@", re.IGNORECASE),
]

# System Sender Display Names
SYSTEM_SENDER_NAMES = [
    "microsoft exchange",
    "microsoft outlook",
    "mail delivery subsystem",
    "mail delivery system",
    "internet mail delivery",
    "mailer-daemon",
    "postmaster",
]

# Standard Exchange & RFC 3464 DSN Subject Patterns
NDR_SUBJECT_PATTERNS = [
    re.compile(r"^undeliverable\s*:", re.IGNORECASE),
    re.compile(r"^undelivered mail returned to sender", re.IGNORECASE),
    re.compile(r"^delivery has failed", re.IGNORECASE),
    re.compile(r"^mail delivery failed", re.IGNORECASE),
    re.compile(r"^delivery status notification\s*\(\s*failure\s*\)", re.IGNORECASE),
    re.compile(r"^failure notice", re.IGNORECASE),
    re.compile(r"^returned mail\s*:", re.IGNORECASE),
    re.compile(r"^non[- ]delivery report", re.IGNORECASE),
    re.compile(r"^\[ndr\]", re.IGNORECASE),
    re.compile(r"^ndr\s*:", re.IGNORECASE),
    re.compile(r"^message could not be delivered", re.IGNORECASE),
    re.compile(r"^unsuccessful mail delivery", re.IGNORECASE),
]

# Technical DSN / Exchange Failure Body Indicators
NDR_BODY_PHRASES = [
    "delivery has failed to these recipients or groups",
    "your message couldn't be delivered",
    "your message could not be delivered",
    "the following organization rejected your message",
    "diagnostic-code: smtp;",
    "action: failed",
    "final-recipient: rfc822;",
    "remote server returned '550",
    "remote server returned '554",
    "550 5.1.1",
    "554 5.4.4",
    "a communication failure occurred during the delivery",
    "the recipient's email address isn't correct",
    "i'm afraid i wasn't able to deliver your message",
    "this is a permanent error; i've given up",
    "was not delivered to the following",
]


# ============================================================
# Helpers to Extract Standard Fields from Varying Schemas
# ============================================================

def _extract_sender(email: Any) -> Tuple[str, str]:
    """Extracts (sender_address, sender_name) from email dict or object (case-insensitive keys)."""
    sender_addr = ""
    sender_name = ""

    if isinstance(email, dict):
        # Support both lowercase and uppercase (Oracle DB) keys
        s_addr = email.get("sender_email") or email.get("SENDER_EMAIL")
        s_name = email.get("sender_name") or email.get("SENDER_NAME")
        if s_addr:
            sender_addr = str(s_addr).strip()
        if s_name:
            sender_name = str(s_name).strip()

        # 2. Microsoft Graph message: sender or from object
        if not sender_addr and email.get("sender"):
            s_obj = email["sender"]
            if isinstance(s_obj, dict):
                ea = s_obj.get("emailAddress", {})
                sender_addr = ea.get("address", "").strip()
                sender_name = ea.get("name", "").strip()
        elif not sender_addr and email.get("from"):
            f_obj = email["from"]
            if isinstance(f_obj, dict):
                ea = f_obj.get("emailAddress", {})
                sender_addr = ea.get("address", "").strip()
                sender_name = ea.get("name", "").strip()
    elif hasattr(email, "sender_email"):
        sender_addr = str(getattr(email, "sender_email") or "").strip()
        if hasattr(email, "sender_name"):
            sender_name = str(getattr(email, "sender_name") or "").strip()

    return sender_addr.lower(), sender_name.lower()


def _extract_subject(email: Any) -> str:
    """Extracts subject line string (case-insensitive keys)."""
    if isinstance(email, dict):
        subj = email.get("subject") or email.get("SUBJECT")
        return str(subj or "").strip()
    elif hasattr(email, "subject"):
        return str(getattr(email, "subject") or "").strip()
    return ""


def _extract_body(email: Any) -> str:
    """Extracts raw body string (case-insensitive keys)."""
    body_val = ""
    if isinstance(email, dict):
        b = email.get("body") if "body" in email else email.get("BODY")
        if isinstance(b, dict):
            body_val = str(b.get("content") or "")
        elif b:
            body_val = str(b)
    elif hasattr(email, "body"):
        b = getattr(email, "body")
        if isinstance(b, dict):
            body_val = str(b.get("content") or "")
        elif b:
            body_val = str(b)
    return body_val


# ============================================================
# Multi-Signal NDR / System Notification Detector
# ============================================================

def detect_system_notification(email: Any) -> Dict[str, Any]:
    """
    Evaluates whether an email is a Microsoft 365 Exchange Non-Delivery Report (NDR),
    bounce notification, or mailer-daemon delivery failure report.

    Returns a detailed diagnostic dictionary:
    {
        "is_system_notification": bool,
        "category": "exchange_ndr" | "postmaster_ndr" | "mailer_daemon_ndr" | "dsn_bounce" | "none",
        "reason": str,
        "signals": List[str]
    }
    """
    sender_addr, sender_name = _extract_sender(email)
    subject = _extract_subject(email)
    body = _extract_body(email)

    signals: List[str] = []
    category = "none"

    # Signal 1: Check System Sender Address
    is_exchange_sender = "microsoftexchange" in sender_addr
    is_postmaster_sender = sender_addr.startswith("postmaster@") or "@postmaster." in sender_addr
    is_daemon_sender = any(p.search(sender_addr) for p in SYSTEM_SENDER_PATTERNS)

    if is_exchange_sender:
        signals.append(f"sender_microsoftexchange:{sender_addr}")
        category = "exchange_ndr"
    elif is_postmaster_sender:
        signals.append(f"sender_postmaster:{sender_addr}")
        category = "postmaster_ndr"
    elif is_daemon_sender:
        signals.append(f"sender_system_daemon:{sender_addr}")
        category = "mailer_daemon_ndr"

    # Signal 2: Check System Sender Display Name
    for s_name in SYSTEM_SENDER_NAMES:
        if s_name in sender_name:
            signals.append(f"sender_name_system:{sender_name}")
            if category == "none":
                category = "dsn_bounce"
            break

    # Signal 3: Check Subject Patterns
    subject_matched_pattern = None
    for pat in NDR_SUBJECT_PATTERNS:
        if pat.search(subject):
            subject_matched_pattern = pat.pattern
            signals.append(f"subject_ndr_pattern:{subject[:50]}")
            break

    # Signal 4: Check Body Technical DSN Phrases
    body_lower = body.lower()
    matched_body_phrases: List[str] = []
    for phrase in NDR_BODY_PHRASES:
        if phrase in body_lower:
            matched_body_phrases.append(phrase)
            signals.append(f"body_dsn_phrase:{phrase}")
            if len(matched_body_phrases) >= 3:
                break

    # Decision Logic: Multi-Signal Correlation
    is_ndr = False
    reason = ""

    # Rule 1: Definite System Sender + (Subject NDR pattern OR Body DSN phrases OR Bounce keywords)
    if is_exchange_sender:
        is_ndr = True
        reason = f"Microsoft 365 Exchange System Sender detected ({sender_addr}) with delivery notification telemetry."
        category = "exchange_ndr"

    elif (is_postmaster_sender or is_daemon_sender) and (subject_matched_pattern or matched_body_phrases):
        is_ndr = True
        reason = f"System Postmaster/Mailer-Daemon sender ({sender_addr}) with DSN failure signals."
        category = category if category != "none" else "postmaster_ndr"

    elif (is_postmaster_sender or is_daemon_sender) and any(w in subject.lower() for w in ["undeliverable", "failed", "failure", "returned mail"]):
        is_ndr = True
        reason = f"System Postmaster/Mailer-Daemon sender ({sender_addr}) with failure subject."
        category = category if category != "none" else "mailer_daemon_ndr"

    # Rule 2: Unmistakable NDR Subject Prefix (e.g., 'Undeliverable:', 'Delivery Status Notification (Failure)')
    elif subject_matched_pattern and (matched_body_phrases or is_exchange_sender or is_postmaster_sender or is_daemon_sender):
        is_ndr = True
        reason = f"Standard delivery failure subject pattern ({subject[:40]}...) correlated with DSN failure telemetry."
        category = "dsn_bounce"

    # Rule 3: High-confidence DSN Body (e.g. Exchange "Delivery has failed to these recipients" header) + any NDR subject
    elif "delivery has failed to these recipients or groups" in body_lower or "your message couldn't be delivered" in body_lower:
        is_ndr = True
        reason = "Exchange delivery failure diagnostic template detected in message payload."
        category = "exchange_ndr"

    return {
        "is_system_notification": is_ndr,
        "category": category if is_ndr else "business_email",
        "reason": reason if is_ndr else "Ordinary business email (no system notification signals).",
        "signals": signals,
    }


def is_system_notification(email: Any) -> bool:
    """
    Clean, reusable boolean helper to check if an email is an NDR / delivery failure report.
    Returns True if the email is a system notification, False otherwise.
    """
    return detect_system_notification(email)["is_system_notification"]
