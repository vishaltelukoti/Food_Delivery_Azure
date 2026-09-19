"""Food delivery endpoints and order status business rules."""

from decimal import Decimal

from fastapi import FastAPI, HTTPException, status

from app import data
from app.models import (
    HealthResponse,
    Order,
    OrderCreate,
    OrderStatus,
    Restaurant,
    StatusUpdate,
)

app = FastAPI(
    title="Food Delivery API",
    version="1.0.0",
    description="Backend API for Food Delivery platform",
)
app.openapi_version = "3.0.3"

# Move forward one step at a time. Cancellation is allowed before dispatch.
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PLACED: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.OUT_FOR_DELIVERY, OrderStatus.CANCELLED},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def find_order(order_id: int) -> Order:
    """Return a stored order, or raise HTTP 404 when its ID is unknown."""
    if order_id not in data.orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    return data.orders[order_id]


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report that the API process is running."""
    return HealthResponse(status="healthy")


@app.get("/restaurants", response_model=list[Restaurant])
async def get_restaurants() -> list[Restaurant]:
    """Return the sample restaurants, including those marked closed."""
    return data.restaurants


@app.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(request: OrderCreate) -> Order:
    """Store a new order with a server-calculated total and PLACED status.

    Raises:
        HTTPException: HTTP 404 if the restaurant does not exist.
    """
    if not any(
        restaurant.id == request.restaurant_id for restaurant in data.restaurants
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found"
        )

    # Decimal avoids common floating-point addition errors, such as 0.1 + 0.2.
    total = sum(
        (Decimal(str(item.price)) * item.quantity for item in request.items),
        Decimal("0"),
    )
    order = Order(
        id=data.next_order_id,
        **request.model_dump(),
        total_amount=float(total),
        status=OrderStatus.PLACED,
    )
    data.orders[order.id] = order
    data.next_order_id += 1
    return order


@app.get("/orders/{id}", response_model=Order)
async def get_order(id: int) -> Order:
    """Return the requested order, or HTTP 404 if it does not exist."""
    return find_order(id)


@app.put("/orders/{id}/status", response_model=Order)
async def update_order_status(id: int, request: StatusUpdate) -> Order:
    """Apply an allowed status transition or return the unchanged current status.

    Raises:
        HTTPException: HTTP 404 for an unknown order, or HTTP 400 for a
            transition that skips a step, moves backward, or leaves a final state.
    """
    order = find_order(id)
    # Repeating the current status is harmless and returns the existing order.
    if request.status == order.status:
        return order
    if request.status not in ALLOWED_TRANSITIONS[order.status]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot change status from {order.status.value} "
                f"to {request.status.value}"
            ),
        )
    order.status = request.status
    return order
