
from sqlalchemy import text


def process_order(connection, job, worker_id):
    # Confirm that this worker still owns the job.
    owned_job = connection.execute(
        text("""
            SELECT id
            FROM jobs
            WHERE id = :job_id
              AND status = 'running'
              AND locked_by = :worker_id
              AND locked_until > NOW()
            FOR UPDATE
        """),
        {
            "job_id": job["id"],
            "worker_id": worker_id,
        },
    ).first()

    if owned_job is None:
        raise RuntimeError("JOB_LEASE_LOST")

    order_id = job["order_id"]

    order = connection.execute(
        text("""
            SELECT id, status
            FROM orders
            WHERE id = :order_id
            FOR UPDATE
        """),
        {"order_id": order_id},
    ).mappings().first()

    if order is None:
        raise ValueError("ORDER_NOT_FOUND")

    if order["status"] == "completed":
        return

    if order["status"] not in ("queued", "processing"):
        raise ValueError("ORDER_NOT_PROCESSABLE")

    connection.execute(
        text("""
            UPDATE orders
            SET status = 'completed',
                updated_at = NOW()
            WHERE id = :order_id
        """),
        {"order_id": order_id},
    )
