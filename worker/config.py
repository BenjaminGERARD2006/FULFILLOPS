import os
import socket

from app.config import settings

# Use the exact same database connection as the backend.
DATABASE_URL = settings.database_url

# Use an explicit ID when configured; otherwise use the
# unique hostname assigned to this worker container or pod.
WORKER_ID = os.getenv("WORKER_ID") or socket.gethostname()

POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2"))

MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "5"))

LEASE_SECONDS = int(os.getenv("LEASE_SECONDS", "30"))