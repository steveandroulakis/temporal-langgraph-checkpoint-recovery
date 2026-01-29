"""Shared data models for LangGraph agent."""

from dataclasses import dataclass


@dataclass
class AgentCheckpoint:
    """Checkpoint state for Temporal heartbeat recovery."""

    thread_id: str
    checkpoint_id: str | None = None
    superstep_count: int = 0
    current_node: str | None = None


@dataclass
class AgentInput:
    """Input to the research agent workflow."""

    query: str


@dataclass
class AgentOutput:
    """Output from the research agent activity."""

    final_report: str
    thread_id: str
    superstep_count: int
