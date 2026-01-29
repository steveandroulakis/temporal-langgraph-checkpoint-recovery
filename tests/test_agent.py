"""Tests for LangGraph agent data models."""

from langgraph_agent.shared import (
    AgentCheckpoint,
    AgentInput,
    AgentOutput,
)


def test_agent_input_creation() -> None:
    """Test AgentInput dataclass creation."""
    input = AgentInput(query="test query")
    assert input.query == "test query"


def test_agent_output_creation() -> None:
    """Test AgentOutput dataclass creation."""
    output = AgentOutput(
        final_report="Test report",
        thread_id="thread-123",
        superstep_count=3,
    )
    assert output.final_report == "Test report"
    assert output.thread_id == "thread-123"
    assert output.superstep_count == 3


def test_agent_checkpoint_creation() -> None:
    """Test AgentCheckpoint dataclass creation."""
    checkpoint = AgentCheckpoint(thread_id="thread-789")
    assert checkpoint.thread_id == "thread-789"
    assert checkpoint.checkpoint_id is None
    assert checkpoint.superstep_count == 0
    assert checkpoint.current_node is None


def test_agent_checkpoint_with_state() -> None:
    """Test AgentCheckpoint with state."""
    checkpoint = AgentCheckpoint(
        thread_id="thread-abc",
        checkpoint_id="cp-123",
        superstep_count=5,
        current_node="analyze",
    )
    assert checkpoint.checkpoint_id == "cp-123"
    assert checkpoint.superstep_count == 5
    assert checkpoint.current_node == "analyze"
