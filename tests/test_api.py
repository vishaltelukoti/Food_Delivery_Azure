"""API tests covering successful requests, validation, and status rules."""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app import data
from app.main import app


# AnyIO is already installed through FastAPI/Starlette.
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests with the standard asyncio backend."""
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Provide an HTTP client and fresh in-memory orders for each test."""
    data.orders.clear()
    data.next_order_id = 1
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as test_client:
        yield test_client
    data.orders.clear()
    data.next_order_id = 1


@pytest.fixture
def order_payload() -> dict[str, Any]:
    """Return a valid order payload that individual tests can modify."""
    return {
        "customer_name": "John",
        "restaurant_id": 1,
        "items": [{"name": "Pizza", "quantity": 2, "price": 250}],
    }


async def test_health(client: AsyncClient) -> None:
    """The health endpoint reports that the process is healthy."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


async def test_openapi_schema(client: AsyncClient) -> None:
    """The generated OpenAPI schema is available for APIM import."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["openapi"] == "3.0.3"
    assert schema["info"]["title"] == "Food Delivery API"
    assert schema["info"]["version"] == "1.0.0"


async def test_get_restaurants(client: AsyncClient) -> None:
    """The restaurant list includes the expected sample data."""
    response = await client.get("/restaurants")
    assert response.status_code == 200
    assert response.json()[0] == {
        "id": 1, "name": "Pizza Palace", "cuisine": "Italian", "is_open": True
    }


async def test_create_and_get_order(
    client: AsyncClient,
    order_payload: dict[str, Any],
) -> None:
    """Created orders have calculated totals, unique IDs, and can be retrieved."""
    response = await client.post("/orders", json=order_payload)
    assert response.status_code == 201
    order = response.json()
    assert order == {**order_payload, "id": 1, "total_amount": 500, "status": "PLACED"}
    fetched = await client.get(f"/orders/{order['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == order
    assert (await client.post("/orders", json=order_payload)).json()["id"] == 2


async def test_status_progression_and_terminal_state(
    client: AsyncClient,
    order_payload: dict[str, Any],
) -> None:
    """Orders advance through delivery and cannot leave the delivered state."""
    await client.post("/orders", json=order_payload)
    for status in ["CONFIRMED", "PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"]:
        response = await client.put("/orders/1/status", json={"status": status})
        assert response.status_code == 200
        assert response.json()["status"] == status
    response = await client.put("/orders/1/status", json={"status": "PREPARING"})
    assert response.status_code == 400
    assert (await client.get("/orders/1")).json()["status"] == "DELIVERED"


async def test_cancel_and_repeat_status(
    client: AsyncClient,
    order_payload: dict[str, Any],
) -> None:
    """Cancellation is final, and repeating the current status is harmless."""
    await client.post("/orders", json=order_payload)
    for _ in range(2):
        response = await client.put("/orders/1/status", json={"status": "CANCELLED"})
        assert response.status_code == 200
    response = await client.put("/orders/1/status", json={"status": "CONFIRMED"})
    assert response.status_code == 400


async def test_invalid_order_id(client: AsyncClient) -> None:
    """Unknown orders return HTTP 404 for reads and updates."""
    assert (await client.get("/orders/999")).status_code == 404
    response = await client.put("/orders/999/status", json={"status": "CONFIRMED"})
    assert response.status_code == 404


async def test_invalid_restaurant_id(
    client: AsyncClient,
    order_payload: dict[str, Any],
) -> None:
    """Creating an order for an unknown restaurant returns HTTP 404."""
    order_payload["restaurant_id"] = 999
    assert (await client.post("/orders", json=order_payload)).status_code == 404


@pytest.mark.parametrize("quantity", [0, -1, 1.5])
async def test_invalid_quantity(
    client: AsyncClient,
    order_payload: dict[str, Any],
    quantity: int | float,
) -> None:
    """Zero, negative, and fractional quantities are rejected."""
    order_payload["items"][0]["quantity"] = quantity
    assert (await client.post("/orders", json=order_payload)).status_code == 422


async def test_invalid_status(
    client: AsyncClient,
    order_payload: dict[str, Any],
) -> None:
    """Unknown status values and skipped transitions are rejected."""
    await client.post("/orders", json=order_payload)
    response = await client.put("/orders/1/status", json={"status": "UNKNOWN"})
    assert response.status_code == 422
    response = await client.put("/orders/1/status", json={"status": "READY"})
    assert response.status_code == 400


@pytest.mark.parametrize("field,value", [("customer_name", "   "), ("items", [])])
async def test_empty_fields(
    client: AsyncClient,
    order_payload: dict[str, Any],
    field: str,
    value: Any,
) -> None:
    """Blank customer names and empty item lists are rejected."""
    order_payload[field] = value
    assert (await client.post("/orders", json=order_payload)).status_code == 422


async def test_invalid_items_and_missing_fields(
    client: AsyncClient,
    order_payload: dict[str, Any],
) -> None:
    """Required fields, item names, and prices are validated."""
    assert (await client.post("/orders", json={})).status_code == 422
    order_payload["items"][0]["name"] = " "
    assert (await client.post("/orders", json=order_payload)).status_code == 422
    order_payload["items"][0]["name"] = "Pizza"
    order_payload["items"][0]["price"] = -1
    assert (await client.post("/orders", json=order_payload)).status_code == 422


async def test_server_calculates_total(
    client: AsyncClient,
    order_payload: dict[str, Any],
) -> None:
    """Totals handle decimal addition and cannot be supplied by clients."""
    order_payload["items"] = [
        {"name": "A", "quantity": 1, "price": 0.1},
        {"name": "B", "quantity": 1, "price": 0.2},
    ]
    response = await client.post("/orders", json=order_payload)
    assert response.json()["total_amount"] == 0.3
    order_payload["total_amount"] = 1
    assert (await client.post("/orders", json=order_payload)).status_code == 422
