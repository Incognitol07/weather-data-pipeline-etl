# app/routers/analytics.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, between
from datetime import datetime, timedelta, date
from pydantic import BaseModel
from typing import List, Optional

from app.core.database import get_db
from app.models import WeatherData, WeatherForecast, Location
from app.utils import logger

analytics_router = APIRouter(prefix="/analytics")

# Pydantic response models
class TemperatureTrend(BaseModel):
    date: date
    avg_temp: float
    max_temp: float
    min_temp: float

class Precipitation(BaseModel):
    total_rain: float
    total_snow: float

class WindAnalysis(BaseModel):
    avg_wind: Optional[float]
    max_wind: Optional[float]

class HistoricalResponse(BaseModel):
    temperature_trends: List[TemperatureTrend]
    precipitation: Precipitation
    wind_analysis: WindAnalysis

class ForecastItem(BaseModel):
    data_calculation_time: datetime
    temperature: float
    rain: Optional[float] = 0
    snow: Optional[float] = 0
    wind_speed: Optional[float]
    weather_main: str

class ForecastResponse(BaseModel):
    upcoming_temperatures: List[float]
    precipitation_probability: float
    wind_alerts: List[ForecastItem]
    storm_warnings: List[ForecastItem]

class StatisticsResponse(BaseModel):
    avg_temp: Optional[float]
    max_temp: Optional[float]
    min_temp: Optional[float]
    avg_humidity: Optional[float]
    total_rain: float
    total_snow: float

class Alert(BaseModel):
    date: str
    weather_main: str
    description: str
    temperature: float
    rain: float
    snow: float

class WeatherTrendsResponse(BaseModel):
    historical: HistoricalResponse
    forecast: ForecastResponse
    statistics: StatisticsResponse
    alerts: List[Alert]

@analytics_router.get(
    "/weather-trends",
    response_model=WeatherTrendsResponse,
    summary="Get weather trends and analytics",
    description="Return historical trends, short-term forecasts, and key statistics for a location."
)
async def get_weather_trends(
    lat: float,
    lon: float,
    days: int = Query(7, gt=0, le=30),
    db: AsyncSession = Depends(get_db)
) -> WeatherTrendsResponse:
    try:
        # Resolve location
        result = await db.execute(select(Location).where(Location.lat == lat, Location.lon == lon))
        location = result.scalar_one_or_none()
        if not location:
            raise HTTPException(404, detail="Location not found")

        now = datetime.now()
        start_date = now - timedelta(days=days)
        forecast_start = now + timedelta(hours=1)

        historical = await get_historical_analysis(location.id, start_date, now, db)
        forecast = await get_forecast_analysis(location.id, forecast_start, db)
        statistics = await get_statistical_aggregates(location.id, start_date, db)
        alerts = await get_weather_alerts(location.id, db)

        return WeatherTrendsResponse(
            historical=historical,
            forecast=forecast,
            statistics=statistics,
            alerts=alerts
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(500, detail="Error generating analytics")

# Internal helpers
async def get_historical_analysis(
    city_id: int, start: datetime, end: datetime, db: AsyncSession
) -> HistoricalResponse:
    temp_q = select(
        func.date(WeatherData.data_calculation_time).label("date"),
        func.avg(WeatherData.temperature).label("avg_temp"),
        func.max(WeatherData.temperature).label("max_temp"),
        func.min(WeatherData.temperature).label("min_temp")
    ).where(
        WeatherData.city_id == city_id,
        between(WeatherData.data_calculation_time, start, end)
    ).group_by("date")

    rain_q = select(
        func.coalesce(func.sum(WeatherData.rain), 0).label("total_rain"),
        func.coalesce(func.sum(WeatherData.snow), 0).label("total_snow")
    ).where(
        WeatherData.city_id == city_id,
        between(WeatherData.data_calculation_time, start, end)
    )

    wind_q = select(
        func.avg(WeatherData.wind_speed).label("avg_wind"),
        func.max(WeatherData.wind_speed).label("max_wind")
    ).where(
        WeatherData.city_id == city_id,
        between(WeatherData.data_calculation_time, start, end)
    )

    temp_rows = (await db.execute(temp_q)).all()
    rain_row = (await db.execute(rain_q)).first()
    wind_row = (await db.execute(wind_q)).first()

    trends: List[TemperatureTrend] = []
    for r in temp_rows:
        # r.date is a string in 'YYYY-MM-DD' format
        trends.append(TemperatureTrend(
            date=r.date,
            avg_temp=r.avg_temp,
            max_temp=r.max_temp,
            min_temp=r.min_temp
        ))

    precipitation = Precipitation(
        total_rain=rain_row.total_rain,
        total_snow=rain_row.total_snow
    )

    wind_analysis = WindAnalysis(
        avg_wind=wind_row.avg_wind,
        max_wind=wind_row.max_wind
    )

    return HistoricalResponse(
        temperature_trends=trends,
        precipitation=precipitation,
        wind_analysis=wind_analysis
    )

async def get_forecast_analysis(
    city_id: int, start: datetime, db: AsyncSession
) -> ForecastResponse:
    q = select(
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

    rows = (await db.execute(q)).all()
    temps = [r.temperature for r in rows]
    total = len(rows)
    precip_count = sum(1 for r in rows if (r.rain or 0) > 0 or (r.snow or 0) > 0)
    precip_pct = (precip_count / total * 100) if total else 0.0

    wind_alerts: List[ForecastItem] = []
    storm_warnings: List[ForecastItem] = []
    for r in rows:
        item = ForecastItem(
            data_calculation_time=r.data_calculation_time,
            temperature=r.temperature,
            rain=r.rain or 0,
            snow=r.snow or 0,
            wind_speed=r.wind_speed,
            weather_main=r.weather_main
        )
        if (r.wind_speed or 0) > 15:
            wind_alerts.append(item)
        if r.weather_main in ["Thunderstorm", "Hurricane"]:
            storm_warnings.append(item)

    return ForecastResponse(
        upcoming_temperatures=temps,
        precipitation_probability=precip_pct,
        wind_alerts=wind_alerts,
        storm_warnings=storm_warnings
    )

async def get_statistical_aggregates(
    city_id: int, start: datetime, db: AsyncSession
) -> StatisticsResponse:
    q = select(
        func.avg(WeatherData.temperature).label("avg_temp"),
        func.max(WeatherData.temperature).label("max_temp"),
        func.min(WeatherData.temperature).label("min_temp"),
        func.avg(WeatherData.humidity).label("avg_humidity"),
        func.coalesce(func.sum(WeatherData.rain), 0).label("total_rain"),
        func.coalesce(func.sum(WeatherData.snow), 0).label("total_snow")
    ).where(
        WeatherData.city_id == city_id,
        WeatherData.data_calculation_time >= start
    )
    row = (await db.execute(q)).first()

    return StatisticsResponse(
        avg_temp=row.avg_temp,
        max_temp=row.max_temp,
        min_temp=row.min_temp,
        avg_humidity=row.avg_humidity,
        total_rain=row.total_rain,
        total_snow=row.total_snow
    )

async def get_weather_alerts(city_id: int, db: AsyncSession) -> List[Alert]:
    cutoff = datetime.now() - timedelta(hours=24)
    q = select(WeatherData).where(
        WeatherData.city_id == city_id,
        WeatherData.data_calculation_time >= cutoff,
        WeatherData.weather_main.in_(["Thunderstorm", "Tornado", "Hurricane"])
    )
    rows = (await db.execute(q)).scalars().all()
    alerts: List[Alert] = []
    for wd in rows:
        alerts.append(Alert(
            date=wd.data_calculation_time.isoformat(),
            weather_main=wd.weather_main,
            description=wd.description,
            temperature=wd.temperature,
            rain=wd.rain or 0,
            snow=wd.snow or 0
        ))
    return alerts