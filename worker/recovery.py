
from datetime import UTC, datetime

from sqlalchemy import text


def recover_expired_jobs(connection):
    now = datetime.now(UTC)

    # Jobs that have exhausted their attempts go to dead-letter.
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

    return recovered.rowcount + len(exhausted)
