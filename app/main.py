
import time

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.catalog import router as catalog_router
from app.api.inventory import router as inventory_router
from app.api.orders import router as orders_router
from app.database import get_db
from app.metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS

app = FastAPI(
    title="FulfillOps API",
    description="Resilient Order Processing Platform",
    version="1.0.0",
)


# Register all API routers
app.include_router(catalog_router)
app.include_router(inventory_router)
app.include_router(orders_router)


# Monitor HTTP requests
@app.middleware("http")
async def monitor_http_requests(request: Request, call_next):
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        elapsed = time.perf_counter() - start_time
        route = request.scope.get("route")
        route_name = getattr(route, "path", "unmatched")

        HTTP_REQUESTS.labels(
            request.method, route_name, "500"
        ).inc()

        HTTP_REQUEST_DURATION.labels(
            request.method, route_name
        ).observe(elapsed)

        raise

    elapsed = time.perf_counter() - start_time
    route = request.scope.get("route")
    route_name = getattr(route, "path", "unmatched")

    HTTP_REQUESTS.labels(
        request.method,
        route_name,
        str(response.status_code),
    ).inc()

    HTTP_REQUEST_DURATION.labels(
        request.method,
        route_name,
    ).observe(elapsed)

    return response


@app.get("/")
def root():
    return {
        "message": "Welcome to FulfillOps",
        "status": "running",
    }


@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        revision = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()

        if revision is None:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready"},
            )

        return {"status": "ready"}

    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready"},
        )


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(
        content=generate_latest(),
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )
