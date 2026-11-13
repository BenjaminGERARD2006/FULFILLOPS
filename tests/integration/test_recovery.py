
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import text

from app.database import engine
from worker.recovery import recover_expired_jobs


def create_expired_job(connection, attempts, max_attempts):
    order_id = uuid4()
    job_id = uuid4()
    now = datetime.now(UTC)

    connection.execute(
        text("""
            INSERT INTO orders (
                id, customer_id, status, total_cents
            )
            VALUES (
                :id, :customer_id, 'processing', :total_cents
            )
        """),
        {
            "id": order_id,
            "customer_id": "recovery-test-customer",
            "total_cents": 1299,
        },
    )

    connection.execute(
        text("""
            INSERT INTO jobs (
                id, order_id, status, attempts, max_attempts,
                available_at, locked_by, locked_until
            )
            VALUES (
                :id, :order_id, 'running', :attempts, :max_attempts,
                :now, 'crashed-worker', :expired_at
            )
        """),
        {
            "id": job_id,
            "order_id": order_id,
            "attempts": attempts,
            "max_attempts": max_attempts,
            "now": now,
            "expired_at": now - timedelta(seconds=60),
        },
    )

    return job_id, order_id


def test_expired_job_returns_to_queue():
    with engine.begin() as connection:
        job_id, order_id = create_expired_job(
            connection,
            attempts=1,
            max_attempts=5,
        )

    with engine.begin() as connection:
        recovered = recover_expired_jobs(connection)

    assert recovered == 1

    with engine.connect() as connection:
        job = connection.execute(
            text("""
                SELECT status, locked_by, locked_until
                FROM jobs
                WHERE id = :id
            """),
            {"id": job_id},
        ).mappings().one()

        order_status = connection.execute(
            text("SELECT status FROM orders WHERE id = :id"),
            {"id": order_id},
        ).scalar_one()

    assert job["status"] == "queued"
    assert job["locked_by"] is None
    assert job["locked_until"] is None
    assert order_status == "processing"


def test_expired_job_at_max_attempts_becomes_dead():
    with engine.begin() as connection:
        job_id, order_id = create_expired_job(
            connection,
            attempts=5,
            max_attempts=5,
        )

    with engine.begin() as connection:
        recovered = recover_expired_jobs(connection)

    assert recovered == 1

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
