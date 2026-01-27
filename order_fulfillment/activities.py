import asyncio
import datetime
import uuid

from temporalio import activity
from temporalio.exceptions import ApplicationError

from order_fulfillment.shared import Order, PackingCheckpoint


def _restore_checkpoint(heartbeat_details: list) -> PackingCheckpoint | None:
    """Restore checkpoint from heartbeat details, handling dict/object conversion."""
    if not heartbeat_details:
        return None
    raw = heartbeat_details[0]
    return raw if isinstance(raw, PackingCheckpoint) else PackingCheckpoint(**raw)


def _generate_packing_slip_id() -> str:
    """Generate unique packing slip ID (simulates external API call)."""
    return f"SLIP-{uuid.uuid4().hex[:8].upper()}"


@activity.defn
async def process_payment(order: Order) -> str:
    """Validate payment and simulate processing."""
    exp_month, exp_year = map(int, order.credit_card_expiry.split("/"))
    exp_year += 2000
    now = datetime.datetime.now()
    if exp_year < now.year or (exp_year == now.year and exp_month < now.month):
        raise ApplicationError("Invalid credit card expiry")
    await asyncio.sleep(1)
    return f"Payment processed for order {order.order_id}"


@activity.defn
async def reserve_inventory(order: Order, inventory_down: bool = False) -> str:
    """Reserve items in inventory. Simulate downtime with progressive failure."""
    if inventory_down:
        attempt = activity.info().attempt
        if attempt <= 4:
            print(f"Inventory service down, attempt {attempt}")
            await asyncio.sleep(10)  # Simulate 10-second delay
            raise ApplicationError(f"Inventory service down (attempt {attempt})")
        else:
            print(f"Inventory service recovered on attempt {attempt}")
            await asyncio.sleep(1)
            return (
                f"Inventory reserved for order {order.order_id} "
                f"(recovered after {attempt} attempts)"
            )

    await asyncio.sleep(1)
    return f"Inventory reserved for order {order.order_id}"


@activity.defn
async def deliver_order(order: Order) -> str:
    """Simulate final order delivery."""
    await asyncio.sleep(1)
    return f"Order {order.order_id} delivered"


@activity.defn
async def pack_order_items(items: list[str]) -> str:
    """Pack items with heartbeat checkpointing for recovery on failure.

    Uses a background heartbeat task to ensure heartbeats continue even if
    individual items take longer than expected. Checkpoints are updated after
    each item completes, and the background task sends the latest checkpoint
    every 5 seconds.
    """
    info = activity.info()
    total_items = len(items)
    start_idx = 0
    packing_slip_id: str | None = None

    # Resume from checkpoint if available
    checkpoint = _restore_checkpoint(info.heartbeat_details)
    if checkpoint:
        start_idx = checkpoint.last_processed_idx + 1
        packing_slip_id = checkpoint.packing_slip_id
        activity.logger.info(
            f"Resuming from checkpoint idx={checkpoint.last_processed_idx}, "
            f"last_item={checkpoint.last_item_sku}, slip_id={packing_slip_id}"
        )

    # Acquire packing slip ID if not resuming
    if not packing_slip_id:
        packing_slip_id = _generate_packing_slip_id()
        activity.logger.info(f"Acquired new packing slip ID: {packing_slip_id}")
        # Heartbeat immediately to persist the ID before doing any work
        checkpoint = PackingCheckpoint(
            last_processed_idx=-1, last_item_sku="not_started", packing_slip_id=packing_slip_id
        )
        activity.heartbeat(checkpoint)

    # Background heartbeat task - sends latest checkpoint every 5s
    async def heartbeat_loop() -> None:
        while True:
            await asyncio.sleep(5)
            if checkpoint:
                activity.heartbeat(checkpoint)

    heartbeat_task = asyncio.create_task(heartbeat_loop())
    try:
        for idx in range(start_idx, total_items):
            sku = items[idx]
            # Simulate packing work (~10s per item, 30 items = 5 min total)
            await asyncio.sleep(10)

            progress_pct = ((idx + 1) / total_items) * 100
            activity.logger.info(
                f"Packed {sku} ({idx + 1}/{total_items}, {progress_pct:.1f}%)"
            )

            # Update checkpoint and send immediately
            checkpoint = PackingCheckpoint(
                last_processed_idx=idx, last_item_sku=sku, packing_slip_id=packing_slip_id
            )
            activity.heartbeat(checkpoint)
            activity.logger.info(f"Checkpoint saved at idx={idx}")
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

    return f"Packed {total_items} items (slip: {packing_slip_id})"
