import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from database import get_db
from schemas.sectors import (
    SectorCreate,
    SectorRead,
    SectorUpdate,
)
from services.sectors import sector_service

router = APIRouter(prefix="/api/v1/sectors", tags=["Sectors"])


@router.get("", response_model=list[SectorRead])
def get_all_sectors(
    province_name: str | None = Query(None),
    district_name: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return sector_service.get_all_sectors(db, province_name, district_name, skip, limit)


@router.get("/{sector_id}", response_model=SectorRead)
def get_sector(sector_id: uuid.UUID, db: Session = Depends(get_db)):
    return sector_service.get_sector(db, sector_id)


@router.post("", response_model=SectorRead, status_code=status.HTTP_201_CREATED)
def create_sector(sector: SectorCreate, db: Session = Depends(get_db)):
    return sector_service.create_sector(db, sector)


@router.patch("/{sector_id}", response_model=SectorRead)
def update_sector(
    sector_id: uuid.UUID, updated_sector: SectorUpdate, db: Session = Depends(get_db)
):
    return sector_service.update_sector(db, sector_id, updated_sector)


@router.delete("/{sector_id}", status_code=status.HTTP_200_OK)
def delete_sector(sector_id: uuid.UUID, db: Session = Depends(get_db)):
    return sector_service.delete_sector(db, sector_id)
