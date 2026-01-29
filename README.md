# LangGraph Agent with Temporal Checkpointing

A research agent built with LangGraph running inside Temporal activities with heartbeat checkpointing for resilience and human-in-the-loop approval.

## Features

- **LangGraph Research Agent**: Multi-step agent with search, analysis, and report generation
- **Dual Heartbeat Pattern**: Background heartbeats + immediate superstep checkpoints
- **Human-in-the-Loop**: Optional approval interrupt with Temporal signals
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

## Human Approval Flow

```bash
# Start workflow requiring approval
uv run scripts/starter.py --needs-approval "Write a report on AI safety"

# Workflow pauses after analysis. Send approval:
uv run scripts/signal_approve.py <workflow-id>

# Or reject with feedback:
uv run scripts/signal_approve.py <workflow-id> --reject --feedback "Need more sources"
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
uv run scripts/inspect_checkpoints.py              # list all threads
uv run scripts/inspect_checkpoints.py <thread_id>  # show checkpoint history
```

**Finding thread_id:** The demo script prints it, or get it from Temporal heartbeat details via UI/CLI/API (e.g., `temporal workflow describe -w <workflow-id>`).

## Architecture

```
Query → [Search] → [Analyze] → [Approval?] → [Report] → Output
           ↓           ↓           ↓            ↓
        Heartbeat  Heartbeat  Interrupt    Heartbeat
```

- **Temporal Workflow**: Orchestrates activity execution, handles approval signals
- **Temporal Activity**: Runs LangGraph with dual heartbeat pattern
- **LangGraph**: StateGraph with SQLite checkpointer for graph state
- **litellm**: Unified LLM interface (OpenAI/Anthropic)

## Project Structure

```
langgraph-agent/
├── langgraph_agent/          # Main package
│   ├── __init__.py
│   ├── activities.py         # Temporal activity with dual heartbeat
│   ├── graph.py             # LangGraph StateGraph definition
│   ├── shared.py            # Data models
│   └── workflow.py          # Temporal workflow with signal handling
├── scripts/                  # Executable scripts
│   ├── worker_workflow.py
│   ├── worker_activity.py
│   ├── starter.py
│   ├── starter_checkpoint_demo.py
│   ├── signal_approve.py
│   └── inspect_checkpoints.py
├── tests/
│   └── test_agent.py
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
| Approval Timeout | 30 minutes |
| Activity Timeout | 10 minutes |
| Max Retries | 5 |

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
