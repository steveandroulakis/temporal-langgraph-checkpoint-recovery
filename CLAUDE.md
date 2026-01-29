# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup
```bash
# Install dependencies
uv sync --all-groups

# Set LLM API key (choose one)
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
```

### Testing and Quality Assurance
```bash
# Run tests
uv run nox -s tests

# Run tests on specific Python versions
uv run nox -s tests -p 3.11
uv run nox -s tests -p 3.12

# Run single test file
uv run pytest tests/test_agent.py -v

# Run linting
uv run nox -s lint

# Run type checking
uv run nox -s typecheck

# Format code
uv run nox -s format

# Check formatting without changes
uv run nox -s format_check

# Run all pre-commit checks
uv run nox -s pre_commit
```

### Running the Application
```bash
# Start Temporal dev server (if not running)
temporal operator namespace describe default >/dev/null 2>&1 || temporal server start-dev &

# Terminal 1: Workflow worker
uv run scripts/worker_workflow.py

# Terminal 2: Activity worker
uv run scripts/worker_activity.py

# Terminal 3: Start workflow
uv run scripts/starter.py "What is quantum computing?"
```

### Heartbeat Checkpoint Demo
```bash
# With both workers running, start checkpoint demo
uv run scripts/starter_checkpoint_demo.py

# After seeing superstep progress, kill activity worker (Ctrl+C in Terminal 2)
# Wait ~15 seconds for heartbeat timeout
# Restart activity worker
uv run scripts/worker_activity.py

# Activity resumes from checkpoint, completes

# Inspect LangGraph checkpoints in SQLite (thread_id = workflow_id)
uv run scripts/inspect_langgraph_checkpoints.py                  # list threads
uv run scripts/inspect_langgraph_checkpoints.py <workflow_id> -d # detailed history
```

## Architecture Overview

This is a LangGraph research agent running inside a Temporal workflow with dual heartbeat checkpointing for resilience.

### Adapter Pattern

The codebase uses an adapter pattern to separate Temporal concerns from agent logic:

- **`langgraph_agent/adapters/base.py`**: `AgentAdapter` ABC
  - `supports_checkpointing`: bool property
  - `setup(thread_id, checkpoint)`: Initialize adapter
  - `run(input)`: AsyncIterator yielding `StepResult`
  - `get_final_output()`: Return final result

- **`langgraph_agent/runner.py`**: Generic Temporal runner
  - Handles heartbeating, checkpoint restoration, cleanup
  - Works with any `AgentAdapter` implementation

- **`langgraph_agent/adapters/langgraph.py`**: `LangGraphAdapter`
  - Checkpointing adapter for LangGraph research agent

- **`langgraph_agent/adapters/sleeping.py`**: `SleepingAdapter`
  - Non-checkpointing demo adapter

See [docs/adapter-pattern.md](docs/adapter-pattern.md) for creating custom adapters.

### Core Components

- **`langgraph_agent/graph.py`**: LangGraph StateGraph definition
  - Nodes: search → analyze → report
  - Uses litellm for LLM calls (OpenAI or Anthropic)
  - SQLite checkpointer for graph state persistence

- **`langgraph_agent/activities.py`**: Thin activity wrappers
  - `run_langgraph_agent()`: Uses LangGraphAdapter
  - `run_sleeping_agent()`: Uses SleepingAdapter

- **`langgraph_agent/workflow.py`**: Temporal workflows
  - `ResearchAgentWorkflow`: LangGraph research agent
  - `SleepingAgentWorkflow`: Non-checkpointing demo

- **`langgraph_agent/shared.py`**: Data models
  - `AgentInput`, `AgentOutput`: LangGraph agent I/O
  - `SleepingInput`, `SleepingOutput`: Sleeping agent I/O
  - `AgentCheckpoint`: Checkpoint state
  - `StepResult`: Yielded by adapters for progress
  - Note: `thread_id` is derived from `workflow_id` in the runner

- **`scripts/`**: Executable scripts:
  - `worker_workflow.py`: Workflow worker
  - `worker_activity.py`: Activity worker (can be killed for checkpoint demo)
  - `starter.py`: Starts LangGraph workflow
  - `starter_checkpoint_demo.py`: LangGraph checkpoint recovery demo
  - `starter_sleeping.py`: Sleeping agent demo (no checkpointing)
  - `inspect_langgraph_checkpoints.py`: Inspect LangGraph checkpoints in SQLite

### Agent Flow
1. **Search**: Gathers information about query (LLM call)
2. **Analyze**: Synthesizes findings into insights (LLM call)
3. **Report**: Generates final research report (LLM call)

### Testing Scenarios
- **Happy path**: `starter.py "topic"` - LangGraph agent runs to completion
- **Checkpoint recovery**: `starter_checkpoint_demo.py` - kill worker mid-execution, resumes from checkpoint
- **No checkpoint**: `starter_sleeping.py` - kill worker mid-execution, restarts from beginning

### Configuration
- **Task Queue**: `research-agent-queue`
- **Temporal Server**: `localhost:7233` (default dev server)
- **LLM**: Auto-selects based on env (ANTHROPIC_API_KEY → Claude, else → GPT-4)
- **Heartbeat Timeout**: 30 seconds
- **Background Heartbeat Interval**: 5 seconds
- **Start-to-Close Timeout**: 10 minutes
- **Retry Policy**: 5 attempts, 2x backoff

### SQLite Checkpointer Limitation

This demo uses SQLite for LangGraph checkpointing, requiring all activity workers to share the same filesystem. For production with distributed workers, use a shared database like PostgreSQL via LangGraph's `PostgresSaver`.

### Temporal Sandbox Pattern

This project follows Temporal Python SDK sandbox best practices:

1. **Dataclasses imported directly** in workflow - `shared.py` contains only pure dataclasses (deterministic, side-effect-free)

2. **Activity imports via `imports_passed_through()`** - Heavy deps (langgraph, litellm) are passed through to avoid sandbox reloading:
   ```python
   with workflow.unsafe.imports_passed_through():
       from langgraph_agent.activities import run_langgraph_agent, run_sleeping_agent
   ```

3. **Worker-level passthrough config** - Third-party modules configured at worker creation:
   ```python
   restrictions = SandboxRestrictions.default.with_passthrough_modules(
       "langgraph", "litellm", "pydantic", ...
   )
   Worker(..., workflow_runner=SandboxedWorkflowRunner(restrictions=restrictions))
   ```

See [Temporal Python SDK Sandbox docs](https://docs.temporal.io/develop/python/python-sdk-sandbox) for details.
