# FulfillOps Assistance and Contribution Log

**Project:** FulfillOps  
**Disclosure date:** 14 November 2026

## 1. AI assistance disclosure

ChatGPT was used as an AI assistance tool during project development and final verification.

The assistance included:

- Explaining Docker Compose configuration and helping diagnose the shared PostgreSQL volume configuration.
- Suggesting a separate persistent volume for the isolated test database.
- Preparing and explaining PowerShell commands for database migration, seeding, service startup and health checks.
- Helping identify the correct API port for the public checker.
- Organising and drafting evidence documentation for the public checker and persistence tests.
- Reviewing the submission checklist and identifying missing documentation and technical hardening items.

AI-generated commands and documentation wording were reviewed and executed or adapted by the student. ChatGPT did not independently operate the student's local Docker environment, execute the public checker on the student's machine, or push commits to GitHub.

## 2. Verification performed by the student

The student executed the commands and inspected the outputs in the local project environment.

The following results were observed:

- Official public API checker: 15 passed, 0 failed, 0 skipped, using the isolated `fulfillops_test` database.
- PostgreSQL restart: a previously completed order remained in the database.
- API and worker restart: the API became ready and returned the same completed order.
- Git commits and pushes: performed from the student's local PowerShell terminal.

Supporting evidence is stored in:

- `docs/public-checker-evidence.md`
- `docs/persistence-evidence.md`
- `docs/observability-evidence.md`
- `docs/incident-postmortem.md`

### Student's confirmed individual contribution

My individual contribution to FulfillOps was primarily focused on the backend and database implementation as Student 1.

I worked on the FastAPI backend, including the catalog, inventory and order endpoints, as well as health checks and Prometheus metrics. I contributed to the SQLAlchemy database models for products, inventory, orders, order items, idempotency records and durable jobs, together with the PostgreSQL schema and Alembic migrations.

A major part of my work was the order-processing transaction. I implemented the backend logic for validating orders, aggregating duplicate SKU lines, calculating order totals, checking inventory availability and reserving stock atomically. I also worked on idempotency handling to ensure that repeated requests with the same key do not create duplicate orders or reserve inventory twice. The order, inventory changes, idempotency record and durable job are persisted together in a database transaction.

I also worked on database seeding and backend testing, including API validation, order processing, inventory reservation, idempotency and concurrency scenarios.

During final integration and verification, I personally configured and checked an isolated Docker Compose test environment with a separate PostgreSQL volume. I ran the official public API checker with both concurrency and stress options, obtaining **15 passed, 0 failed and 0 skipped**. I also performed a persistence test by restarting PostgreSQL, the API and worker services, then verified that an existing completed order remained accessible through the API.

I prepared and committed supporting evidence for these tests, including the public checker results and persistence verification.

My work was primarily focused on the backend and its verification. Worker implementation, platform engineering, CI/CD and Kubernetes responsibilities were shared or assigned to other team members, and I do not claim ownership of work that I did not personally implement.

## 4. Responsibility and review

The student remains responsible for understanding, checking and being able to explain submitted code, architecture decisions, test results and documentation. AI-generated suggestions should be treated as assistance, not as proof that a requirement has been satisfied.
