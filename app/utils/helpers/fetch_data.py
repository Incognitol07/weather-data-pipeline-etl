# app/utils/helpers/fetch_data.py
from fastapi import HTTPException
from app.utils import logger
from app.core.config import settings
import aiohttp
from app.core.config import settings


async def fetch_data_from_api(endpoint: str, params: dict):
    params["appid"] = settings.WEATHER_API_KEY
    async with aiohttp.ClientSession() as session:
        async with session.get(endpoint, params=params) as response:
            if response.status != 200:
                text = await response.text()
                logger.error(f"API error: {text}")
                raise HTTPException(status_code=response.status, detail=text)
            return await response.json()
