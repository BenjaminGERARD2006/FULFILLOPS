# Public API Checker Evidence

Date: 14 November 2026

## Environment
- Database: fulfillops_test
- PostgreSQL: 16
- Dedicated volume: fulfillops_test_postgres_data
- API: http://localhost:8001
- Worker: separate Docker Compose service
- Checker: official fulfillops_public_checker.py

## Command
py "$checkDir\fulfillops_public_checker.py" --base-url http://localhost:8001 --concurrency --stress

## Results
- PASS Liveness endpoint
- PASS Readiness endpoint
- PASS Catalog and fixed prices
- PASS Unknown order returns 404
- PASS Missing Idempotency-Key returns 400
- PASS Invalid item quantity returns 422
- PASS Inventory reading
- PASS Create order and idempotent retry
- PASS Conflicting idempotency payload rejected
- PASS Asynchronous worker eventually completes
- PASS Inventory reduced exactly once
- PASS Prometheus metrics exposed
- PASS Concurrent inventory reservations are atomic
- PASS Eight concurrent identical-key requests reserve once
- PASS Duplicate SKU lines aggregate and bill correctly

## Final result
15 passed / 0 failed / 0 skipped

Tests ran against an isolated test database.
