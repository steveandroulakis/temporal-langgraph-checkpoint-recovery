# Bring Your Own LangGraph

This guide shows how to integrate your existing LangGraph with Temporal for automatic crash recovery and checkpoint restoration.

## Why Temporal + LangGraph?

LangGraph has built-in checkpointing, but it doesn't handle:
- **Crash detection**: No automatic retry when a worker dies mid-execution
- **Timeout handling**: No built-in activity timeouts
- **Resume orchestration**: Manual intervention needed to restart from checkpoint

Temporal adds:
- **Heartbeat monitoring**: Detects worker death within ~30 seconds
- **Automatic retry**: Re-dispatches activity to healthy worker
- **Checkpoint passing**: Heartbeat details carry checkpoint state to new worker
- **LangGraph resumes**: New worker continues from last checkpointed superstep

## Integration Overview

```
Your LangGraph → LangGraphAdapter → Temporal Activity → Temporal Workflow
     ↓                  ↓                   ↓
  Checkpoints      StepResults         Heartbeats
  (SQLite)       (yield progress)    (carry checkpoint)
```

The key insight: LangGraph's checkpointing saves graph state after each node. Temporal's heartbeating carries the checkpoint location to new workers on retry. Together, they enable seamless crash recovery.

## What You Need to Modify

To bring your own graph, you modify **3 files**:

| File | What to Change |
|------|----------------|
| `langgraph_agent/graph.py` | Your graph definition (nodes, edges, state) |
| `langgraph_agent/shared.py` | Input/output dataclasses |
| `langgraph_agent/adapters/langgraph.py` | State initialization and output extraction |

The following remain **unchanged**:
- `runner.py` - Generic Temporal runner
- `activities.py` - Thin wrapper (unless renaming)
- `workflow.py` - Orchestration layer

## Step-by-Step Guide

### Step 1: Define Your Graph State

Replace `AgentState` in [graph.py](../langgraph_agent/graph.py) with your state schema:

```python
# Before (research agent)
class AgentState(TypedDict):
    query: str
    messages: Annotated[list[Any], add_messages]
    search_results: str
    analysis: str
    final_report: str

# After (your graph)
class AgentState(TypedDict):
    user_input: str
    documents: list[str]
    summary: str
    # ... your fields
```

### Step 2: Define Your Nodes

Replace the node functions with your logic:

```python
# Your nodes - same signature pattern
async def my_node(state: AgentState) -> dict[str, Any]:
    """Each node receives state, returns partial state update."""
    result = await do_something(state["user_input"])
    return {"documents": result}  # Partial state update
```

### Step 3: Build Your Graph

Update `build_graph()`:

```python
def build_graph() -> StateGraph[AgentState]:
    builder = StateGraph(AgentState)

    # Add your nodes
    builder.add_node("fetch", fetch_node)
    builder.add_node("process", process_node)
    builder.add_node("summarize", summarize_node)

    # Define flow
    builder.set_entry_point("fetch")
    builder.add_edge("fetch", "process")
    builder.add_edge("process", "summarize")
    builder.add_edge("summarize", END)

    # Conditional edges work too
    # builder.add_conditional_edges("router", routing_function, {...})

    return builder
```

### Step 4: Update Input/Output Types

In [shared.py](../langgraph_agent/shared.py):

```python
@dataclass
class AgentInput:
    """Input to your workflow."""
    user_input: str
    # ... other input fields

@dataclass
class AgentOutput:
    """Output from your activity."""
    summary: str  # Must match what you extract in adapter
    thread_id: str
    superstep_count: int
```

### Step 5: Update the Adapter

In [langgraph.py](../langgraph_agent/adapters/langgraph.py), update two methods:

**Initialize state in `run()`:**

```python
async def run(self, input: AgentInput) -> AsyncIterator[StepResult]:
    if self._resuming:
        stream_input = None
    else:
        # Initialize YOUR state schema
        stream_input = {
            "user_input": input.user_input,
            "documents": [],
            "summary": "",
            # ... all fields with initial values
        }
    # Rest stays the same
```

**Extract output in `get_final_output()`:**

```python
async def get_final_output(self) -> AgentOutput:
    final_state = await self._graph.aget_state(self._config)

    # Extract YOUR output field
    summary = ""
    if final_state.values:
        summary = final_state.values.get("summary", "")

    return AgentOutput(
        summary=summary,
        thread_id=self._thread_id,
        superstep_count=self._superstep_count,
    )
```

## Complete Example: RAG Pipeline

Here's a minimal RAG pipeline example:

### graph.py

```python
from typing import Any
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

class RAGState(TypedDict):
    question: str
    documents: list[str]
    answer: str

async def retrieve_node(state: RAGState) -> dict[str, Any]:
    docs = await vector_search(state["question"])
    return {"documents": docs}

async def generate_node(state: RAGState) -> dict[str, Any]:
    answer = await llm_generate(state["question"], state["documents"])
    return {"answer": answer}

def build_graph() -> StateGraph[RAGState]:
    builder = StateGraph(RAGState)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)
    builder.set_entry_point("retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", END)
    return builder
```

### shared.py additions

```python
@dataclass
class RAGInput:
    question: str

@dataclass
class RAGOutput:
    answer: str
    thread_id: str
    superstep_count: int
```

### Adapter run() update

```python
stream_input = {
    "question": input.question,
    "documents": [],
    "answer": "",
}
```

## Conditional Edges and Complex Flows

LangGraph conditional edges work seamlessly:

```python
def should_retry(state: AgentState) -> str:
    if state["confidence"] < 0.8:
        return "retry"
    return "finish"

builder.add_conditional_edges(
    "evaluate",
    should_retry,
    {"retry": "search", "finish": END}
)
```

Each path through the graph creates checkpoints. If the worker crashes mid-retry-loop, it resumes from the last completed node.

## Human-in-the-Loop Patterns

For graphs requiring human input, consider using Temporal signals:

```python
# In workflow.py
@workflow.signal
async def provide_feedback(self, feedback: str) -> None:
    self._feedback = feedback

# Activity waits for feedback via workflow signal
# LangGraph checkpoints preserve state while waiting
```

## Production Considerations

### Database Backend

This sample uses SQLite (single-machine). For distributed workers:

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def get_checkpointer():
    return AsyncPostgresSaver.from_conn_string(
        "postgresql://user:pass@host/db"
    )
```

### Checkpoint Cleanup

LangGraph checkpoints accumulate. Implement cleanup:

```python
# After workflow completes successfully
await checkpointer.adelete_thread(thread_id)
```

### Error Handling

Temporal retries handle transient failures. For permanent failures:

```python
async def my_node(state: AgentState) -> dict[str, Any]:
    try:
        result = await risky_operation()
        return {"result": result}
    except PermanentError as e:
        # Store error in state, let graph handle gracefully
        return {"error": str(e)}
```

## Testing Your Integration

```bash
# 1. Start workers
uv run scripts/worker_workflow.py &
uv run scripts/worker_activity.py &

# 2. Run your workflow
uv run scripts/starter.py "your input"

# 3. Test crash recovery: kill activity worker during execution
# Wait for heartbeat timeout (~15s)
# Restart worker - should resume from checkpoint
```

## FAQ

**Q: Do I need to modify the Temporal workflow?**

No. The workflow just calls the activity. Unless you need signals/queries for human-in-the-loop, the workflow stays unchanged.

**Q: What if my graph has many nodes?**

Works fine. Each node completion triggers a checkpoint + heartbeat. More nodes = more granular recovery points.

**Q: Can I use LangGraph's interrupt feature?**

Yes, but you'd need to add signal handling in the workflow for the human to provide input. The checkpoint preserves state while waiting.

**Q: What about sub-graphs?**

Sub-graphs checkpoint normally. The adapter treats the compiled graph as a black box—it just streams supersteps.

**Q: My graph uses invoke() not stream(). Does this work?**

The adapter uses `astream()` for progress tracking. If you only need final output, you could modify the adapter, but you'd lose per-step heartbeating (less granular recovery).
