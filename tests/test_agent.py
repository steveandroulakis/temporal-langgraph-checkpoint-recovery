"""Tests for LangGraph agent data models."""

from langgraph_agent.shared import (
    AgentCheckpoint,
    AgentInput,
    AgentOutput,
    ApprovalResponse,
)


def test_agent_input_creation() -> None:
    """Test AgentInput dataclass creation."""
    input = AgentInput(query="test query")
    assert input.query == "test query"
    assert input.needs_approval is False
    assert input.resume_value is None


def test_agent_input_with_approval() -> None:
    """Test AgentInput with approval flag."""
    input = AgentInput(query="test", needs_approval=True)
    assert input.needs_approval is True


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
    assert output.interrupted is False
    assert output.interrupt_value is None


def test_agent_output_interrupted() -> None:
    """Test AgentOutput with interrupt."""
    output = AgentOutput(
        final_report="",
        thread_id="thread-456",
        superstep_count=2,
        interrupted=True,
        interrupt_value={"message": "approval needed"},
    )
    assert output.interrupted is True
    assert output.interrupt_value == {"message": "approval needed"}


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


def test_approval_response_creation() -> None:
    """Test ApprovalResponse dataclass creation."""
    response = ApprovalResponse(approved=True)
    assert response.approved is True
    assert response.feedback == ""


def test_approval_response_with_feedback() -> None:
    """Test ApprovalResponse with feedback."""
    response = ApprovalResponse(approved=False, feedback="needs more detail")
    assert response.approved is False
    assert response.feedback == "needs more detail"
