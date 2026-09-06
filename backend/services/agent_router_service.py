from services.agent_router import AgentRouter

from agents.invoice_agent import invoice_agent
from agents.rag_agent import rag_agent
from agents.data_agent import data_agent


def human_review_handler(email: dict, analysis: dict) -> dict:
    """Explicit human-review route for sensitive or manual compliance items."""
    return {
        "agent": "human_review",
        "status": "HUMAN_REVIEW",
        "action": "routed_to_human_review",
        "email_id": email.get("email_id"),
        "answer": None,
        "message": "Flagged for manual operator handling without AI auto-draft.",
    }


def system_notification_handler(email: dict, analysis: dict) -> dict:
    """System notification / NDR handler: audits without business agent or AI draft."""
    return {
        "agent": "system_notification",
        "status": "SYSTEM_NOTIFICATION",
        "action": "ignore_system_notification",
        "email_id": email.get("email_id"),
        "answer": None,
        "sources": [],
        "message": "Microsoft 365 Exchange NDR / delivery notification bypassed from business agent processing.",
    }


# ---------------------------------------------------------
# Create Agent Router
# ---------------------------------------------------------

agent_router = AgentRouter()


# ---------------------------------------------------------
# Register Agents
# ---------------------------------------------------------

agent_router.register_agent(
    "route_to_invoice_agent",
    invoice_agent,
)

agent_router.register_agent(
    "route_to_rag_agent",
    rag_agent,
)

agent_router.register_agent(
    "route_to_data_agent",
    data_agent,
)

agent_router.register_agent(
    "route_to_human_review",
    human_review_handler,
)

agent_router.register_agent(
    "ignore_system_notification",
    system_notification_handler,
)

agent_router.register_agent(
    "route_to_system_notification",
    system_notification_handler,
)


def route_email(
    email: dict,
    analysis: dict,
) -> dict:
    """
    Route an analyzed email to the appropriate agent.
    Falls back intelligently to rag_agent for any unhandled action
    that requires enterprise AI knowledge or drafting.
    """

    action = analysis.get("recommended_action")

    if action in ("ignore_system_notification", "route_to_system_notification") or analysis.get("email_type") == "system_notification":
        return system_notification_handler(email, analysis)

    if not action:
        action = "route_to_rag_agent"

    result = agent_router.route(
        action=action,
        email=email,
        analysis=analysis,
    )

    if result.get("status") == "NO_AGENT":
        # If action was unrecognized, fall back to rag_agent to ensure a response draft is prepared
        return rag_agent(email=email, analysis=analysis)

    return result


# Compatibility alias
route_and_execute_agent = route_email