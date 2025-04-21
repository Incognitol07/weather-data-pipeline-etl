# app/routers/weather.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models import WeatherData, WeatherForecast, Location
from app.utils import logger

weather_router = APIRouter(prefix="/weather")

@weather_router.get("/current")
async def get_current_weather(
    lat: float,
    lon: float,
    db: AsyncSession = Depends(get_db)
):
    try:
        recent_time = datetime.now() - timedelta(hours=1)
        
        result = await db.execute(
            select(WeatherData)
            .join(Location)
            .where(
                Location.lat == lat,
                Location.lon == lon,
                WeatherData.data_calculation_time >= recent_time
            )
        )
        current_weather = result.scalars().all()
        
        if current_weather:
            logger.info("Returning cached current weather data")
            return current_weather
            
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No recent weather data available")
        
    except Exception as e:
        logger.error(f"Weather fetch error: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching weather data")

@weather_router.get("/forecast")
async def get_weather_forecast(
    lat: float,
    lon: float,
    db: AsyncSession = Depends(get_db)
):
    try:
        recent_time = datetime.now() - timedelta(hours=6)
        
        result = await db.execute(
            select(WeatherForecast)
            .join(Location)
            .where(
                Location.lat == lat,
                Location.lon == lon,
                WeatherForecast.data_calculation_time >= recent_time
            )
        )
        forecasts = result.scalars().all()
        
        if forecasts:
            logger.info("Returning cached forecast data")
            return forecasts
            
        raise HTTPException(404, detail="No recent forecast data available")
        
    except Exception as e:
        logger.error(f"Forecast fetch error: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching forecast data")