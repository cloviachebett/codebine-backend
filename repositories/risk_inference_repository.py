import uuid
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.risk_inferences import RiskInference


class RiskInferenceRepository:
    def __init__(self):
        self.model = RiskInference

    async def create(
        self,
        db: AsyncSession,
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
        await db.flush()
        return db_obj

    async def get_by_id(
        self, db: AsyncSession, inference_id: uuid.UUID
    ) -> RiskInference | None:
        result = await db.execute(
            select(self.model).where(self.model.inference_id == inference_id)
        )
        return result.scalar_one_or_none()


risk_inference_repository = RiskInferenceRepository()
