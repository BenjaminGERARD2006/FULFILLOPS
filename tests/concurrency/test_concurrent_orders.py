
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import SessionLocal
from app.main import app
from app.models import (
    IdempotencyRecord,
    Inventory,
    Job,
    Order,
    OrderItem,
)


def test_concurrent_orders_never_oversell():
    """Ten customers compete for seven available units."""

    def place_order(customer_number: int):
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/orders",
                headers={
                    "Idempotency-Key": (
                        f"concurrent-order-{customer_number:03d}"
                    )
                },
                json={
                    "customer_id": f"CUST-{customer_number:03d}",
                    "items": [{"sku": "KIT-100", "quantity": 1}],
                },
            )

            if response.status_code == 202:
                return "accepted"

            if response.status_code == 409:
                return "out_of_stock"

            raise AssertionError(
                f"Unexpected response: "
                f"{response.status_code} {response.text}"
            )

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(place_order, range(10)))

    assert results.count("accepted") == 7
    assert results.count("out_of_stock") == 3

    with SessionLocal() as db:
        inventory = db.get(Inventory, "KIT-100")

        order_count = db.scalar(
            select(func.count()).select_from(Order)
        )

        job_count = db.scalar(
            select(func.count()).select_from(Job)
        )

        assert inventory.available == 0
        assert order_count == 7
        assert job_count == 7


def test_eight_concurrent_identical_requests_create_one_order():
    """Eight simultaneous requests with one key reserve stock once."""

    shared_key = "pytest-same-key-concurrent-001"

    def submit_request(_):
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/orders",
                headers={"Idempotency-Key": shared_key},
                json={
                    "customer_id": "CUST-SHARED",
                    "items": [{"sku": "KIT-100", "quantity": 1}],
                },
            )

            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(submit_request, range(8)))

    # Every request must receive an accepted receipt.
    assert all(status == 202 for status, _ in results)

    # Every request must return exactly the same order ID.
    order_ids = {
        body["order_id"]
        for _, body in results
    }

    assert len(order_ids) == 1

    with SessionLocal() as db:
        inventory = db.get(Inventory, "KIT-100")

        order_count = db.scalar(
            select(func.count()).select_from(Order)
        )

        job_count = db.scalar(
            select(func.count()).select_from(Job)
        )

        idempotency_count = db.scalar(
            select(func.count()).select_from(IdempotencyRecord)
        )

        assert inventory.available == 6
        assert order_count == 1
        assert job_count == 1
        assert idempotency_count == 1


def test_duplicate_sku_lines_are_combined():
    """Repeated SKU lines are combined before reservation and billing."""

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders",
            headers={
                "Idempotency-Key": "pytest-multiline-001"
            },
            json={
                "customer_id": "CUST-MULTI",
                "items": [
                    {"sku": "PACK-300", "quantity": 2},
                    {"sku": "PACK-300", "quantity": 2},
                ],
            },
        )

    assert response.status_code == 202

    order_id = response.json()["order_id"]

    with SessionLocal() as db:
        inventory = db.get(Inventory, "PACK-300")
        order = db.get(Order, order_id)

        items = db.scalars(
            select(OrderItem).where(
                OrderItem.order_id == order.id
            )
        ).all()

        assert inventory.available == 1
        assert order.total_cents == 996

        assert len(items) == 1
        assert items[0].sku == "PACK-300"
        assert items[0].quantity == 4
