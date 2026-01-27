# Order Fulfillment Temporal Sample (Python)

This application implements an order fulfillment workflow with four activities executed in sequence:

1. `process_payment`
2. `reserve_inventory`
3. `pack_order_items` (optional, with heartbeat checkpointing)
4. `deliver_order`

It demonstrates the following scenarios:

- **Happy path** – approve the order and it is delivered.
- **API downtime** – start with `--inventory-down` to simulate a failing inventory service.
- **Invalid order troubleshooting** – use `--expiry 12/23` to trigger an invalid credit card.
- **Human in the loop** – send the `approve_order` signal to continue processing.
- **Approve or expire order** – workflow waits 30s for approval before expiring.
- **Bug in workflow** – uncomment the line in `order_fulfillment/workflow.py` that raises `RuntimeError`.
- **Heartbeat checkpointing** – demonstrates activity recovery from worker failure using checkpoint data.

## Project Structure

```
temporal-order-fulfill-python/
├── order_fulfillment/          # Main package
│   ├── __init__.py
│   ├── activities.py           # Temporal activities
│   ├── shared.py              # Shared data models (Order, PackingCheckpoint)
│   ├── workflow.py            # Temporal workflow definition
│   └── py.typed              # Type checking marker
├── scripts/                   # Executable scripts
│   ├── worker_workflow.py    # Workflow worker
│   ├── worker_activity.py    # Activity worker
│   ├── starter.py            # Workflow starter
│   ├── starter_checkpoint_demo.py  # Checkpoint demo starter
│   └── signal_approve.py     # Signal sender
├── tests/                    # Test suite
│   ├── __init__.py
│   └── test_shared.py
├── pyproject.toml           # Project configuration
├── noxfile.py              # Test automation
├── uv.lock                 # Dependency lock file
└── README.md
```

## Prerequisites

- [Temporal CLI](https://docs.temporal.io/cli)
- Python 3.11+ with [uv](https://docs.astral.sh/uv/)

## Development Setup

Install dependencies:

```bash
uv sync --all-groups
```

Run tests:

```bash
uv run nox -s tests
```

Run linting and type checking:

```bash
uv run nox -s lint
uv run nox -s typecheck
```

Format code:

```bash
uv run nox -s format
```

## Running the sample

Start the Temporal dev server if not already running:

```bash
temporal operator namespace describe default >/dev/null 2>&1 || temporal server start-dev &
```

### 1. Start the workers

Open two terminals:

**Terminal 1 - Workflow Worker:**
```bash
uv run scripts/worker_workflow.py
```

**Terminal 2 - Activity Worker:**
```bash
uv run scripts/worker_activity.py
```

### 2. Run a workflow

In a third terminal, start a workflow. The process prints the workflow ID and waits for completion.

```bash
uv run scripts/starter.py &
START_PID=$!
# note the workflow ID from output (e.g. order-order-1)
```

Send the approval signal in another process:

```bash
uv run scripts/signal_approve.py order-order-1
```

Wait for the starter to finish and show the result:

```bash
wait $START_PID
```

### Additional scenarios

- **Order expires:** start the workflow and do not send the signal. After ~30s it returns `Order expired`.
- **Inventory API down:**
  ```bash
  uv run scripts/starter.py --inventory-down
  ```
- **Invalid credit card:**
  ```bash
  uv run scripts/starter.py --expiry 12/23
  ```
- **With packing (heartbeat checkpoints):**
  ```bash
  uv run scripts/starter.py --pack
  ```
- **Bug in workflow:** uncomment `raise RuntimeError("workflow bug!")` in `order_fulfillment/workflow.py`, restart the workflow worker, then run `scripts/starter.py` again.

### 3. Clean up

Stop both workers with Ctrl+C in their respective terminals.

## Heartbeat Checkpoint Demo

This demo shows how long-running activities can save progress checkpoints via heartbeats and resume from where they left off after a worker failure.

### Quick Start

With both workers running (see above), start the checkpoint demo:

```bash
uv run scripts/starter_checkpoint_demo.py
```

### Demo Flow

1. Watch Terminal 2 (activity worker) for packing progress logs
2. After seeing a few "Packed SKU-XXX" messages, kill the activity worker (Ctrl+C)
3. Wait ~30 seconds for heartbeat timeout
4. Restart the activity worker: `uv run scripts/worker_activity.py`
5. Observe "Resuming from checkpoint" - activity continues from last checkpoint
6. Send approval signal when prompted: `uv run scripts/signal_approve.py <workflow-id>`

### Implementation Notes

The `pack_order_items` activity uses a dual heartbeat strategy:
- **Background heartbeat (every 5s)**: Keeps activity alive if individual items take longer than expected
- **Immediate heartbeat after each item**: Ensures latest checkpoint is always available for recovery

This handles real-world scenarios where item processing time varies unpredictably.

When running the demo:
- Activity resumes from `last_processed_idx + 1`, skipping already-packed items
- `attempt: 2` in logs indicates this is a retry
- Temporal UI shows `ActivityTaskTimedOut` with `HEARTBEAT` timeout type
