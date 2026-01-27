import asyncio
import datetime

from temporalio import activity
from temporalio.exceptions import ApplicationError

from order_fulfillment.shared import Order, PackingCheckpoint


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

    Heartbeats after every item. SDK throttles transmission automatically
    (default 30s or 80% of heartbeat_timeout, whichever is smaller).
    Most recent checkpoint is always sent on failure, so progress is preserved.
    """
    info = activity.info()
    total_items = len(items)
    start_idx = 0

    # Resume from checkpoint if available (deserializes as dict with default converter)
    if info.heartbeat_details:
        raw = info.heartbeat_details[0]
        checkpoint = (
            raw if isinstance(raw, PackingCheckpoint) else PackingCheckpoint(**raw)
        )
        start_idx = checkpoint.last_processed_idx + 1
        activity.logger.info(
            f"Resuming from checkpoint idx={checkpoint.last_processed_idx}, "
            f"last_item={checkpoint.last_item_sku}"
        )

    for idx in range(start_idx, total_items):
        sku = items[idx]
        # Simulate packing work (~10s per item, 30 items = 5 min total)
        await asyncio.sleep(10)

        progress_pct = ((idx + 1) / total_items) * 100
        activity.logger.info(
            f"Packed {sku} ({idx + 1}/{total_items}, {progress_pct:.1f}%)"
        )

        # Heartbeat with checkpoint after every item - SDK throttles automatically
        checkpoint = PackingCheckpoint(last_processed_idx=idx, last_item_sku=sku)
        activity.heartbeat(checkpoint)

    return f"Packed {total_items} items"
