import asyncio
import logging
import time

from rich.console import Console
from rich.panel import Panel
from temporalio.client import Client

from langgraph_agent.shared import AgentInput
from langgraph_agent.workflow import ResearchAgentWorkflow


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    console = Console()

    # Query that requires multiple LLM calls
    query = (
        "Tell me where to find marsupials in Australia, and " +
        "detail the endangered species among them."
    )

    client = await Client.connect("localhost:7233")
    workflow_id = f"checkpoint-demo-{int(time.time())}"
    agent_input = AgentInput(query=query)
    handle = await client.start_workflow(
        ResearchAgentWorkflow.run,
        agent_input,
        id=workflow_id,
        task_queue="research-agent-queue",
    )

    console.print(f"\n[bold green]Started workflow:[/bold green] {workflow_id}")
    console.print("[dim](workflow_id is also the LangGraph thread_id)[/dim]")
    console.print(f"[dim]Query: {query}[/dim]")
    console.print(
        Panel.fit(
            f"""[bold cyan]CHECKPOINT DEMO INSTRUCTIONS[/bold cyan]

1. Watch Terminal 2 (activity worker) for superstep progress

2. After seeing "Superstep 1" or "Superstep 2", kill activity worker (Ctrl+C)

3. Wait ~15 seconds (heartbeat timeout triggers retry)

4. Restart activity worker:
   [green]uv run scripts/worker_activity.py[/green]

5. Observe: "Resuming from checkpoint" in logs
   - Agent resumes from last saved superstep
   - LangGraph SQLite checkpoint restores graph state

6. Workflow completes with research report

[bold]VALIDATE CHECKPOINTS:[/bold]
   [green]uv run scripts/inspect_langgraph_checkpoints.py[/green]
   [green]uv run scripts/inspect_langgraph_checkpoints.py {workflow_id} -d[/green]
""",
            title="Demo Steps",
            border_style="yellow",
        )
    )

    result = await handle.result()
    console.print(Panel(result, title="Research Report", border_style="green"))


if __name__ == "__main__":
    asyncio.run(main())
