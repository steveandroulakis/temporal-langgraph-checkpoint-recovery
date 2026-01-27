import asyncio
import sys

from temporalio.client import Client


async def main(workflow_id: str) -> None:
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal("approve_order")
    print("Approval signal sent")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: uv run signal_approve.py <workflow_id>")
    asyncio.run(main(sys.argv[1]))
