import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.risk_inference_repository import risk_inference_repository


class RiskInferenceService:
    def __init__(self, db: AsyncSession):
        self.repo = risk_inference_repository
        self.db = db

    async def record_prediction(
        self,
        model_version_id: uuid.UUID | None,
        sector_id: uuid.UUID,
        risk_level: str,
        risk_score: float,
    ):
        result = await self.repo.create(
            self.db, model_version_id, sector_id, risk_level, risk_score
        )
        await self.db.commit()
        await self.db.refresh(result)
        return result

    async def fetch_prediction(self, inference_id: uuid.UUID):
        return await self.repo.get_by_id(self.db, inference_id)
