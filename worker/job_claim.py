

from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from worker.config import LEASE_SECONDS


def claim_job(connection, worker_id: str):
    now = datetime.now(UTC)
    lease_until = now + timedelta(seconds=LEASE_SECONDS)

    # Lock one available job so another worker cannot claim it
    # at the same time.
    result = connection.execute(
        text("""
            SELECT id, order_id, attempts, max_attempts
            FROM jobs
            WHERE status = 'queued'
              AND available_at <= :now
              AND attempts < max_attempts
            ORDER BY created_at, id
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        """),
        {"now": now},
    ).mappings().first()

    if result is None:
        return None

    connection.execute(
        text("""
            UPDATE jobs
            SET status = 'running',
                attempts = attempts + 1,
                locked_by = :worker_id,
                locked_until = :lease_until,
                updated_at = :now
            WHERE id = :job_id
        """),
        {
            "worker_id": worker_id,
            "lease_until": lease_until,
            "now": now,
            "job_id": result["id"],
        },
    )

    return {
        "id": result["id"],
        "order_id": result["order_id"],
        "attempts": result["attempts"] + 1,
        "max_attempts": result["max_attempts"],
    }
