# app/routers/automation.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.background_tasks.jobs import fetch_current_weather_job, fetch_forecast_job

trigger_router = APIRouter(prefix="/trigger")

@trigger_router.post("/weather-forecast", status_code=202)
async def trigger_forecast_fetch(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        background_tasks.add_task(fetch_forecast_job, db)
        return {"message": "Forecast fetch job queued successfully"}
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@trigger_router.post("/current-weather", status_code=202)
async def trigger_current_fetch(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        background_tasks.add_task(fetch_current_weather_job, db)
        return {"message": "Current weather fetch job queued successfully"}
    except Exception as e:
        raise HTTPException(500, detail=str(e))