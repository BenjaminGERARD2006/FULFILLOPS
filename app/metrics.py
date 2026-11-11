
from prometheus_client import Counter, Histogram

# Business metrics
ORDERS_CREATED = Counter(
    "fulfillops_orders_created",
    "Total number of orders accepted by the API",
)

ORDERS_FAILED = Counter(
    "fulfillops_orders_failed",
    "Total number of orders that ultimately failed",
)

WORKER_RETRIES = Counter(
    "fulfillops_worker_retries",
    "Total number of worker retry attempts",
)

# HTTP metrics. Labels use route templates, never customer IDs
# or idempotency keys.
HTTP_REQUESTS = Counter(
    "fulfillops_http_requests",
    "Total number of HTTP requests",
    ["method", "route", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "fulfillops_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
)
