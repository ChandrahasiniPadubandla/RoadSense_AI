from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.connection import get_db


app = FastAPI(
    title="AI-Based Smart Traffic & Accident Prediction System",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "Smart Traffic API is running"
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):

    result = db.execute(
        text("SELECT 1")
    )

    return {
        "status": "healthy",
        "database": "connected",
        "result": result.scalar()
    }