import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RainfallMatrixBase(BaseModel):
    sector_id: uuid.UUID
    observation_time: datetime
    rain_1day_mm: float
    rain_3day_mm: float
    rain_7day_mm: float
    rain_10day_mm: float
    rain_30day_mm: float


class RainfallMatrixRead(RainfallMatrixBase):
    rainfall_id: uuid.UUID
    dataset_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class RainfallSyncResult(BaseModel):
    start_date: str
    end_date: str
    requested_end_date: str
    chirps_latest_available: str
    clamped_to_latest_available: bool
    sectors_synced: int
    rows_inserted: int
    rows_updated: int
    days_skipped_incomplete: int
    sectors_with_missing_data: list[str]
    sector_days_without_chirps_value: int


class RainfallStatus(BaseModel):
    stored_rows: int
    sectors_with_data: int
    latest_stored_date: str | None = None
    dataset_status: str | None = None
    last_synced_at: str | None = None
    chirps_latest_available: str | None = None
