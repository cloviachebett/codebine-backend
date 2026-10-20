import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models._enums import GeologyClass


class SectorBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    province_name: str = Field(min_length=1, max_length=50)
    district_name: str = Field(min_length=1, max_length=100)
    sector_name: str = Field(min_length=1, max_length=50)
    boundary_ref: str | None = Field(default=None, min_length=1)
    mean_slope_deg: float | None = Field(default=None, ge=0, le=90)
    geology_class: GeologyClass | None = None
    soil_features: dict[str, Any] | None = None
    land_cover_class: str | None = Field(default=None, min_length=1, max_length=100)


class SectorCreate(SectorBase):
    pass


class SectorUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    province_name: str | None = Field(default=None, min_length=1, max_length=50)
    district_name: str | None = Field(default=None, min_length=1, max_length=100)
    sector_name: str | None = Field(default=None, min_length=1, max_length=50)
    boundary_ref: str | None = Field(default=None, min_length=1)
    mean_slope_deg: float | None = Field(default=None, ge=0, le=90)
    geology_class: GeologyClass | None = None
    soil_features: dict[str, Any] | None = None
    land_cover_class: str | None = Field(default=None, min_length=1, max_length=100)


class SectorRead(SectorBase):
    sector_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
