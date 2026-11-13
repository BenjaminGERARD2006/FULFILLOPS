
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text

from app.database import engine
from worker.job_claim import claim_job
from worker.processor import process_order


def create_queued_job(connection):
    order_id = uuid4()
    job_id = uuid4()

    connection.execute(
        text("""
            INSERT INTO orders (
                id, customer_id, status, total_cents
            )
            VALUES (
                :id, :customer_id, 'queued', :total_cents
            )
        """),
        {
            "id": order_id,
            "customer_id": "worker-test-customer",
            "total_cents": 1299,
        },
    )

    connection.execute(
        text("""
            INSERT INTO jobs (
                id, order_id, status, attempts, max_attempts,
                available_at
            )
            VALUES (
                :id, :order_id, 'queued', 0, 5, :available_at
            )
        """),
        {
            "id": job_id,
            "order_id": order_id,
            "available_at": datetime.now(UTC),
        },
    )

    return job_id, order_id


def test_worker_claims_and_completes_order():
    worker_id = "integration-test-worker"

    with engine.begin() as connection:
        job_id, order_id = create_queued_job(connection)

    with engine.begin() as connection:
        job = claim_job(connection, worker_id)

    assert job is not None
    assert job["id"] == job_id
    assert job["order_id"] == order_id
    assert job["attempts"] == 1

    with engine.begin() as connection:
        process_order(connection, job, worker_id)

        result = connection.execute(
            text("""
                UPDATE jobs
                SET status = 'completed',
                    locked_by = NULL,
                    locked_until = NULL,
                    updated_at = NOW()
                WHERE id = :job_id
                  AND status = 'running'
                  AND locked_by = :worker_id
                  AND locked_until > NOW()
            """),
            {
                "job_id": job_id,
                "worker_id": worker_id,
            },
        )

        assert result.rowcount == 1

    with engine.connect() as connection:
        order_status = connection.execute(
            text("SELECT status FROM orders WHERE id = :id"),
            {"id": order_id},
        ).scalar_one()

        job_status = connection.execute(
            text("SELECT status FROM jobs WHERE id = :id"),
            {"id": job_id},
        ).scalar_one()

    assert order_status == "completed"
    assert job_status == "completed"
