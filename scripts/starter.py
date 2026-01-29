import argparse
import asyncio
import logging
import time

from rich.console import Console
from rich.panel import Panel
from temporalio.client import Client

from langgraph_agent.shared import AgentInput
from langgraph_agent.workflow import ResearchAgentWorkflow


async def main() -> None:
    parser = argparse.ArgumentParser(description="Start a research agent workflow")
    parser.add_argument(
        "query", nargs="?", default="What is quantum computing?", help="Research query"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    console = Console()

    agent_input = AgentInput(query=args.query)

    try:
        client = await Client.connect("localhost:7233")
        workflow_id = f"research-{int(time.time())}"
        handle = await client.start_workflow(
            ResearchAgentWorkflow.run,
            agent_input,
            id=workflow_id,
            task_queue="research-agent-queue",
        )
        console.print(f"\n[bold green]Started workflow:[/bold green] {workflow_id}")
        console.print(f"[dim]Query: {args.query}[/dim]")

        result = await handle.result()
        console.print(Panel(result, title="Research Report", border_style="green"))
    except Exception as err:
        logging.error("Workflow execution failed: %s", err)
        raise SystemExit(1) from err


if __name__ == "__main__":
    asyncio.run(main())
