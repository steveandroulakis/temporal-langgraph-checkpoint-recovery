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
uv run scripts/inspect_checkpoints.py                  # list all threads
uv run scripts/inspect_checkpoints.py <workflow_id>   # show checkpoint history
```

## Architecture Overview

This is a LangGraph research agent running inside a Temporal workflow with dual heartbeat checkpointing for resilience.

### Core Components

- **`langgraph_agent/graph.py`**: LangGraph StateGraph definition
  - Nodes: search → analyze → report
  - Uses litellm for LLM calls (OpenAI or Anthropic)
  - SQLite checkpointer for graph state persistence

- **`langgraph_agent/activities.py`**: Temporal activity with dual heartbeat pattern
  - Background heartbeat loop (5s interval)
  - Immediate heartbeat after each graph superstep
  - Checkpoint recovery from heartbeat_details

- **`langgraph_agent/workflow.py`**: `ResearchAgentWorkflow`
  - Executes activity with retry policy and heartbeat timeout

- **`langgraph_agent/shared.py`**: Data models
  - `AgentInput`: query
  - `AgentOutput`: final_report, thread_id, superstep_count
  - `AgentCheckpoint`: thread_id, checkpoint_id, superstep_count, current_node
  - Note: `thread_id` is derived from `workflow_id` in the activity, not passed via input

- **`scripts/`**: Executable scripts for running the application:
  - `worker_workflow.py`: Workflow worker
  - `worker_activity.py`: Activity worker (can be killed for checkpoint demo)
  - `starter.py`: Starts workflow with query
  - `starter_checkpoint_demo.py`: Interactive checkpoint recovery demo
  - `inspect_checkpoints.py`: Inspect LangGraph checkpoints in SQLite

### Agent Flow
1. **Search**: Gathers information about query (LLM call)
2. **Analyze**: Synthesizes findings into insights (LLM call)
3. **Report**: Generates final research report (LLM call)

### Testing Scenarios
- **Happy path**: `starter.py "topic"` - runs to completion
- **Checkpoint recovery**: `starter_checkpoint_demo.py` - kill worker mid-execution

### Configuration
- **Task Queue**: `research-agent-queue`
- **Temporal Server**: `localhost:7233` (default dev server)
- **LLM**: Auto-selects based on env (ANTHROPIC_API_KEY → Claude, else → GPT-4)
- **Heartbeat Timeout**: 30 seconds
- **Background Heartbeat Interval**: 5 seconds
- **Start-to-Close Timeout**: 10 minutes
- **Retry Policy**: 5 attempts, 2x backoff

### Temporal Sandbox Pattern

This project follows Temporal Python SDK sandbox best practices:

1. **Dataclasses imported directly** in workflow - `shared.py` contains only pure dataclasses (deterministic, side-effect-free)

2. **Activity imports via `imports_passed_through()`** - Heavy deps (langgraph, litellm) are passed through to avoid sandbox reloading:
   ```python
   with workflow.unsafe.imports_passed_through():
       from langgraph_agent.activities import run_langgraph_agent
   ```

3. **Worker-level passthrough config** - Third-party modules configured at worker creation:
   ```python
   restrictions = SandboxRestrictions.default.with_passthrough_modules(
       "langgraph", "litellm", "pydantic", ...
   )
   Worker(..., workflow_runner=SandboxedWorkflowRunner(restrictions=restrictions))
   ```

See [Temporal Python SDK Sandbox docs](https://docs.temporal.io/develop/python/python-sdk-sandbox) for details.
