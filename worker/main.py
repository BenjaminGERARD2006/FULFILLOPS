import logging
import time

from prometheus_client import start_http_server
from sqlalchemy import create_engine, text

from worker.config import (
    DATABASE_URL,
    POLL_INTERVAL,
    WORKER_ID,
)
from worker.job_claim import claim_job
from worker.processor import process_order
from worker.recovery import recover_expired_jobs
from worker.retry import handle_failure

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


def run_worker():
    logger.info("Worker started: %s", WORKER_ID)

    while True:
        try:
            # 1. Recover jobs abandoned by crashed workers.
            with engine.begin() as connection:
                recovered = recover_expired_jobs(connection)

                if recovered:
                    logger.info(
                        "Recovered %s expired jobs",
                        recovered,
                    )

            # 2. Claim one available queued job.
            with engine.begin() as connection:
                job = claim_job(connection, WORKER_ID)

            # 3. Wait if there are no available jobs.
            if job is None:
                time.sleep(POLL_INTERVAL)
                continue

            logger.info("Claimed job: %s", job["id"])

            # 4. Process the job and mark it completed.
            try:
                with engine.begin() as connection:
                    process_order(connection, job, WORKER_ID)

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
                            "job_id": job["id"],
                            "worker_id": WORKER_ID,
                        },
                    )

                    if result.rowcount != 1:
                        raise RuntimeError(
                            "JOB_COMPLETION_OWNERSHIP_LOST"
                        )

                logger.info(
                    "Completed job: %s",
                    job["id"],
                )

            except Exception as error:
                logger.exception(
                    "Failed processing job %s",
                    job["id"],
                )

                # 5. Schedule a retry or move the job to dead-letter.
                job_with_worker = {
                    **job,
                    "worker_id": WORKER_ID,
                }

                with engine.begin() as connection:
                    handle_failure(
                        connection,
                        job_with_worker,
                        error,
                    )

        except Exception:
            logger.exception("Worker loop encountered an error")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    # Expose this worker's Prometheus metrics on port 9101.
    start_http_server(port=9101, addr="0.0.0.0")

    logger.info("Worker metrics endpoint listening on port 9101")

    try:
        run_worker()
    except KeyboardInterrupt:
        logger.info("Worker stopped")
    finally:
        engine.dispose()