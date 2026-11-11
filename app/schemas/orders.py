
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
)


class OrderItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: StrictStr = Field(min_length=1, max_length=32)
    quantity: StrictInt = Field(ge=1, le=20)


class OrderCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: StrictStr = Field(min_length=1, max_length=64)
    items: list[OrderItemCreate] = Field(min_length=1, max_length=10)

    @field_validator("customer_id")
    @classmethod
    def customer_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Customer ID cannot be blank")
        return value


class OrderAcceptedResponse(BaseModel):
    order_id: str
    status: Literal["queued"]


class OrderStatusResponse(BaseModel):
    order_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    total_cents: int
