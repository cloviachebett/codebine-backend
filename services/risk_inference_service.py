import uuid
from datetime import date, datetime, time, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from repositories.risk_inference_repository import risk_inference_repository
from models._enums import RiskLevel
from models.model_versions import ModelVersion
from models.risk_inferences import RiskInference
from models.sectors import Sector


class RiskInferenceService:
    def __init__(self, db: Session):
        self.repo = risk_inference_repository
        self.db = db

    def record_prediction(
        self,
        model_version_id: uuid.UUID | None,
        sector_id: uuid.UUID,
        risk_level: str,
        risk_score: float,
    ):
        sector = self.db.get(Sector, sector_id)
        if not sector:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sector not found.",
            )

        if model_version_id is not None:
            model_version = self.db.get(ModelVersion, model_version_id)
            if not model_version:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Model version not found.",
                )

        try:
            return self.repo.create(
                self.db, model_version_id, sector_id, risk_level, risk_score
            )
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not record prediction. Referenced records may be missing.",
            )

    def fetch_prediction(self, inference_id: uuid.UUID):
        result = self.repo.get_by_id(self.db, inference_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prediction signature log entries not found.",
            )
        return result

    def list_predictions(
        self,
        district: str | None = None,
        risk_level: str | None = None,
        start: date | None = None,
        end: date | None = None,
        latest_only: bool = False,
        limit: int = 500,
    ) -> list[dict]:
        query = self.db.query(RiskInference, Sector).join(
            Sector, RiskInference.sector_id == Sector.sector_id
        )
        if district:
            query = query.filter(Sector.district_name == district)
        if risk_level:
            try:
                level = RiskLevel(risk_level.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Unknown risk level: {risk_level}",
                )
            query = query.filter(RiskInference.risk_level == level)
        if start:
            query = query.filter(
                RiskInference.prediction_time
                >= datetime.combine(start, time.min, tzinfo=timezone.utc)
            )
        if end:
            query = query.filter(
                RiskInference.prediction_time
                < datetime.combine(
                    end + timedelta(days=1), time.min, tzinfo=timezone.utc
                )
            )
        query = query.order_by(RiskInference.prediction_time.desc())
        if not latest_only:
            query = query.limit(limit)
        rows = query.all()
        seen: set[uuid.UUID] = set()
        items = []
        for inference, sector in rows:
            if latest_only and sector.sector_id in seen:
                continue
            seen.add(sector.sector_id)
            items.append(
                {
                    "inference_id": inference.inference_id,
                    "sector_id": sector.sector_id,
                    "sector_name": sector.sector_name,
                    "district_name": sector.district_name,
                    "model_version_id": inference.model_version_id,
                    "prediction_time": inference.prediction_time,
                    "risk_level": inference.risk_level.value,
                    "risk_score": float(inference.risk_score),
                }
            )
            if len(items) >= limit:
                break
        return items
