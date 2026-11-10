
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db


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


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "ready",
            "database": "connected",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )
