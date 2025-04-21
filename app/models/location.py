# app/models/location.py

from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base
from sqlalchemy.orm import relationship

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    country = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    state = Column(String, nullable=True)

    weather_forecasts = relationship("WeatherForecast", back_populates="city")
    weather_data = relationship("WeatherData", back_populates="city")
