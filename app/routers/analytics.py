# app/routers/analytics.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, between
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models import WeatherData, WeatherForecast, Location
from app.utils import logger
from typing import Optional

analytics_router = APIRouter(prefix="/analytics")

@analytics_router.get("/weather-trends")
async def get_weather_trends(
    lat: float,
    lon: float,
    days: int = Query(7, gt=0, le=30),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive weather trends and analytics for a location
    Returns:
    - Historical trends
    - Forecast predictions
    - Significant weather events
    - Statistical aggregates
    """
    try:
        # Get location
        location = await get_location(lat, lon, db)
        
        # Date ranges
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        forecast_start = end_date + timedelta(hours=1)

        return {
            "historical": await get_historical_analysis(location.id, start_date, end_date, db),
            "forecast": await get_forecast_analysis(location.id, forecast_start, db),
            "statistics": await get_statistical_aggregates(location.id, start_date, db),
            "alerts": await get_weather_alerts(location.id, db)
        }

    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        raise HTTPException(500, detail="Error generating analytics")

async def get_location(lat: float, lon: float, db: AsyncSession):
    result = await db.execute(
        select(Location)
        .where(Location.lat == lat, Location.lon == lon)
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(404, detail="Location not found")
    return location

async def get_historical_analysis(city_id: int, start: datetime, end: datetime, db: AsyncSession):
    # Temperature trends
    temp_query = select(
        func.date(WeatherData.data_calculation_time).label("date"),
        func.avg(WeatherData.temperature).label("avg_temp"),
        func.max(WeatherData.temperature).label("max_temp"),
        func.min(WeatherData.temperature).label("min_temp")
    ).where(
        WeatherData.city_id == city_id,
        between(WeatherData.data_calculation_time, start, end)
    ).group_by("date")

    # Precipitation analysis
    rain_query = select(
        func.sum(WeatherData.rain).label("total_rain"),
        func.sum(WeatherData.snow).label("total_snow")
    ).where(
        WeatherData.city_id == city_id,
        between(WeatherData.data_calculation_time, start, end)
    )

    # Wind analysis
    wind_query = select(
        func.avg(WeatherData.wind_speed).label("avg_wind"),
        func.max(WeatherData.wind_speed).label("max_wind")
    ).where(
        WeatherData.city_id == city_id,
        between(WeatherData.data_calculation_time, start, end)
    )

    temp_result = await db.execute(temp_query)
    rain_result = await db.execute(rain_query)
    wind_result = await db.execute(wind_query)

    return {
        "temperature_trends": temp_result.all(),
        "precipitation": rain_result.first(),
        "wind_analysis": wind_result.first()
    }

async def get_forecast_analysis(city_id: int, start: datetime, db: AsyncSession):
    forecast_query = select(
        WeatherForecast.data_calculation_time,
        WeatherForecast.temperature,
        WeatherForecast.rain,
        WeatherForecast.snow,
        WeatherForecast.wind_speed,
        WeatherForecast.weather_main
    ).where(
        WeatherForecast.city_id == city_id,
        WeatherForecast.data_calculation_time >= start
    ).order_by(WeatherForecast.data_calculation_time)

    result = await db.execute(forecast_query)
    forecasts = result.all()

    return {
        "upcoming_temperatures": [f.temperature for f in forecasts],
        "precipitation_probability": analyze_precipitation(forecasts),
        "wind_alerts": [f for f in forecasts if f.wind_speed > 15],  # 15 m/s threshold
        "storm_warnings": [f for f in forecasts if f.weather_main in ["Thunderstorm", "Hurricane"]]
    }

async def get_statistical_aggregates(city_id: int, start: datetime, db: AsyncSession):
    query = select(
        func.avg(WeatherData.temperature).label("avg_temp"),
        func.max(WeatherData.temperature).label("max_temp"),
        func.min(WeatherData.temperature).label("min_temp"),
        func.avg(WeatherData.humidity).label("avg_humidity"),
        func.sum(WeatherData.rain).label("total_rain"),
        func.sum(WeatherData.snow).label("total_snow")
    ).where(
        WeatherData.city_id == city_id,
        WeatherData.data_calculation_time >= start
    )

    result = await db.execute(query)
    return result.first()

async def get_weather_alerts(city_id: int, db: AsyncSession):
    alert_query = select(WeatherData).where(
        WeatherData.city_id == city_id,
        WeatherData.data_calculation_time >= datetime.now() - timedelta(hours=24),
        WeatherData.weather_main.in_(["Thunderstorm", "Tornado", "Hurricane"])
    )

    result = await db.execute(alert_query)
    return result.scalars().all()

def analyze_precipitation(forecasts):
    return sum(1 for f in forecasts if f.rain > 0 or f.snow > 0) / len(forecasts) * 100