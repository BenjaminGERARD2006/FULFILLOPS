# Docker Compose Persistence Evidence

Date: 14 November 2026

## Test environment
- Database: fulfillops_test
- PostgreSQL: 16
- Dedicated Docker volume: fulfillops_test_postgres_data
- API endpoint: http://localhost:8001
- Separate worker service: fulfillops-worker-1

## Test procedure
1. Created and completed an order through the public API checker.
2. Recorded the order ID: 41ce2576-2367-4e42-be76-0dd3efacd108.
3. Restarted the PostgreSQL test container without deleting its volume.
4. Queried PostgreSQL and confirmed the same order remained completed.
5. Restarted the API and worker containers.
6. Checked the API readiness endpoint.
7. Retrieved the same order through the API.

## Results
- PostgreSQL after restart: order still present, status completed.
- API readiness after restart: ready.
- API order retrieval: successful.
- Order ID: 41ce2576-2367-4e42-be76-0dd3efacd108.
- Order status: completed.
- Total: 996 cents (EUR 9.96).

## Conclusion
The committed order survived a PostgreSQL container restart and remained accessible through the API after restarting the API and worker services. The test used a dedicated test database volume; no volume deletion was performed.
