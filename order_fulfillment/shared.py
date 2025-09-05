from dataclasses import dataclass


@dataclass
class Order:
    order_id: str
    item: str
    quantity: int
    credit_card_expiry: str  # MM/YY
