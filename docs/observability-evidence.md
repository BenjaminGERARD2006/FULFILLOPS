# FulfillOps Observability and Performance Evidence

## Prometheus
Prometheus successfully discovered and scraped four application targets:
- Two API replicas on port 8000.
- Two worker replicas on port 9101.

All four targets reported UP.

Metrics include:
- `fulfillops_orders_created_total`
- `fulfillops_orders_failed_total`
- `fulfillops_worker_retries_total`
- `fulfillops_http_requests_total`
- `fulfillops_http_request_duration_seconds`

## HTTP performance measurement
Test location: dedicated local Kind Kubernetes cluster, from a worker Pod to the API Service.

- Samples: 200
- Successful responses: 200
- Failed responses: 0
- Success rate: 100%
- Observed p95 latency: 9.236 ms
- Endpoint: GET /api/v1/catalog

Raw evidence: `docs/http_samples.csv`
Measurement script: `docs/http_sample_200.py`

## Rolling-update availability measurement
The professor-supplied probe was run for approximately 30 seconds during an API rollout.

Latest diagnostic attempt:
- Samples: 121
- Duration: approximately 30.02 seconds
- Failed requests: 2
- Failed responses: HTTP 502
- Diagnostic log: upstream connection timeout
- A new API ReplicaSet was created during the measurement window.
- Final API Deployment recovered to two ready replicas.
- Argo CD returned to Synced and Healthy.

This result demonstrates the rollout and identifies a brief availability degradation. It does not demonstrate zero-failure availability.

## Illustrative SLO targets
- Availability target: 99.5% successful requests over the defined evaluation window.
- Latency target: p95 below 300 ms.

The 200-request test achieved 100% success and 9.236 ms p95 in this local environment. This small local test is not a production SLO guarantee.

## Limitations
Kind runs locally on one machine. Results do not represent production networking, distributed infrastructure, realistic user traffic or long-term availability.
