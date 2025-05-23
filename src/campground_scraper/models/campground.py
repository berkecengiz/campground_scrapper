from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

class CampgroundLinks(BaseModel):
    self: HttpUrl

class Campground(BaseModel):
    """
    Pydantic model representing campground data.
    """
    id: str
    type: str
    links: CampgroundLinks
    name: str
    latitude: float
    longitude: float
    region_name: str = Field(..., alias="region-name")
    administrative_area: Optional[str] = Field(None, alias="administrative-area")
    nearest_city_name: Optional[str] = Field(None, alias="nearest-city-name")
    accommodation_type_names: List[str] = Field(default_factory=list, alias="accommodation-type-names")
    bookable: bool = False
    camper_types: List[str] = Field(default_factory=list, alias="camper-types")
    operator: Optional[str] = None
    photo_url: Optional[HttpUrl] = Field(None, alias="photo-url")
    photo_urls: List[HttpUrl] = Field(default_factory=list, alias="photo-urls")
    photos_count: int = Field(0, alias="photos-count")
    rating: Optional[float] = None
    reviews_count: int = Field(0, alias="reviews-count")
    slug: Optional[str] = None
    price_low: Optional[float] = Field(None, alias="price-low")
    price_high: Optional[float] = Field(None, alias="price-high")
    availability_updated_at: Optional[datetime] = Field(None, alias="availability-updated-at")
    address: Optional[str] = ""
