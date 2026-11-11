
import hashlib
import json
from collections import defaultdict

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.metrics import ORDERS_CREATED
from app.models import (
    IdempotencyRecord,
    Inventory,
    Job,
    Order,
    OrderItem,
    Product,
)
from app.schemas.orders import OrderCreateRequest


class OrderError(Exception):
    pass


class InvalidSKU(OrderError):
    pass


class OutOfStock(OrderError):
    pass


class IdempotencyConflict(OrderError):
    pass


def create_order(
    db: Session,
    request_data: OrderCreateRequest,
    idempotency_key: str,
) -> dict:

    # Combine repeated SKU lines.
    quantities = defaultdict(int)

    for item in request_data.items:
        quantities[item.sku] += item.quantity

    normalized_items = [
        {"sku": sku, "quantity": quantity}
        for sku, quantity in sorted(quantities.items())
    ]

    # Create a stable hash of the request.
    canonical_payload = {
        "customer_id": request_data.customer_id,
        "items": normalized_items,
    }

    payload_json = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    payload_hash = hashlib.sha256(
        payload_json.encode("utf-8")
    ).hexdigest()

    accepted_order_id = None
    created_new_order = False

    # All database changes happen in one transaction.
    with db.begin():

        # Serialize requests with the same idempotency key.
        lock_id = int.from_bytes(
            hashlib.sha256(
                idempotency_key.encode("ascii")
            ).digest()[:8],
            byteorder="big",
            signed=True,
        )

        db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": lock_id},
        )

        # Check whether this request was already accepted.
        existing = db.get(
            IdempotencyRecord,
            idempotency_key,
        )

        if existing is not None:

            if existing.payload_hash != payload_hash:
                raise IdempotencyConflict(
                    "Idempotency key was used with a different request"
                )

            # Return the original order without reserving stock again.
            accepted_order_id = str(existing.order_id)

        else:

            skus = list(quantities.keys())

            products = db.scalars(
                select(Product).where(Product.sku.in_(skus))
            ).all()

            products_by_sku = {
                product.sku: product
                for product in products
            }

            # Reject unknown SKUs.
            unknown_skus = set(skus) - set(products_by_sku)

            if unknown_skus:
                raise InvalidSKU(
                    "One or more product SKUs do not exist"
                )

            # Calculate total using integer cents.
            total_cents = sum(
                products_by_sku[sku].unit_price_cents * quantity
                for sku, quantity in quantities.items()
            )

            # Reserve inventory atomically.
            # A conditional UPDATE prevents overselling.
            # Sorting SKUs gives transactions a consistent lock order.
            for sku in sorted(skus):

                quantity = quantities[sku]

                reserved_sku = db.execute(
                    update(Inventory)
                    .where(
                        Inventory.sku == sku,
                        Inventory.available >= quantity,
                    )
                    .values(
                        available=Inventory.available - quantity
                    )
                    .returning(Inventory.sku)
                ).scalar_one_or_none()

                if reserved_sku is None:
                    raise OutOfStock(
                        "Not enough items available"
                    )

            # Create order.
            order = Order(
                customer_id=request_data.customer_id,
                status="queued",
                total_cents=total_cents,
            )

            db.add(order)
            db.flush()

            # Create order items.
            for line in normalized_items:

                sku = line["sku"]
                quantity = line["quantity"]

                db.add(
                    OrderItem(
                        order_id=order.id,
                        sku=sku,
                        quantity=quantity,
                        unit_price_cents=products_by_sku[
                            sku
                        ].unit_price_cents,
                    )
                )

            # Save idempotency record.
            db.add(
                IdempotencyRecord(
                    idempotency_key=idempotency_key,
                    payload_hash=payload_hash,
                    order_id=order.id,
                )
            )

            # Create durable background job.
            db.add(
                Job(
                    order_id=order.id,
                    status="queued",
                )
            )

            db.flush()

            accepted_order_id = str(order.id)
            created_new_order = True

    # The transaction has committed successfully at this point.
    if created_new_order:
        ORDERS_CREATED.inc()

    return {
        "order_id": accepted_order_id,
        "status": "queued",
    }
