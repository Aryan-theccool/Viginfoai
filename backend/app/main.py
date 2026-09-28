"""VigInfo AI — FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, SessionLocal, engine
from .routers import audit, findings, ingestion, records, reviews, stats

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.AUTO_SEED:
        from .data.seed import seed_demo_data

        db = SessionLocal()
        try:
            n = seed_demo_data(db)
            if n:
                print(f"[viginfo] seeded {n} demo records")
        finally:
            db.close()
    yield


app = FastAPI(
    title="VigInfo AI",
    description="System of record for MDR clinical evidence & post-market surveillance (EU MDR 2017/745).",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion.router, prefix="/api")
app.include_router(records.router, prefix="/api")
app.include_router(findings.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/api/health")
def health():
    from .services.ai_engine import current_engine_version

    return {"status": "ok", "engine": current_engine_version()}


@app.get("/")
def root():
    return {"app": "VigInfo AI", "docs": "/docs", "health": "/api/health"}
