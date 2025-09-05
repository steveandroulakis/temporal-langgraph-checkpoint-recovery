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

# Start worker (run in background)
uv run scripts/worker.py &
echo $! > worker.pid

# Start workflow (basic order)
uv run scripts/starter.py

# Start workflow with inventory down simulation
uv run scripts/starter.py --inventory-down

# Start workflow with invalid credit card
uv run scripts/starter.py --expiry 12/23

# Send approval signal within 30 seconds (replace workflow-id with actual ID from starter output)
uv run scripts/signal_approve.py <workflow-id>

# Clean up worker
kill $(cat worker.pid)
rm -f worker.pid
```

## Architecture Overview

This is a Temporal workflow application demonstrating order fulfillment with three sequential activities and human-in-the-loop approval.

### Core Components

- **`order_fulfillment/workflow.py`**: Contains `OrderWorkflow` class implementing the main business logic
  - Sequential execution: payment → inventory → approval wait → delivery
  - Handles approval signal and timeout (30s expiry)
  - Configurable retry policies and timeouts

- **`order_fulfillment/activities.py`**: Three Temporal activities:
  - `process_payment`: Validates credit card expiry date
  - `reserve_inventory`: Reserves inventory with optional downtime simulation
  - `deliver_order`: Final delivery simulation

- **`order_fulfillment/shared.py`**: Contains `Order` dataclass with order details

- **`scripts/`**: Executable scripts for running the application:
  - `worker.py`: Starts Temporal worker with workflows and activities
  - `starter.py`: Starts workflow execution with configurable scenarios
  - `signal_approve.py`: Sends approval signal to waiting workflow

### Workflow Pattern
1. **Payment Processing**: Validates credit card, fails on expired cards
2. **Inventory Reservation**: Can be configured to simulate progressive API downtime
3. **Approval Wait**: Workflow pauses for human approval signal (30s timeout)
4. **Order Delivery**: Final fulfillment step

### Testing Scenarios
- **Happy path**: Normal order flow with approval within 30 seconds
- **Progressive API downtime**: Use `--inventory-down` flag
  - First 4 attempts fail with 10-second delays each
  - 5th attempt succeeds, demonstrating Temporal's retry resilience
- **Invalid credit card**: Use `--expiry 12/23` or past dates
- **Order expiration**: Don't send approval signal within 30 seconds
- **Workflow bug**: Uncomment `RuntimeError` in workflow.py to simulate workflow failures

### Configuration
- **Task Queue**: `order-task-queue`
- **Temporal Server**: `localhost:7233` (default dev server)
- **Python Version**: 3.11+ required
- **Type Checking**: Strict mypy configuration enabled
- **Code Quality**: Ruff for linting and formatting