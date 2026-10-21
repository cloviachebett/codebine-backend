import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.sectors import Sector
from repositories.sectors import SectorRepository
from schemas.sectors import SectorCreate, SectorUpdate


class SectorService:
    def __init__(self):
        self.sector_repository = SectorRepository()

    def get_sector(self, db: Session, sector_id: uuid.UUID):
        sector = self.sector_repository.get(db, sector_id)
        if not sector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Sector not found"
            )
        return sector

    def get_all_sectors(
        self,
        db: Session,
        province_name: str | None = None,
        district_name: str | None = None,
        skip: int = 0,
        limit: int | None = None,
    ):
        return self.sector_repository.get_all(
            db, province_name, district_name, skip, limit
        )

    def create_sector(self, db: Session, sector: SectorCreate):
        data = sector.model_dump()
        self._ensure_unique(db, data["district_name"], data["sector_name"])
        new_sector = Sector(**data)
        try:
            return self.sector_repository.create(db, new_sector)
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A sector with this name already exists in this district",
            ) from exc

    def update_sector(
        self, db: Session, sector_id: uuid.UUID, updated_sector: SectorUpdate
    ):
        existing_sector = self.get_sector(db, sector_id)
        updated_data = updated_sector.model_dump(exclude_unset=True, exclude_none=True)

        if {"district_name", "sector_name"} & updated_data.keys():
            self._ensure_unique(
                db,
                updated_data.get("district_name", existing_sector.district_name),
                updated_data.get("sector_name", existing_sector.sector_name),
                ignore_id=sector_id,
            )

        for key, value in updated_data.items():
            setattr(existing_sector, key, value)
        try:
            return self.sector_repository.update(db, existing_sector)
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A sector with this name already exists in this district",
            ) from exc

    def delete_sector(self, db: Session, sector_id: uuid.UUID):
        sector = self.get_sector(db, sector_id)
        linked = {
            name: count
            for name, count in self.sector_repository.count_linked_records(
                db, sector_id
            ).items()
            if count
        }
        if linked:
            details = ", ".join(f"{count} in {name}" for name, count in linked.items())
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Sector still has linked records ({details}); remove them first",
            )
        self.sector_repository.delete(db, sector)
        return {"detail": "Sector deleted successfully"}

    def _ensure_unique(
        self,
        db: Session,
        district_name: str,
        sector_name: str,
        ignore_id: uuid.UUID | None = None,
    ):
        found = self.sector_repository.get_by_location(db, district_name, sector_name)
        if found and found.sector_id != ignore_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A sector with this name already exists in this district",
            )


sector_service = SectorService()
