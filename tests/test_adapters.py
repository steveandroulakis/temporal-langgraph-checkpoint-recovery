"""Tests for agent adapters and related components."""

import pytest

from langgraph_agent.shared import (
    AgentCheckpoint,
    SleepingInput,
    SleepingOutput,
    StepResult,
)


class TestStepResult:
    """Tests for StepResult dataclass."""

    def test_step_result_creation(self) -> None:
        """Test basic StepResult creation."""
        result = StepResult(step_number=1, step_name="search")
        assert result.step_number == 1
        assert result.step_name == "search"
        assert result.checkpoint_id is None

    def test_step_result_with_checkpoint(self) -> None:
        """Test StepResult with checkpoint_id."""
        result = StepResult(
            step_number=2,
            step_name="analyze",
            checkpoint_id="cp-123abc",
        )
        assert result.checkpoint_id == "cp-123abc"


class TestSleepingInputOutput:
    """Tests for SleepingInput and SleepingOutput dataclasses."""

    def test_sleeping_input_defaults(self) -> None:
        """Test SleepingInput default values."""
        input = SleepingInput()
        assert input.sleep_seconds == 30.0
        assert input.num_steps == 4

    def test_sleeping_input_custom(self) -> None:
        """Test SleepingInput with custom values."""
        input = SleepingInput(sleep_seconds=10.0, num_steps=2)
        assert input.sleep_seconds == 10.0
        assert input.num_steps == 2

    def test_sleeping_output_creation(self) -> None:
        """Test SleepingOutput creation."""
        output = SleepingOutput(steps_completed=4, total_sleep_time=120.0)
        assert output.steps_completed == 4
        assert output.total_sleep_time == 120.0


class TestLangGraphAdapter:
    """Tests for LangGraphAdapter."""

    def test_supports_checkpointing(self) -> None:
        """Test that LangGraphAdapter supports checkpointing."""
        from langgraph_agent.adapters.langgraph import LangGraphAdapter

        adapter = LangGraphAdapter()
        assert adapter.supports_checkpointing is True


class TestSleepingAdapter:
    """Tests for SleepingAdapter."""

    def test_supports_checkpointing(self) -> None:
        """Test that SleepingAdapter does NOT support checkpointing."""
        from langgraph_agent.adapters.sleeping import SleepingAdapter

        adapter = SleepingAdapter()
        assert adapter.supports_checkpointing is False

    @pytest.mark.asyncio
    async def test_setup_ignores_checkpoint(self) -> None:
        """Test that setup ignores checkpoint (always starts fresh)."""
        from langgraph_agent.adapters.sleeping import SleepingAdapter

        adapter = SleepingAdapter()
        checkpoint = AgentCheckpoint(
            thread_id="test-thread",
            superstep_count=3,
            checkpoint_id="cp-123",
        )
        # Should not raise, just ignores checkpoint
        await adapter.setup("test-thread", checkpoint)

    @pytest.mark.asyncio
    async def test_run_yields_correct_steps(self) -> None:
        """Test that run yields correct number of steps."""
        from langgraph_agent.adapters.sleeping import SleepingAdapter

        adapter = SleepingAdapter()
        await adapter.setup("test-thread", None)

        # Use very short sleep for test
        input = SleepingInput(sleep_seconds=0.01, num_steps=3)

        steps = []
        async for step in adapter.run(input):
            steps.append(step)

        assert len(steps) == 3
        assert steps[0].step_number == 1
        assert steps[0].step_name == "sleep_1"
        assert steps[0].checkpoint_id is None
        assert steps[2].step_number == 3
        assert steps[2].step_name == "sleep_3"

    @pytest.mark.asyncio
    async def test_get_final_output(self) -> None:
        """Test final output after run completes."""
        from langgraph_agent.adapters.sleeping import SleepingAdapter

        adapter = SleepingAdapter()
        await adapter.setup("test-thread", None)

        input = SleepingInput(sleep_seconds=0.01, num_steps=2)

        async for _ in adapter.run(input):
            pass

        output = await adapter.get_final_output()
        assert output.steps_completed == 2
        assert output.total_sleep_time == pytest.approx(0.02, abs=0.01)
