# app/background_tasks/jobs/fetch_weather_forecast.py
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.utils import logger
from app.models import Location, WeatherForecast
from app.utils.helpers.fetch_data import fetch_data_from_api
from app.core.database import AsyncSessionLocal

async def fetch_forecast_job():
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Starting async forecast job...")
            result = await db.execute(select(Location))
            locations = result.scalars().all()
            
            tasks = []
            for location in locations:
                tasks.append(process_location_forecast(db, location))
            
            await asyncio.gather(*tasks)
            await db.commit()
            logger.info("Forecast data updated for all locations.")

        except Exception as e:
            await db.rollback()
            logger.error(f"Forecast job failed: {str(e)}")
            raise

async def process_location_forecast(db: AsyncSession, location: Location):
    params = {"lat": location.lat, "lon": location.lon}
    weather_data = await fetch_data_from_api(
        "https://api.openweathermap.org/data/2.5/forecast", 
        params
    )
    
    forecast_tasks = []
    for entry in weather_data["list"]:
        forecast_tasks.append(create_forecast_entry(db, location, entry, weather_data['city']))
    
    await asyncio.gather(*forecast_tasks)
    logger.info(f"Forecast processed for {location.name}")

async def create_forecast_entry(db: AsyncSession, location: Location, entry: dict, city:dict):
    forecast = WeatherForecast(
        weather_main=entry["weather"][0]["main"],
        description=entry["weather"][0]["description"],
        data_calculation_time=datetime.fromtimestamp(entry["dt"]),
        temperature=round(entry["main"]["temp"] - 273.15, 2),
        feels_like=round(entry["main"]["feels_like"] - 273.15, 2),
        min_temperature=round(entry["main"]["temp_min"] - 273.15, 2),
        max_temperature=round(entry["main"]["temp_max"] - 273.15, 2),
        pressure=entry["main"]["pressure"],
        humidity=entry["main"]["humidity"],
        sea_level=entry["main"].get("sea_level"),
        ground_level=entry["main"].get("grnd_level"),
        weather_degrees=entry["wind"]["deg"],
        wind_speed=entry["wind"]["speed"],
        wind_gust=entry["wind"].get("gust"),
        rain=entry.get("rain", {}).get("3h"),
        snow=entry.get("snow", {}).get("3h"),
        cloudiness=entry["clouds"]["all"],
        visibility=entry.get("visibility"),
        part_of_day=entry["sys"]["pod"],
        sunrise_time=datetime.fromtimestamp(city["sunrise"]),
        sunset_time=datetime.fromtimestamp(city["sunset"]),
        city_id=location.id
    )
    db.add(forecast)