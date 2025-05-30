# app/models/weather_data.py

from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, DateTime,
    Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base

class WeatherData(Base):
    __tablename__ = "weather_data"
    __table_args__ = (
        Index('ix_weather_data_city_time', 'city_id', 'data_calculation_time'),
        UniqueConstraint('city_id', 'data_calculation_time', name='uq_weather_data_city_time'),
    )

    id = Column(Integer, primary_key=True, index=True)
    weather_main = Column(String)
    description = Column(String)
    data_calculation_time = Column(DateTime)
    temperature = Column(Float)
    feels_like = Column(Float)
    min_temperature = Column(Float)
    max_temperature = Column(Float)
    pressure = Column(Float)
    humidity = Column(Integer)
    sea_level = Column(Float)
    ground_level = Column(Float)
    weather_degrees = Column(Float)
    wind_speed = Column(Float)
    wind_gust = Column(Float)
    rain = Column(Float)
    snow = Column(Float)
    cloudiness = Column(Integer)
    visibility = Column(Float)
    part_of_day = Column(String)
    sunrise_time = Column(DateTime)
    sunset_time = Column(DateTime)
    city_id = Column(Integer, ForeignKey("locations.id"))

    city = relationship("Location", back_populates="weather_data")
