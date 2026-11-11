from uuid import UUID

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

client = TestClient(app)


def submit_order(key, items=None, customer_id="CUST-TEST"):
    if items is None:
        items = [{"sku": "KIT-100", "quantity": 1}]

    return client.post(
        "/api/v1/orders",
        headers={"Idempotency-Key": key},
        json={
            "customer_id": customer_id,
            "items": items,
        },
    )


def test_health_endpoints():
    live = client.get("/health/live")
    ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.json() == {"status": "ok"}

    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}


def test_catalog_contains_fixed_products():
    response = client.get("/api/v1/catalog")

    assert response.status_code == 200

    products = {
        item["sku"]: item["unit_price_cents"]
        for item in response.json()["products"]
    }

    assert products == {
        "KIT-100": 1299,
        "PART-200": 599,
        "PACK-300": 249,
    }


def test_inventory_endpoint():
    response = client.get("/api/v1/inventory/KIT-100")

    assert response.status_code == 200
    assert response.json() == {
        "sku": "KIT-100",
        "available": 7,
    }


def test_unknown_inventory_sku():
    response = client.get("/api/v1/inventory/UNKNOWN")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SKU_NOT_FOUND"


def test_missing_idempotency_key():
    response = client.post(
        "/api/v1/orders",
        json={
            "customer_id": "CUST-TEST",
            "items": [{"sku": "KIT-100", "quantity": 1}],
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IDEMPOTENCY_REQUIRED"


def test_create_order_persists_all_records():
    key = "pytest-create-001"

    response = submit_order(key)

    assert response.status_code == 202

    data = response.json()
    order_id = data["order_id"]

    assert data["status"] == "queued"
    assert isinstance(order_id, str)
    assert order_id

    with SessionLocal() as db:
        order = db.get(Order, UUID(order_id))
        record = db.get(IdempotencyRecord, key)
        inventory = db.get(Inventory, "KIT-100")

        items = db.scalars(
            select(OrderItem).where(OrderItem.order_id == order.id)
        ).all()

        job = db.scalar(
            select(Job).where(Job.order_id == order.id)
        )

        assert order is not None
        assert order.customer_id == "CUST-TEST"
        assert order.status == "queued"
        assert order.total_cents == 1299

        assert record is not None
        assert record.order_id == order.id

        assert len(items) == 1
        assert items[0].sku == "KIT-100"
        assert items[0].quantity == 1

        assert job is not None
        assert job.status == "queued"
        assert job.attempts == 0

        assert inventory.available == 6


def test_identical_idempotency_replay_reserves_once():
    key = "pytest-replay-001"

    first = submit_order(key)
    second = submit_order(key)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["order_id"] == second.json()["order_id"]

    with SessionLocal() as db:
        order_count = db.scalar(
            select(func.count()).select_from(Order)
        )

        job_count = db.scalar(
            select(func.count()).select_from(Job)
        )

        inventory = db.get(Inventory, "KIT-100")

        assert order_count == 1
        assert job_count == 1
        assert inventory.available == 6


def test_idempotency_conflict():
    key = "pytest-conflict-001"

    first = submit_order(key, [
        {"sku": "KIT-100", "quantity": 1}
    ])

    second = submit_order(key, [
        {"sku": "KIT-100", "quantity": 2}
    ])

    assert first.status_code == 202
    assert second.status_code == 409

    assert (
        second.json()["error"]["code"]
        == "IDEMPOTENCY_CONFLICT"
    )

    with SessionLocal() as db:
        inventory = db.get(Inventory, "KIT-100")
        assert inventory.available == 6


def test_insufficient_stock_rolls_back_all_reservations():
    response = submit_order(
        "pytest-stock-001",
        [
            {"sku": "KIT-100", "quantity": 1},
            {"sku": "PART-200", "quantity": 13},
        ],
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "OUT_OF_STOCK"

    with SessionLocal() as db:
        kit = db.get(Inventory, "KIT-100")
        part = db.get(Inventory, "PART-200")

        order_count = db.scalar(
            select(func.count()).select_from(Order)
        )

        job_count = db.scalar(
            select(func.count()).select_from(Job)
        )

        assert kit.available == 7
        assert part.available == 12
        assert order_count == 0
        assert job_count == 0


def test_unknown_product_is_rejected():
    response = submit_order(
        "pytest-sku-001",
        [{"sku": "UNKNOWN", "quantity": 1}],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SKU"


def test_invalid_quantity_is_rejected():
    response = submit_order(
        "pytest-quantity-001",
        [{"sku": "KIT-100", "quantity": 0}],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_QUANTITY"


def test_boolean_quantity_is_rejected():
    response = submit_order(
        "pytest-boolean-001",
        [{"sku": "KIT-100", "quantity": True}],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_QUANTITY"


def test_order_retrieval():
    creation = submit_order("pytest-get-001")

    assert creation.status_code == 202

    order_id = creation.json()["order_id"]

    response = client.get(f"/api/v1/orders/{order_id}")

    assert response.status_code == 200
    assert response.json() == {
        "order_id": order_id,
        "status": "queued",
        "total_cents": 1299,
    }


def test_unknown_order_returns_404():
    response = client.get(
        "/api/v1/orders/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORDER_NOT_FOUND"


def test_metrics_endpoint():
    client.get("/health/live")

    response = client.get("/metrics")

    assert response.status_code == 200

    metrics = response.text

    assert "fulfillops_orders_created_total" in metrics
    assert "fulfillops_orders_failed_total" in metrics
    assert "fulfillops_worker_retries_total" in metrics
    assert "fulfillops_http_requests_total" in metrics
    assert "fulfillops_http_request_duration_seconds" in metrics


def test_invalid_idempotency_key():
    response = submit_order("short")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_invalid_json_body():
    response = client.post(
        "/api/v1/orders",
        headers={
            "Idempotency-Key": "pytest-invalid-json-001",
            "Content-Type": "application/json",
        },
        content="{invalid-json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_JSON"


def test_request_body_too_large():
    response = client.post(
        "/api/v1/orders",
        headers={
            "Idempotency-Key": "pytest-large-body-001",
            "Content-Type": "application/json",
        },
        content=b"x" * (16 * 1024 + 1),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_missing_order_fields():
    response = client.post(
        "/api/v1/orders",
        headers={"Idempotency-Key": "pytest-missing-fields-001"},
        json={"customer_id": "CUST-TEST"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_non_string_sku_is_rejected():
    response = submit_order(
        "pytest-wrong-sku-type-001",
        [{"sku": 123, "quantity": 1}],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SKU"


def test_malformed_order_id_returns_404():
    response = client.get("/api/v1/orders/not-a-uuid")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORDER_NOT_FOUND"
