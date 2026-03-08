import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import get_settings
from app.db.session import engine, Base
from app.db.redis import redis_client
from app.api.routes import drugs, patients, prescription, reports, chat
from fastapi.staticfiles import StaticFiles
from pathlib import Path

settings = get_settings()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer() if settings.APP_DEBUG else structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("starting_medguard", env=settings.APP_ENV)

    # Create tables + enable pg_trgm extension
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_ready")

    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("redis_ready")
    except Exception as e:
        logger.warning("redis_not_available", error=str(e))

    yield

    # Shutdown
    await engine.dispose()
    await redis_client.aclose()
    logger.info("medguard_shutdown")


app = FastAPI(
    title="MedGuard API",
    description="Medicine Allergy Detection System — checks prescribed drugs against patient allergy profiles",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(drugs.router)
app.include_router(patients.router)
app.include_router(prescription.router)
app.include_router(reports.router)
app.include_router(chat.router)

# Serve uploaded files
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "medguard"}


@app.get("/health/ready")
async def health_ready():
    checks = {}

    # DB check
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Redis check
    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ready" if all_ok else "degraded", "checks": checks}