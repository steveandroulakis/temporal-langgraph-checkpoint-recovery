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


@dataclass
class StepResult:
    """Result from a single adapter step."""

    step_number: int
    step_name: str
    checkpoint_id: str | None = None


@dataclass
class SleepingInput:
    """Input for the sleeping agent."""

    sleep_seconds: float = 30.0
    num_steps: int = 4


@dataclass
class SleepingOutput:
    """Output from the sleeping agent."""

    steps_completed: int
    total_sleep_time: float
