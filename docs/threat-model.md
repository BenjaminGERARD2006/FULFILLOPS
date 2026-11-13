# FulfillOps Threat Model

**Review date:** 14 November 2026  
**Scope:** FulfillOps API, PostgreSQL database, background worker, Docker Compose, Kubernetes and CI pipeline.

## 1. System and assets

FulfillOps accepts customer orders, reserves inventory, records idempotency information and processes accepted orders asynchronously.

The principal assets are:

- Product catalog, prices and inventory quantities.
- Orders, order items and customer references.
- Idempotency records used to prevent duplicate orders.
- Durable worker jobs, attempts, leases and failure information.
- Database credentials, Kubernetes Secrets and CI credentials.
- Application images, dependencies, build artifacts and SBOM reports.
- Application availability, logs and operational metrics.

## 2. Trust boundaries

1. **Client to API:** HTTP requests enter the FastAPI application. Request validation and error handling are required at this boundary.
2. **API and worker to PostgreSQL:** Both services share the database. Transactions and database constraints protect business state.
3. **Worker execution:** The worker claims durable jobs and may retry work after failures or lease expiry.
4. **CI and container registry:** Source code, dependencies and images pass through the build and delivery pipeline.
5. **Kubernetes control plane:** Deployments, Secrets, Services and persistent storage control the deployed environment.

## 3. Threats, controls and residual risks

| ID | Threat | Controls and evidence | Residual risk |
|---|---|---|---|
| T1 | Malformed requests or invalid quantities cause incorrect orders. | API validation rejects missing idempotency keys and invalid quantities. Public checker passed these cases. | Rate limiting and authentication controls are not demonstrated by the current evidence. |
| T2 | Concurrent requests oversell inventory. | Transactional inventory reservation and concurrency checks. Public checker passed atomic reservation tests. | Database contention and availability remain operational risks. |
| T3 | Replayed requests create duplicate orders or reserve stock twice. | Durable idempotency records and conflict detection. Public checker passed retry, conflict and eight-request same-key tests. | Cross-replica behavior should remain part of regression testing. |
| T4 | A worker crash or retry processes the same business effect more than once. | Durable jobs, leases, retry handling and dead-letter state are implemented. Retry and lease-recovery scenarios were exercised. | A real process kill during an in-flight committed job has not been conclusively demonstrated. |
| T5 | Database credentials are exposed through source control or logs. | Local environment variables and Kubernetes Secret references are used. `.env` and credentials must remain outside Git and logs. | Secret rotation and automated secret scanning need continued verification. |
| T6 | Database data is lost during container replacement. | PostgreSQL uses persistent Docker/Kubernetes storage. An isolated test order remained completed after database, API and worker restarts. | Backup, restore and disaster-recovery procedures have not been demonstrated. |
| T7 | Vulnerable dependencies or container images enter a release. | CI includes dependency/image security scanning and SBOM generation. | The reviewed scan configuration was report-only; an enforced blocking vulnerability policy is still required. |
| T8 | Compromised or misconfigured containers gain excessive privileges. | Container and Kubernetes configuration are reviewed as part of delivery. | The current Dockerfile is single-stage and does not define a non-root runtime user. API and worker resource requests and limits also need to be added. |
| T9 | Sensitive information is exposed through metrics or logs. | Operational metrics are exposed for monitoring. Customer identifiers and idempotency keys should not be used as metric labels. | Logging and metric-label policies need continuing review. |
| T10 | A broken deployment makes the API unavailable. | Kubernetes readiness/liveness probes and a Git-based recovery were exercised. A deliberately broken readiness probe was detected and reverted. | The observed rolling-update probe recorded two transient HTTP 502 responses; uninterrupted availability is not claimed. |

## 4. Security assumptions

- PostgreSQL is the authoritative store for orders, inventory and durable jobs.
- API and worker instances use the same database state.
- The test environment is isolated from development data.
- Secrets are supplied through environment configuration or Kubernetes Secret references and are not committed to Git.
- Production-grade authentication, TLS termination, backups and disaster recovery must be configured where the deployment environment requires them.

## 5. Priorities for risk reduction

1. Add an enforced CI security policy with a documented severity threshold.
2. Use a multi-stage container build and a non-root application user.
3. Add CPU and memory requests and limits to API and worker Deployments.
4. Demonstrate recovery after killing a worker during actual in-flight processing.
5. Demonstrate backup restoration and review API exposure, authentication and TLS requirements.

## 6. Limitations

This threat model describes the current project and its available evidence. A passing public API checker does not prove that every security control is implemented. Items described as residual risks or not demonstrated must not be presented as completed controls.
