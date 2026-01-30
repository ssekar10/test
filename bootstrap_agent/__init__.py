from .agent import root_agent

__all__ = ["root_agent"]


def get_agent():
    """Return the root agent for ADK to load"""
    return root_agent
