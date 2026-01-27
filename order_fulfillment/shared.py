from dataclasses import dataclass, field


@dataclass
class Order:
    order_id: str
    item: str
    quantity: int
    credit_card_expiry: str  # MM/YY
    items_to_pack: list[str] = field(default_factory=list)


@dataclass
class PackingCheckpoint:
    last_processed_idx: int
    last_item_sku: str
