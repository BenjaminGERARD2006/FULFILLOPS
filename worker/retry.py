from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.metrics import ORDERS_FAILED, WORKER_RETRIES


def calculate_backoff(attempts):
    """Calculate exponential retry delay, capped at 60 seconds."""
    return min(2 ** max(attempts - 1, 0), 60)


def handle_failure(connection, job, error):
    """Schedule a failed job for retry or move it to dead-letter."""

    attempts = job["attempts"]
    max_attempts = job["max_attempts"]
    worker_id = job["worker_id"]

    now = datetime.now(UTC)
    error_message = str(error)[:1000]

    # Maximum attempts reached: move the job to dead-letter.
    if attempts >= max_attempts:
        result = connection.execute(
            text("""
                UPDATE jobs
                SET status = 'dead',
                    locked_by = NULL,
                    locked_until = NULL,
                    last_error = :error,
                    updated_at = :now
                WHERE id = :job_id
                  AND status = 'running'
                  AND locked_by = :worker_id
                  AND locked_until > :now
            """),
            {
                "job_id": job["id"],
                "worker_id": worker_id,
                "error": error_message,
                "now": now,
            }
        )

        if result.rowcount != 1:
            return "ownership_lost"

        connection.execute(
            text("""
                UPDATE orders
                SET status = 'failed',
                    updated_at = :now
                WHERE id = :order_id
                  AND status != 'completed'
            """),
            {
                "order_id": job["order_id"],
                "now": now,
            }
        )

        # Record the terminal order failure.
        ORDERS_FAILED.inc()

        return "dead"

    # Attempts remain: schedule another retry.
    delay = calculate_backoff(attempts)
    next_attempt = now + timedelta(seconds=delay)

    result = connection.execute(
        text("""
            UPDATE jobs
            SET status = 'queued',
                available_at = :next_attempt,
                locked_by = NULL,
                locked_until = NULL,
                last_error = :error,
                updated_at = :now
            WHERE id = :job_id
              AND status = 'running'
              AND locked_by = :worker_id
              AND locked_until > :now
        """),
        {
            "job_id": job["id"],
            "worker_id": worker_id,
            "next_attempt": next_attempt,
            "error": error_message,
            "now": now,
        }
    )

    if result.rowcount != 1:
        return "ownership_lost"

    # Record a successfully scheduled retry.
    WORKER_RETRIES.inc()

    return "queued"