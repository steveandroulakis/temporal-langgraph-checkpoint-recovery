"""Temporal activities using agent adapters."""

from temporalio import activity

from langgraph_agent.adapters.langgraph import LangGraphAdapter
from langgraph_agent.adapters.sleeping import SleepingAdapter
from langgraph_agent.runner import run_adapter
from langgraph_agent.shared import (
    AgentInput,
    AgentOutput,
    SleepingInput,
    SleepingOutput,
)


@activity.defn
async def run_langgraph_agent(input: AgentInput) -> AgentOutput:
    """Run the LangGraph research agent with checkpoint support."""
    return await run_adapter(LangGraphAdapter(), input)


@activity.defn
async def run_sleeping_agent(input: SleepingInput) -> SleepingOutput:
    """Run the sleeping agent (no checkpoint support)."""
    return await run_adapter(SleepingAdapter(), input)
