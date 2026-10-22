import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.rainfall_matrices import (
    RainfallMatrixRead,
    RainfallStatus,
    RainfallSyncRequest,
    RainfallSyncResult,
)
from services.rainfall_matrices import rainfall_service

router = APIRouter(prefix="/api/v1/rainfall", tags=["Rainfall"])


@router.get("/matrices", response_model=list[RainfallMatrixRead])
def get_all_matrices(
    sector_id: uuid.UUID | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    return rainfall_service.get_all_matrices(db, sector_id, start_date, end_date, limit)


@router.get("/sectors/{sector_id}", response_model=list[RainfallMatrixRead])
def get_sector_matrix(
    sector_id: uuid.UUID,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    return rainfall_service.get_sector_matrix(db, sector_id, start_date, end_date)


@router.post("/sync", response_model=RainfallSyncResult)
def sync_rainfall(
    payload: RainfallSyncRequest,
    db: Session = Depends(get_db),
):
    return rainfall_service.sync_rainfall(
        db,
        sector_ids=[payload.sector_id] if payload.sector_id else None,
        start=payload.start_date,
        end=payload.end_date,
    )


@router.get("/status", response_model=RainfallStatus)
def get_status(
    include_chirps: bool = Query(
        False, description="Also ask Earth Engine for the newest CHIRPS day"
    ),
    db: Session = Depends(get_db),
):
    return rainfall_service.get_status(db, include_chirps)
