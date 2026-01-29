"""LangGraph research agent with Temporal checkpointing.

Note: Imports are lazy to avoid loading heavy dependencies (langgraph, litellm)
in workflow sandbox context.
"""

from langgraph_agent.shared import (
    AgentCheckpoint,
    AgentInput,
    AgentOutput,
    SleepingInput,
    SleepingOutput,
    StepResult,
)

__all__ = [
    "AgentCheckpoint",
    "AgentInput",
    "AgentOutput",
    "SleepingInput",
    "SleepingOutput",
    "StepResult",
]


def __getattr__(name: str) -> object:
    """Lazy import heavy modules."""
    if name == "run_langgraph_agent":
        from langgraph_agent.activities import run_langgraph_agent

        return run_langgraph_agent
    if name == "run_sleeping_agent":
        from langgraph_agent.activities import run_sleeping_agent

        return run_sleeping_agent
    if name == "build_graph":
        from langgraph_agent.graph import build_graph

        return build_graph
    if name == "get_checkpointer":
        from langgraph_agent.graph import get_checkpointer

        return get_checkpointer
    if name == "ResearchAgentWorkflow":
        from langgraph_agent.workflow import ResearchAgentWorkflow

        return ResearchAgentWorkflow
    if name == "SleepingAgentWorkflow":
        from langgraph_agent.workflow import SleepingAgentWorkflow

        return SleepingAgentWorkflow
    if name == "run_adapter":
        from langgraph_agent.runner import run_adapter

        return run_adapter
    if name == "AgentAdapter":
        from langgraph_agent.adapters.base import AgentAdapter

        return AgentAdapter
    if name == "LangGraphAdapter":
        from langgraph_agent.adapters.langgraph import LangGraphAdapter

        return LangGraphAdapter
    if name == "SleepingAdapter":
        from langgraph_agent.adapters.sleeping import SleepingAdapter

        return SleepingAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
