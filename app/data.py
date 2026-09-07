"""Sample data and mutable order storage, isolated to one Python process."""

from app.models import Order, Restaurant


restaurants: list[Restaurant] = [
    Restaurant(id=1, name="Pizza Palace", cuisine="Italian", is_open=True),
    Restaurant(id=2, name="Curry Corner", cuisine="Indian", is_open=True),
    Restaurant(id=3, name="Burger Barn", cuisine="American", is_open=False),
]

# These orders exist only in this Python process and disappear on restart.
orders: dict[int, Order] = {}
next_order_id: int = 1
