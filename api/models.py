"""Pydantic response models for Kajla API."""

from pydantic import BaseModel
from typing import Any


class LocationSummary(BaseModel):
    id: str
    category: str
    name: str
    lat: float
    lon: float
    city: str = ""
    county: str = ""
    address: str = ""
    distance_km: float | None = None
    drive_distance_km: float | None = None
    drive_duration_min: float | None = None


class LocationDetail(LocationSummary):
    details: dict[str, Any] = {}


class LocationListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[LocationSummary]


class CategoryInfo(BaseModel):
    key: str
    label: str
    count: int


class CategoriesResponse(BaseModel):
    categories: list[CategoryInfo]
