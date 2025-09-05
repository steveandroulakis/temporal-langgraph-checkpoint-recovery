# Order Fulfillment Temporal Sample (Python)

This application implements a simple order fulfillment workflow with three activities executed in sequence:

1. `process_payment`
2. `reserve_inventory` 
3. `deliver_order`

It is adapted from a TypeScript example and demonstrates the following scenarios:

- **Happy path** – approve the order and it is delivered.
- **API downtime** – start with `--inventory-down` to simulate a failing inventory service.
- **Invalid order troubleshooting** – use `--expiry 12/23` to trigger an invalid credit card.
- **Human in the loop** – send the `approve_order` signal to continue processing.
- **Approve or expire order** – workflow waits 10s for approval before expiring.
- **Bug in workflow** – uncomment the line in `order_fulfillment/workflow.py` that raises `RuntimeError`.

## Project Structure

```
temporal-order-fulfill-python/
├── order_fulfillment/          # Main package
│   ├── __init__.py
│   ├── activities.py           # Temporal activities
│   ├── shared.py              # Shared data models
│   ├── workflow.py            # Temporal workflow definition
│   └── py.typed              # Type checking marker
├── scripts/                   # Executable scripts
│   ├── worker.py             # Temporal worker
│   ├── starter.py            # Workflow starter
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

### 1. Start the worker

```bash
uv run scripts/worker.py &
echo $! > worker.pid
sleep 3
ps -p $(cat worker.pid) >/dev/null || { echo "Worker failed"; exit 1; }
```

### 2. Run a workflow

Start a workflow. The process prints the workflow ID and waits for completion.

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

- **Order expires:** start the workflow and do not send the signal. After ~10s it returns `Order expired`.
- **Inventory API down:**
  ```bash
  uv run scripts/starter.py --inventory-down
  ```
- **Invalid credit card:**
  ```bash
  uv run scripts/starter.py --expiry 12/23
  ```
- **Bug in workflow:** uncomment `raise RuntimeError("workflow bug!")` in `order_fulfillment/workflow.py`, restart the worker, then run `scripts/starter.py` again.

### 3. Clean up

```bash
kill $(cat worker.pid)
wait $(cat worker.pid) 2>/dev/null || true
rm -f worker.pid
```
