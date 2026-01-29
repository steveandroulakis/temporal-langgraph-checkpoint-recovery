"""LangGraph research agent definition."""

import os
from typing import Annotated, Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from litellm import acompletion
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State for the research agent graph."""

    query: str
    messages: Annotated[list[Any], add_messages]
    search_results: str
    analysis: str
    final_report: str


def _get_model() -> str:
    """Get model based on available API keys."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic/claude-3-5-haiku-latest"
    return "gpt-4"


async def search_node(state: AgentState) -> dict[str, Any]:
    """Search/gather information about the query."""
    model = _get_model()
    system_msg = (
        "You are a research assistant. "
        "Gather key information about the topic. Be concise but thorough."
    )
    user_msg = f"Research topic: {state['query']}\n\nProvide key facts and findings."
    response = await acompletion(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=500,
    )
    search_results = response.choices[0].message.content
    return {"search_results": search_results}


async def analyze_node(state: AgentState) -> dict[str, Any]:
    """Analyze the gathered information."""
    model = _get_model()
    system_msg = "You are an analyst. Synthesize research findings into insights."
    user_msg = (
        f"Topic: {state['query']}\n\n"
        f"Research findings:\n{state['search_results']}\n\n"
        "Provide analysis and insights."
    )
    response = await acompletion(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=500,
    )
    analysis = response.choices[0].message.content
    return {"analysis": analysis}


async def report_node(state: AgentState) -> dict[str, Any]:
    """Generate final research report."""
    model = _get_model()

    system_msg = (
        "You are a report writer. Create a concise, well-structured research report."
    )
    user_content = f"""Topic: {state["query"]}

Research findings:
{state["search_results"]}

Analysis:
{state["analysis"]}

Write a final research report with Summary, Key Findings, and Conclusions."""

    response = await acompletion(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_content},
        ],
        max_tokens=800,
    )
    final_report = response.choices[0].message.content
    return {"final_report": final_report}


def build_graph() -> StateGraph[AgentState]:
    """Build the research agent graph."""
    builder = StateGraph(AgentState)

    builder.add_node("search", search_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("report", report_node)

    builder.set_entry_point("search")
    builder.add_edge("search", "analyze")
    builder.add_edge("analyze", "report")
    builder.add_edge("report", END)

    return builder


async def get_checkpointer(
    db_path: str = "langgraph_checkpoints.db",
) -> AsyncSqliteSaver:
    """Create async SQLite checkpointer."""
    import aiosqlite

    conn = await aiosqlite.connect(db_path)
    return AsyncSqliteSaver(conn)
