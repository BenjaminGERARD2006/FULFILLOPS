from datetime import UTC, datetime

from sqlalchemy import text

from app.metrics import ORDERS_FAILED, WORKER_RETRIES


def recover_expired_jobs(connection):
    """Recover jobs whose worker leases have expired."""

    now = datetime.now(UTC)

    # Jobs that exhausted their attempts go to dead-letter.
    exhausted = connection.execute(
        text("""
            UPDATE jobs
            SET status = 'dead',
                locked_by = NULL,
                locked_until = NULL,
                last_error = 'Worker lease expired after maximum attempts',
                updated_at = :now
            WHERE status = 'running'
              AND locked_until <= :now
              AND attempts >= max_attempts
            RETURNING order_id
        """),
        {"now": now},
    ).mappings().all()

    # Mark the corresponding orders as failed.
    for row in exhausted:
        connection.execute(
            text("""
                UPDATE orders
                SET status = 'failed',
                    updated_at = :now
                WHERE id = :order_id
                  AND status != 'completed'
            """),
            {
                "now": now,
                "order_id": row["order_id"],
            },
        )

    # Record terminal failures.
    if exhausted:
        ORDERS_FAILED.inc(len(exhausted))

    # Jobs with attempts remaining return to the queue.
    recovered = connection.execute(
        text("""
            UPDATE jobs
            SET status = 'queued',
                locked_by = NULL,
                locked_until = NULL,
                available_at = :now,
                updated_at = :now
            WHERE status = 'running'
              AND locked_until <= :now
              AND attempts < max_attempts
        """),
        {"now": now},
    )

    recovered_count = recovered.rowcount

    # Record recovered jobs as additional retry attempts.
    if recovered_count:
        WORKER_RETRIES.inc(recovered_count)

    return recovered_count + len(exhausted)