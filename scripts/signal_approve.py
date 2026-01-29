import argparse
import asyncio

from temporalio.client import Client


async def main(workflow_id: str, approved: bool, feedback: str) -> None:
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal("approve_research", args=[approved, feedback])
    status = "approved" if approved else "rejected"
    print(f"Approval signal sent: {status}")
    if feedback:
        print(f"Feedback: {feedback}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send approval signal to research workflow"
    )
    parser.add_argument("workflow_id", help="Workflow ID to signal")
    parser.add_argument(
        "--reject", action="store_true", help="Reject instead of approve"
    )
    parser.add_argument("--feedback", default="", help="Optional feedback message")
    args = parser.parse_args()

    asyncio.run(main(args.workflow_id, not args.reject, args.feedback))
