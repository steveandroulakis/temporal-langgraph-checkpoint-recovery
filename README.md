# LangGraph Agent with Temporal Checkpointing

A research agent built with LangGraph running inside Temporal activities with heartbeat checkpointing for crash recovery. Use this sample as a template for [automatic crash recovery of any agent](docs/adapter-pattern.md), or [plug in your own LangGraph](docs/bring-your-own-graph.md) with minimal code changes.

## Features

- **LangGraph Research Agent**: Multi-step agent with search, analysis, and report generation
- **Dual Heartbeat Pattern**: Background heartbeats + immediate superstep checkpoints
- **Crash Recovery**: Activity resumes from last checkpoint on worker failure
- **LLM Flexibility**: Uses litellm with OpenAI or Anthropic

## Quick Start

```bash
# Install dependencies
uv sync --all-groups

# Set API key
export OPENAI_API_KEY=sk-...  # or ANTHROPIC_API_KEY

# Start Temporal (if not running)
temporal server start-dev &

# Terminal 1: Workflow worker
uv run scripts/worker_workflow.py

# Terminal 2: Activity worker
uv run scripts/worker_activity.py

# Terminal 3: Run agent
uv run scripts/starter.py "What is quantum computing?"
```

## Checkpoint Recovery Demo

```bash
# Start demo workflow (shows thread_id in output)
uv run scripts/starter_checkpoint_demo.py

# After seeing superstep progress, kill activity worker (Ctrl+C)
# Wait ~15 seconds for heartbeat timeout

# Restart activity worker - resumes from checkpoint
uv run scripts/worker_activity.py

# Verify checkpoints were saved
uv run scripts/inspect_langgraph_checkpoints.py                 # list threads
uv run scripts/inspect_langgraph_checkpoints.py <thread_id> -d  # detailed history
```

**Finding thread_id:** The demo script prints it, or get it from Temporal heartbeat details via UI/CLI/API (e.g., `temporal workflow describe -w <workflow-id>`).

## Sleeping Agent Demo (Non-Checkpointing)

Demonstrates behavior when an agent doesn't support checkpointing:

```bash
# Start sleeping agent (30s × 4 steps = 2 min total)
uv run scripts/starter_sleeping.py

# After 1-2 steps, kill activity worker (Ctrl+C)
# Wait ~15 seconds for heartbeat timeout

# Restart activity worker - agent restarts from beginning (no checkpoint)
uv run scripts/worker_activity.py
```

See [Adapter Pattern](docs/adapter-pattern.md) for details on creating custom adapters.

## Bring Your Own LangGraph

Have an existing LangGraph you want to make crash-resilient? See [Bring Your Own Graph](docs/bring-your-own-graph.md) for a step-by-step guide.

**TL;DR:** Modify 3 files (`graph.py`, `shared.py`, `adapters/langgraph.py`) to plug in your graph. The Temporal infrastructure (`runner.py`, `workflow.py`) stays unchanged.

## Architecture

```
Query → [Search] → [Analyze] → [Report] → Output
           ↓           ↓           ↓
        Heartbeat  Heartbeat  Heartbeat
```

- **Temporal Workflow**: Orchestrates activity execution
- **Temporal Activity**: Runs LangGraph with dual heartbeat pattern
- **LangGraph**: StateGraph with SQLite checkpointer for graph state
- **litellm**: Unified LLM interface (OpenAI/Anthropic)

## Project Structure

```
langgraph-agent/
├── langgraph_agent/          # Main package
│   ├── __init__.py
│   ├── activities.py         # Thin activity wrappers using adapters
│   ├── runner.py             # Generic Temporal runner for adapters
│   ├── graph.py              # LangGraph StateGraph definition
│   ├── shared.py             # Data models
│   ├── workflow.py           # Temporal workflows
│   └── adapters/             # Agent adapters
│       ├── __init__.py
│       ├── base.py           # AgentAdapter ABC
│       ├── langgraph.py      # LangGraph adapter (checkpointing)
│       └── sleeping.py       # Sleeping adapter (no checkpointing)
├── scripts/                  # Executable scripts
│   ├── worker_workflow.py
│   ├── worker_activity.py
│   ├── starter.py
│   ├── starter_checkpoint_demo.py
│   ├── starter_sleeping.py              # Sleeping agent demo
│   └── inspect_langgraph_checkpoints.py # Inspect LangGraph checkpoints
├── tests/
│   ├── test_agent.py
│   └── test_adapters.py
├── docs/
│   ├── adapter-pattern.md    # Adapter pattern documentation
│   └── bring-your-own-graph.md  # Guide for integrating your LangGraph
├── pyproject.toml
├── noxfile.py
└── README.md
```

## Configuration

| Setting | Value |
|---------|-------|
| Task Queue | `research-agent-queue` |
| Heartbeat Timeout | 30 seconds |
| Heartbeat Interval | 5 seconds |
| Activity Timeout | 10 minutes |
| Max Retries | 5 |

> **Note:** This demo uses SQLite for LangGraph checkpointing, which requires all activity workers to share the same filesystem. For production, use a shared database like PostgreSQL via LangGraph's [PostgresSaver](https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.postgres.PostgresSaver).

## Development

```bash
# Run tests
uv run nox -s tests

# Lint
uv run nox -s lint

# Type check
uv run nox -s typecheck

# Format
uv run nox -s format
```
