# FulfillOps Incident Postmortem

## Incident: Deliberately broken API release

### Summary
A deliberately incorrect readiness endpoint was committed to the API Kubernetes Deployment to test release detection and GitOps recovery.

### Root cause
The readiness probe was changed from `/health/ready` to `/health/intentional-failure`. The FastAPI application does not expose this route, so Kubernetes received HTTP 404.

### Detection
Kubernetes recorded:
- Pod: `fulfillops-api-5f67548545-6c9sg`
- Warning: `Unhealthy`
- Reason: readiness probe failed
- HTTP response: 404

The failed Pod was removed from its ReplicaSet.

### Recovery
The faulty Git commit was:
`00ea3ad test: simulate broken API readiness release`

Recovery was performed using:
`dcef30c Revert "test: simulate broken API readiness release"`

Argo CD reconciled the restored Git revision. Final Application state was `Synced` and `Healthy`. The API and worker deployments were subsequently confirmed at two ready replicas each.

### Lessons and prevention
- Readiness probes must reference real application endpoints.
- A new release must pass readiness checks before replacing existing healthy replicas.
- Keep `maxUnavailable: 0` and `maxSurge: 1` for the API rolling-update strategy.
- Use Git revert and Argo CD reconciliation to restore a known-good revision.

### Limitations
The failed release was detected and recovered. Continuous request success throughout this deliberately broken release was not independently measured. No claim of zero user-visible impact is made.
