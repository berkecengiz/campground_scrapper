from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class CampgroundTable(Base):
    """SQLAlchemy model for campground data"""
    __tablename__ = "campgrounds"
    
    id = Column(String, primary_key=True, index=True)
    type = Column(String)
    # links = Column(JSONB)
    name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    region_name = Column(String)
    administrative_area = Column(String, nullable=True)
    nearest_city_name = Column(String, nullable=True)
    accommodation_type_names = Column(ARRAY(String), default=[])
    bookable = Column(Boolean, default=False)
    camper_types = Column(ARRAY(String), default=[])
    operator = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    photo_urls = Column(ARRAY(String), default=[])
    photos_count = Column(Integer, default=0)
    rating = Column(Float, nullable=True)
    reviews_count = Column(Integer, default=0)
    slug = Column(String, nullable=True)
    price_low = Column(Float, nullable=True)
    price_high = Column(Float, nullable=True)
    availability_updated_at = Column(DateTime, nullable=True)
    address = Column(String, default="")
    
    # Tracking columns
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScraperStats(Base):
    """SQLAlchemy model for scraper statistics"""
    __tablename__ = "scraper_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_date = Column(DateTime, default=datetime.utcnow)
    total_campgrounds = Column(Integer, default=0)
    new_campgrounds = Column(Integer, default=0)
    updated_campgrounds = Column(Integer, default=0)
    regions_count = Column(Integer, default=0)
    min_latitude = Column(Float)
    max_latitude = Column(Float)
    min_longitude = Column(Float)
    max_longitude = Column(Float)
    duration_seconds = Column(Float)
    error_message = Column(String, nullable=True)