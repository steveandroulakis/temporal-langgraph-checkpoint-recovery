# Adapter Pattern for Temporal Agent Activities

This document describes the adapter pattern used to separate Temporal concerns (heartbeating, checkpoint restoration) from agent-specific logic.

## Overview

The adapter pattern provides:
1. **Reusable Temporal runner** - handles heartbeating, checkpoint restoration, logging
2. **Pluggable agent logic** - implement `AgentAdapter` for any agent type
3. **Clear separation** - agent code doesn't know about Temporal internals

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Temporal Activity                    │
│  ┌───────────────────────────────────────────────┐  │
│  │               run_adapter()                    │  │
│  │  - Restore checkpoint from heartbeat_details  │  │
│  │  - Background heartbeat loop                  │  │
│  │  - Heartbeat after each step                  │  │
│  │  - Cleanup in finally block                   │  │
│  └───────────────────────────────────────────────┘  │
│                        │                            │
│                        ▼                            │
│  ┌───────────────────────────────────────────────┐  │
│  │            AgentAdapter (ABC)                  │  │
│  │  - supports_checkpointing: bool               │  │
│  │  - setup(thread_id, checkpoint)               │  │
│  │  - run(input) → AsyncIterator[StepResult]     │  │
│  │  - get_final_output() → OutputT               │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Core Components

### AgentAdapter (base.py)

Abstract base class for agent adapters:

```python
class AgentAdapter(ABC, Generic[InputT, OutputT]):
    @property
    @abstractmethod
    def supports_checkpointing(self) -> bool: ...

    @abstractmethod
    async def setup(self, thread_id: str, checkpoint: AgentCheckpoint | None) -> None: ...

    @abstractmethod
    def run(self, input: InputT) -> AsyncIterator[StepResult]: ...

    @abstractmethod
    async def get_final_output(self) -> OutputT: ...
```

### run_adapter() (runner.py)

Generic runner that handles Temporal concerns:

```python
async def run_adapter(
    adapter: AgentAdapter[InputT, OutputT],
    input: InputT,
    heartbeat_interval: float = 5.0,
) -> OutputT:
    # 1. Restore checkpoint from heartbeat_details
    # 2. Log based on supports_checkpointing
    # 3. Call adapter.setup()
    # 4. Start background heartbeat loop
    # 5. Iterate adapter.run(), heartbeat after each step
    # 6. Return adapter.get_final_output()
```

### StepResult (shared.py)

Yielded by adapters to signal progress:

```python
@dataclass
class StepResult:
    step_number: int
    step_name: str
    checkpoint_id: str | None = None  # For checkpointing adapters
```

## Included Adapters

### LangGraphAdapter

Runs LangGraph with SQLite checkpointing:
- `supports_checkpointing = True`
- Resumes from LangGraph checkpoint on retry
- Yields `StepResult` with `checkpoint_id` after each superstep

### SleepingAdapter

Demo adapter without checkpointing:
- `supports_checkpointing = False`
- Always restarts from beginning on retry
- Sleeps in configurable steps (default: 30s × 4 steps)

## Creating Custom Adapters

1. Subclass `AgentAdapter[YourInput, YourOutput]`
2. Implement required methods
3. Create thin activity wrapper

Example:

```python
from langgraph_agent.adapters.base import AgentAdapter
from langgraph_agent.shared import AgentCheckpoint, StepResult

@dataclass
class MyInput:
    data: str

@dataclass
class MyOutput:
    result: str

class MyAdapter(AgentAdapter[MyInput, MyOutput]):
    @property
    def supports_checkpointing(self) -> bool:
        return False  # or True if you implement checkpointing

    async def setup(self, thread_id: str, checkpoint: AgentCheckpoint | None) -> None:
        # Initialize your agent
        pass

    async def run(self, input: MyInput) -> AsyncIterator[StepResult]:
        # Execute your agent, yield progress
        for i, step in enumerate(my_steps):
            result = await execute_step(step, input)
            yield StepResult(
                step_number=i + 1,
                step_name=step.name,
                checkpoint_id=None,  # or actual checkpoint ID
            )

    async def get_final_output(self) -> MyOutput:
        return MyOutput(result=self.accumulated_result)

# Thin activity wrapper
@activity.defn
async def run_my_agent(input: MyInput) -> MyOutput:
    return await run_adapter(MyAdapter(), input)
```

## Checkpointing vs Non-Checkpointing

| Aspect | Checkpointing | Non-Checkpointing |
|--------|---------------|-------------------|
| On retry | Resumes from checkpoint | Restarts from beginning |
| Example | LangGraphAdapter | SleepingAdapter |
| Checkpoint restoration | Uses `checkpoint` param | Ignores `checkpoint` param |
| `checkpoint_id` in StepResult | Set to actual ID | Set to `None` |

## Testing

Run adapter tests:

```bash
uv run pytest tests/test_adapters.py -v
```
