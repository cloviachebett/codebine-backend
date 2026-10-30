import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from models._enums import RiskLevel
from models.prediction_features import PredictionFeature
from models.risk_inferences import RiskInference
from models.sectors import Sector


class RiskInferenceRepository:
    def __init__(self):
        self.model = RiskInference

    def create(
        self,
        db: Session,
        model_version_id: uuid.UUID | None,
        sector_id: uuid.UUID,
        risk_level: str,
        risk_score: float,
    ) -> RiskInference:
        db_obj = self.model(
            model_version_id=model_version_id,
            sector_id=sector_id,
            risk_level=risk_level,
            risk_score=risk_score,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_id(self, db: Session, inference_id: uuid.UUID) -> RiskInference | None:
        return (
            db.query(self.model).filter(self.model.inference_id == inference_id).first()
        )

    def save_with_snapshot(
        self,
        db: Session,
        inference: RiskInference,
        historical_features: dict,
    ) -> RiskInference:
        db.add(inference)
        db.flush()
        snapshot = PredictionFeature(
            inference_id=inference.inference_id,
            historical_features=historical_features,
        )
        db.add(snapshot)
        db.flush()
        inference.feature_snapshot_id = snapshot.feature_snapshot_id
        db.commit()
        db.refresh(inference)
        return inference

    def sector_ids_predicted_since(
        self, db: Session, model_version_id: uuid.UUID, since: datetime
    ) -> set[uuid.UUID]:
        rows = (
            db.query(self.model.sector_id)
            .filter(
                self.model.model_version_id == model_version_id,
                self.model.prediction_time >= since,
            )
            .all()
        )
        return {sector_id for (sector_id,) in rows}

    def list_with_sectors(
        self,
        db: Session,
        district: str | None = None,
        risk_level: RiskLevel | None = None,
        start: datetime | None = None,
        end_exclusive: datetime | None = None,
        limit: int | None = None,
    ) -> list[tuple[RiskInference, Sector]]:
        query = db.query(self.model, Sector).join(
            Sector, self.model.sector_id == Sector.sector_id
        )
        if district:
            query = query.filter(Sector.district_name == district)
        if risk_level:
            query = query.filter(self.model.risk_level == risk_level)
        if start:
            query = query.filter(self.model.prediction_time >= start)
        if end_exclusive:
            query = query.filter(self.model.prediction_time < end_exclusive)
        query = query.order_by(self.model.prediction_time.desc())
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def rollback(self, db: Session) -> None:
        db.rollback()


risk_inference_repository = RiskInferenceRepository()
