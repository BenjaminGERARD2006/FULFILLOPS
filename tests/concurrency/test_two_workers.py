
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

from sqlalchemy import text

from app.database import engine
from worker.job_claim import claim_job


def test_two_workers_cannot_claim_same_job():
    order_id = uuid4()
    job_id = uuid4()

    with engine.begin() as connection:
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
                "customer_id": "concurrency-test-customer",
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

    start_barrier = Barrier(2)
    finish_barrier = Barrier(2)

    def try_claim(worker_id):
        with engine.connect() as connection:
            transaction = connection.begin()

            try:
                start_barrier.wait(timeout=10)

                job = claim_job(connection, worker_id)

                # Keep the transaction open until both workers
                # have attempted to claim the job.
                finish_barrier.wait(timeout=10)

                transaction.commit()
                return job

            except Exception:
                transaction.rollback()
                raise

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(try_claim, "worker-A"),
            executor.submit(try_claim, "worker-B"),
        ]

        results = [future.result(timeout=20) for future in futures]

    successful_claims = [
        result for result in results if result is not None
    ]

    assert len(successful_claims) == 1
    assert successful_claims[0]["id"] == job_id
    assert successful_claims[0]["attempts"] == 1
