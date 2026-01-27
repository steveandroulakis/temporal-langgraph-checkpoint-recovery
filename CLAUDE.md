# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup
```bash
# Install dependencies
uv sync --all-groups
```

### Testing and Quality Assurance
```bash
# Run tests
uv run nox -s tests

# Run tests on specific Python versions
uv run nox -s tests -p 3.11
uv run nox -s tests -p 3.12

# Run single test file
uv run pytest tests/test_shared.py -v

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

# Terminal 3: Start workflow (basic order)
uv run scripts/starter.py

# Start workflow with packing (heartbeat checkpoints)
uv run scripts/starter.py --pack

# Start workflow with inventory down simulation
uv run scripts/starter.py --inventory-down

# Start workflow with invalid credit card
uv run scripts/starter.py --expiry 12/23

# Send approval signal within 30 seconds (replace workflow-id with actual ID from starter output)
uv run scripts/signal_approve.py <workflow-id>
```

### Heartbeat Checkpoint Demo
```bash
# With both workers running, start checkpoint demo
uv run scripts/starter_checkpoint_demo.py

# Kill activity worker (Ctrl+C in Terminal 2), wait 30s, restart it
uv run scripts/worker_activity.py

# After packing completes, approve:
uv run scripts/signal_approve.py <workflow-id>
```

## Architecture Overview

This is a Temporal workflow application demonstrating order fulfillment with four sequential activities, human-in-the-loop approval, and heartbeat checkpointing for long-running activities.

### Core Components

- **`order_fulfillment/workflow.py`**: Contains `OrderWorkflow` class implementing the main business logic
  - Sequential execution: payment → inventory → packing (optional) → approval wait → delivery
  - Handles approval signal and timeout (30s expiry)
  - Configurable retry policies and timeouts

- **`order_fulfillment/activities.py`**: Four Temporal activities:
  - `process_payment`: Validates credit card expiry date
  - `reserve_inventory`: Reserves inventory with optional downtime simulation
  - `pack_order_items`: Long-running packing with heartbeat checkpoints; resumes from checkpoint on worker failure
  - `deliver_order`: Final delivery simulation

- **`order_fulfillment/shared.py`**: Data models
  - `Order`: Order details (order_id, item, quantity, credit_card_expiry, items_to_pack)
  - `PackingCheckpoint`: Checkpoint state (last_processed_idx, last_item_sku)

- **`scripts/`**: Executable scripts for running the application:
  - `worker_workflow.py`: Workflow worker
  - `worker_activity.py`: Activity worker (can be killed independently for checkpoint demo)
  - `starter.py`: Starts workflow execution with configurable scenarios
  - `starter_checkpoint_demo.py`: Starts checkpoint demo workflow
  - `signal_approve.py`: Sends approval signal to waiting workflow

### Workflow Pattern
1. **Payment Processing**: Validates credit card, fails on expired cards
2. **Inventory Reservation**: Can be configured to simulate progressive API downtime
3. **Packing** (optional): Long-running activity with heartbeat checkpointing; resumes from last checkpoint on retry
4. **Approval Wait**: Workflow pauses for human approval signal (30s timeout)
5. **Order Delivery**: Final fulfillment step

### Testing Scenarios
- **Happy path**: Normal order flow with approval within 30 seconds
- **Progressive API downtime**: Use `--inventory-down` flag
  - First 4 attempts fail with 10-second delays each
  - 5th attempt succeeds, demonstrating Temporal's retry resilience
- **Invalid credit card**: Use `--expiry 12/23` or past dates
- **Order expiration**: Don't send approval signal within 30 seconds
- **Workflow bug**: Uncomment `RuntimeError` in workflow.py to simulate workflow failures
- **Heartbeat checkpointing**: Use `starter_checkpoint_demo.py`
  - Kill activity worker mid-pack, wait 30s for heartbeat timeout, restart
  - Activity resumes from last checkpoint, skipping already-packed items

### Configuration
- **Task Queue**: `order-task-queue`
- **Temporal Server**: `localhost:7233` (default dev server)
- **Python Version**: 3.11+ required
- **Type Checking**: Strict mypy configuration enabled
- **Code Quality**: Ruff for linting and formatting
- **Heartbeat Timeout**: 30 seconds (pack_order_items activity)
- **Background Heartbeat Interval**: 5 seconds (keeps activity alive during long item processing)
- **Checkpoint Update**: Immediate after each item completes
