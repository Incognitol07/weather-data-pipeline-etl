# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.background_tasks.jobs.fetch_current_weather import fetch_current_weather_job
from app.background_tasks.jobs.fetch_weather_forecast import fetch_forecast_job
from app.core.database import Base, engine
from app.core.config import settings
from app.routers import weather_router, geocode_router, trigger_router
from app.utils.logging_config import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database setup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Scheduler setup
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        fetch_current_weather_job,
        'interval',
        hours=settings.CURRENT_WEATHER_INTERVAL_HOURS,
        misfire_grace_time=300
    )
    scheduler.add_job(
        fetch_forecast_job,
        'interval',
        hours=settings.FORECAST_INTERVAL_HOURS,
        misfire_grace_time=300
    )
    scheduler.start()
    
    logger.info("Application startup complete")
    yield
    scheduler.shutdown()
    logger.info("Application shutdown complete")

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(weather_router)
app.include_router(geocode_router)
app.include_router(trigger_router)

@app.get("/")
async def health_check():
    return {"status": "healthy"}