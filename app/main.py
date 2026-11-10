
from fastapi import FastAPI

app = FastAPI(
    title="FulfillOps API",
    description="Resilient Order Processing Platform",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "Welcome to FulfillOps",
        "status": "running",
    }


@app.get("/health/live")
def health_live():
    return {
        "status": "alive"
    }
