"""LangGraph research agent with Temporal checkpointing.

Note: Imports are lazy to avoid loading heavy dependencies (langgraph, litellm)
in workflow sandbox context.
"""

from langgraph_agent.shared import (
    AgentCheckpoint,
    AgentInput,
    AgentOutput,
    ApprovalResponse,
)

__all__ = [
    "AgentCheckpoint",
    "AgentInput",
    "AgentOutput",
    "ApprovalResponse",
]


def __getattr__(name: str) -> object:
    """Lazy import heavy modules."""
    if name == "run_langgraph_agent":
        from langgraph_agent.activities import run_langgraph_agent

        return run_langgraph_agent
    if name == "build_graph":
        from langgraph_agent.graph import build_graph

        return build_graph
    if name == "get_checkpointer":
        from langgraph_agent.graph import get_checkpointer

        return get_checkpointer
    if name == "ResearchAgentWorkflow":
        from langgraph_agent.workflow import ResearchAgentWorkflow

        return ResearchAgentWorkflow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
