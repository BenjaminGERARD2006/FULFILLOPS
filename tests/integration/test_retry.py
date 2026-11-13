
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text

from app.database import engine
from worker.job_claim import claim_job
from worker.retry import handle_failure


def create_queued_job(connection, max_attempts=5):
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
            "customer_id": "retry-test-customer",
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
                :id, :order_id, 'queued', 0, :max_attempts,
                :available_at
            )
        """),
        {
            "id": job_id,
            "order_id": order_id,
            "max_attempts": max_attempts,
            "available_at": datetime.now(UTC),
        },
    )

    return job_id, order_id


def test_failed_job_is_scheduled_for_retry():
    worker_id = "retry-test-worker"

    with engine.begin() as connection:
        job_id, _order_id = create_queued_job(connection)

    with engine.begin() as connection:
        job = claim_job(connection, worker_id)

    assert job is not None
    assert job["id"] == job_id

    job_with_worker = {
        **job,
        "worker_id": worker_id,
    }

    with engine.begin() as connection:
        result = handle_failure(
            connection,
            job_with_worker,
            RuntimeError("Temporary processing failure"),
        )

    assert result == "queued"

    with engine.connect() as connection:
        saved_job = connection.execute(
            text("""
                SELECT status, attempts, locked_by,
                       locked_until, last_error, available_at
                FROM jobs
                WHERE id = :id
            """),
            {"id": job_id},
        ).mappings().one()

    assert saved_job["status"] == "queued"
    assert saved_job["attempts"] == 1
    assert saved_job["locked_by"] is None
    assert saved_job["locked_until"] is None
    assert saved_job["last_error"] == "Temporary processing failure"

    delay = (saved_job["available_at"] - datetime.now(UTC)).total_seconds()
    assert 0 < delay <= 1.5


def test_job_moves_to_dead_after_maximum_attempts():
    worker_id = "dead-letter-test-worker"

    with engine.begin() as connection:
        job_id, order_id = create_queued_job(
            connection,
            max_attempts=1,
        )

    with engine.begin() as connection:
        job = claim_job(connection, worker_id)

    assert job is not None
    assert job["id"] == job_id
    assert job["attempts"] == 1

    job_with_worker = {
        **job,
        "worker_id": worker_id,
    }

    with engine.begin() as connection:
        result = handle_failure(
            connection,
            job_with_worker,
            RuntimeError("Permanent processing failure"),
        )

    assert result == "dead"

    with engine.connect() as connection:
        job_status = connection.execute(
            text("SELECT status FROM jobs WHERE id = :id"),
            {"id": job_id},
        ).scalar_one()

        order_status = connection.execute(
            text("SELECT status FROM orders WHERE id = :id"),
            {"id": order_id},
        ).scalar_one()

    assert job_status == "dead"
    assert order_status == "failed"
