# app/background_tasks/jobs/fetch_current_weather.py
import asyncio
from sqlalchemy import select
from app.utils import logger
from app.models import Location, WeatherData
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.helpers.fetch_data import fetch_data_from_api
from app.core.database import AsyncSessionLocal

async def fetch_current_weather_job():
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Starting async current weather job...")
            result = await db.execute(select(Location))
            locations = result.scalars().all()
            
            tasks = []
            for location in locations:
                tasks.append(fetch_location_weather(db, location))
            
            await asyncio.gather(*tasks)
            await db.commit()
            logger.info("Current weather data updated for all locations.")

        except Exception as e:
            await db.rollback()
            logger.error(f"Current weather job failed: {str(e)}")
            raise

async def fetch_location_weather(db: AsyncSession, location: Location):
    params = {"lat": location.lat, "lon": location.lon}
    try:
        weather_data = await fetch_data_from_api(
            "https://api.openweathermap.org/data/2.5/weather", 
            params
        )
        
        current_weather = WeatherData(
            weather_main=weather_data["weather"][0]["main"],
            description=weather_data["weather"][0]["description"],
            data_calculation_time=datetime.fromtimestamp(weather_data["dt"]),
            temperature=weather_data["main"]["temp"] - 273.15,
            feels_like=weather_data["main"]["feels_like"] - 273.15,
            min_temperature=weather_data["main"]["temp_min"] - 273.15,
            max_temperature=weather_data["main"]["temp_max"] - 273.15,
            pressure=weather_data["main"]["pressure"],
            humidity=weather_data["main"]["humidity"],
            sea_level=weather_data["main"].get("sea_level"),
            ground_level=weather_data["main"].get("grnd_level"),
            weather_degrees=weather_data["wind"]["deg"],
            wind_speed=weather_data["wind"]["speed"],
            wind_gust=weather_data["wind"].get("gust"),
            rain=weather_data.get("rain", {}).get("1h"),
            snow=weather_data.get("snow", {}).get("1h"),
            cloudiness=weather_data["clouds"]["all"],
            visibility=weather_data.get("visibility"),
            sunrise_time=datetime.fromtimestamp(weather_data["sys"]["sunrise"]),
            sunset_time=datetime.fromtimestamp(weather_data["sys"]["sunset"]),
            city_id=location.id
        )
        db.add(current_weather)
        logger.info(f"Weather data collected for {location.name}")

    except Exception as e:
        logger.error(f"Failed to fetch weather for {location.name}: {str(e)}")
        raise