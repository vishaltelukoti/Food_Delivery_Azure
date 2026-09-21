"""Pydantic schemas for API validation and the supported order statuses."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RequestModel(BaseModel):
    """Trim request strings before validation."""

    model_config = ConfigDict(str_strip_whitespace=True)


class OrderStatus(str, Enum):
    """Status values accepted by the API and serialized as JSON strings."""

    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class Restaurant(BaseModel):
    """A sample restaurant returned by the restaurant list endpoint."""

    id: int
    name: str
    cuisine: str
    is_open: bool


class OrderItem(RequestModel):
    """An item with a nonblank name, positive quantity, and nonnegative price."""

    name: str = Field(min_length=1)
    quantity: int = Field(strict=True)
    price: float = Field(ge=0, allow_inf_nan=False)


class OrderCreate(RequestModel):
    """Client-supplied order details; IDs, totals, and status are server-owned."""

    customer_name: str = Field(min_length=1)
    restaurant_id: int
    items: list[OrderItem] = Field(min_length=1)


class Order(BaseModel):
    """A stored order returned after creation, retrieval, or a status update."""

    id: int
    customer_name: str
    restaurant_id: int
    items: list[OrderItem]
    total_amount: float
    status: OrderStatus


class StatusUpdate(RequestModel):
    """The requested order status, checked against business rules by the endpoint."""

    status: OrderStatus


class HealthResponse(BaseModel):
    """The API health check response."""

    status: str
