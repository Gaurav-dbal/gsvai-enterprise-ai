from typing import Callable, Any


class AgentRouter:
    """
    Routes an analyzed email to the appropriate AI agent.
    """

    def __init__(self):
        self.routes: dict[str, Callable] = {}

    def register_agent(
        self,
        action: str,
        agent: Callable,
    ) -> None:
        """Register an agent for a routing action."""

        self.routes[action] = agent

    def route(
        self,
        action: str,
        email: dict[str, Any],
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Route an email to the appropriate agent."""

        agent = self.routes.get(action)

        if not agent:
            return {
                "status": "NO_AGENT",
                "action": action,
                "message": f"No agent registered for action: {action}",
            }

        return agent(
            email=email,
            analysis=analysis,
        )