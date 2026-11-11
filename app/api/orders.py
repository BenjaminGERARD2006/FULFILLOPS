
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order
from app.schemas.orders import OrderCreateRequest
from app.services.orders import (
    IdempotencyConflict,
    InvalidSKU,
    OutOfStock,
    create_order,
)

router = APIRouter(prefix="/api/v1", tags=["orders"])

MAX_REQUEST_BYTES = 16 * 1024


def error_response(status_code: int, code: str, message: str):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


@router.post("/orders", status_code=202)
async def submit_order(
    request: Request,
    db: Session = Depends(get_db),
):
    # Check the idempotency header before processing the request.
    idempotency_key = request.headers.get("Idempotency-Key")

    if idempotency_key is None:
        return error_response(
            400,
            "IDEMPOTENCY_REQUIRED",
            "The Idempotency-Key header is required",
        )

    valid_key = (
        8 <= len(idempotency_key) <= 128
        and all(32 <= ord(char) <= 126 for char in idempotency_key)
    )

    if not valid_key:
        return error_response(
            400,
            "INVALID_REQUEST",
            "The Idempotency-Key must contain 8 to 128 printable ASCII characters",
        )

    # Enforce the request body size limit.
    body = await request.body()

    if len(body) > MAX_REQUEST_BYTES:
        return error_response(
            400,
            "INVALID_REQUEST",
            "Request body exceeds the 16 KiB limit",
        )

    # Parse JSON separately to provide the contract's exact error code.
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return error_response(
            400,
            "INVALID_JSON",
            "Request body must contain valid JSON",
        )

    # Validate the request structure and field types.
    try:
        order_request = OrderCreateRequest.model_validate(payload)

    except ValidationError as exc:
        errors = exc.errors()

        # Invalid quantity has its own contract error code.
        if any("quantity" in error["loc"] for error in errors):
            return error_response(
                422,
                "INVALID_QUANTITY",
                "Quantity must be an integer between 1 and 20",
            )

        # Invalid SKU formatting/type also has its own error code.
        if any("sku" in error["loc"] for error in errors):
            return error_response(
                422,
                "INVALID_SKU",
                "SKU must be a valid string",
            )

        return error_response(
            400,
            "INVALID_REQUEST",
            "Request fields are missing or invalid",
        )

    # Create the order, reserve stock and create the durable job.
    try:
        result = create_order(
            db=db,
            request_data=order_request,
            idempotency_key=idempotency_key,
        )

        return JSONResponse(
            status_code=202,
            content=result,
        )

    except InvalidSKU:
        return error_response(
            422,
            "INVALID_SKU",
            "One or more product SKUs do not exist",
        )

    except OutOfStock:
        return error_response(
            409,
            "OUT_OF_STOCK",
            "Not enough items available",
        )

    except IdempotencyConflict:
        return error_response(
            409,
            "IDEMPOTENCY_CONFLICT",
            "Idempotency key was already used with a different request",
        )


@router.get("/orders/{order_id}")
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
):
    try:
        parsed_id = UUID(order_id)
    except ValueError:
        return error_response(
            404,
            "ORDER_NOT_FOUND",
            "Order not found",
        )

    order = db.get(Order, parsed_id)

    if order is None:
        return error_response(
            404,
            "ORDER_NOT_FOUND",
            "Order not found",
        )

    return {
        "order_id": str(order.id),
        "status": order.status,
        "total_cents": order.total_cents,
    }
