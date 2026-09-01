from services.agent_router import AgentRouter

from agents.invoice_agent import invoice_agent
from agents.rag_agent import rag_agent


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


def route_email(
    email: dict,
    analysis: dict,
) -> dict:
    """
    Route an analyzed email to the appropriate agent.
    """

    action = analysis.get(
        "recommended_action"
    )

    if not action:
        return {
            "status": "NO_ACTION",
            "message": (
                "No recommended action was provided "
                "by the email analyzer."
            ),
        }

    return agent_router.route(
        action=action,
        email=email,
        analysis=analysis,
    )