import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class TrackingHit(SQLModel, table=True):
    __tablename__ = "trackinghit"
    id: Optional[int] = Field(default=None, primary_key=True)
    link_id: int = Field(foreign_key="trackinglink.id", index=True)
    hit_type: str = Field(default="link")   # link | pixel
    # Server-captured
    ip: str = Field(default="")
    user_agent: str = Field(default="")
    referrer: str = Field(default="")
    # IP geolocation
    country: str = Field(default="")
    city: str = Field(default="")
    isp: str = Field(default="")
    lat: Optional[float] = Field(default=None)
    lon: Optional[float] = Field(default=None)
    # JS fingerprint (POSTed back from target browser)
    screen: str = Field(default="")
    timezone: str = Field(default="")
    language: str = Field(default="")
    platform: str = Field(default="")
    browser: str = Field(default="")
    plugins: str = Field(default="")
    # GPS (browser permission prompt)
    gps_lat: Optional[float] = Field(default=None)
    gps_lon: Optional[float] = Field(default=None)
    gps_accuracy: Optional[float] = Field(default=None)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
