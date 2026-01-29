"""Shared data models for LangGraph agent."""

from dataclasses import dataclass
from typing import Any


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
    needs_approval: bool = False
    resume_value: dict[str, Any] | None = None  # Approval response (internal)


@dataclass
class AgentOutput:
    """Output from the research agent activity."""

    final_report: str
    thread_id: str
    superstep_count: int
    interrupted: bool = False
    interrupt_value: Any = None


@dataclass
class ApprovalResponse:
    """Human approval response for interrupted workflows."""

    approved: bool
    feedback: str = ""
