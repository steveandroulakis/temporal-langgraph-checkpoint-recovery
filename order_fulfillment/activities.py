import asyncio
import datetime
from temporalio import activity
from temporalio.exceptions import ApplicationError
from order_fulfillment.shared import Order


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
    """Reserve items in inventory. Optionally simulate downtime with progressive failure."""
    if inventory_down:
        attempt = activity.info().attempt
        if attempt <= 4:
            print(f"Inventory service down, attempt {attempt}")
            await asyncio.sleep(10)  # Simulate 10-second delay
            raise ApplicationError(f"Inventory service down (attempt {attempt})")
        else:
            print(f"Inventory service recovered on attempt {attempt}")
            await asyncio.sleep(1)
            return f"Inventory reserved for order {order.order_id} (recovered after {attempt} attempts)"
    
    await asyncio.sleep(1)
    return f"Inventory reserved for order {order.order_id}"


@activity.defn
async def deliver_order(order: Order) -> str:
    """Simulate final order delivery."""
    await asyncio.sleep(1)
    return f"Order {order.order_id} delivered"
