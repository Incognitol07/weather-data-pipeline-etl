# app/routers/geocode.py

from fastapi import (
    HTTPException,
    Query,
    APIRouter,
    status,
    Depends
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import select
from app.models import Location
from app.utils import logger, fetch_data_from_api
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

geocode_router = APIRouter(prefix="/geocoding")

# Direct Geocoding Endpoint
@geocode_router.get("/direct")
async def get_geographical_coordinates(
    city_name: str,
    state_code: str = None,
    country_code: str = None,
    limit: int = Query(5, le=5),
    db: AsyncSession = Depends(get_db)
):
    """
    Get geographical coordinates by city name, state code, and country code.
    """
    try:
        result = await db.execute(select(Location).filter(Location.name == city_name))
        location = result.scalar_one_or_none()
        
        if location:
            logger.info(f"Returned location {city_name} from database")
            return location
        
        q = city_name
        if state_code:
            q += f",{state_code}"
        if country_code:
            q += f",{country_code}"

        params = {
            "q": q,
            "limit": limit
        }
        data = await fetch_data_from_api("http://api.openweathermap.org/geo/1.0/direct", params)
        new_location = Location(
            name = data[0]["name"],
            lat = data[0]["lat"],
            lon = data[0]["lon"],
            country = data[0]["country"],
            state = data[0].get("state")
        )
        db.add(new_location)
        await db.commit()
        await db.refresh(new_location)
        logger.info(f"Fetched location {city_name} from external api")
        return new_location
    except SQLAlchemyError as e:
        logger.error(f"Unexpected error occurred during API call: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An error occurred. Please try connecting to the internet"
            )


# Reverse Geocoding Endpoint
@geocode_router.get("/reverse")
async def get_location_by_coordinates(
    lat: float, 
    lon: float,
    db: AsyncSession = Depends(get_db)
    ):
    
    """
    Get location details by geographical coordinates.
    """
    try:
        location = (await db.execute(select(Location).where(Location.lat == lat, Location.lon == lon))).scalar_one_or_none()

        if location:
            logger.info(f"Returned location {location.name} from database")
            return location
        
        params = {
            "lat": lat,
            "lon": lon
        }
        logger.info(f"Fetched location from external api")
        data = await fetch_data_from_api("http://api.openweathermap.org/geo/1.0/reverse", params)
        for entry in data:
            new_location = Location(
                name = entry["name"],
                lat = entry["lat"],
                lon = entry["lon"],
                country = entry["country"],
                state = entry.get("state")
            )
            db.add(new_location)
        await db.commit()
        await db.refresh(new_location)
        
        return new_location
    except SQLAlchemyError as e:
        logger.error(f"Unexpected error occurred during API call: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An error occurred. Please try connecting to the internet"
            )