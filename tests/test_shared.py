"""Tests for shared models."""

from order_fulfillment.shared import Order


def test_order_creation() -> None:
    """Test Order dataclass creation."""
    order = Order(
        order_id="test-123", item="test-item", quantity=5, credit_card_expiry="12/30"
    )

    assert order.order_id == "test-123"
    assert order.item == "test-item"
    assert order.quantity == 5
    assert order.credit_card_expiry == "12/30"
