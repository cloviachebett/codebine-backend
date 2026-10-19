import os
import uuid
import joblib
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from repositories.model_version_repository import model_version_repository
from models._enums import RiskLevel
from models.risk_inferences import RiskInference


class ModelVersionService:
    # Cache the pickled model structure directly on the service class
    # so it loads into the server's memory exactly once
    _loaded_model_cache = None

    def __init__(self, db: Session):
        self.repo = model_version_repository
        self.db = db

    def register_version(self, payload_data: dict):
        # Registers a new model version tracking record in the database.
        existing = self.repo.get_by_unique_version(
            self.db, payload_data["model_name"], payload_data["version_code"]
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A model version with this specific combination code name already exists.",
            )
        return self.repo.create(
            self.db,
            model_name=payload_data["model_name"],
            version_code=payload_data["version_code"],
            model_type=payload_data["model_type"],
            model_path=payload_data["model_path"],
            precision=payload_data["precision"],
            recall=payload_data["recall"],
            f1_score=payload_data["f1_score"],
            model_status=payload_data["model_status"],
        )

    def fetch_version(self, model_version_id: uuid.UUID):
        model_record = self.repo.get_by_id(self.db, model_version_id)
        if not model_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model version specification data not found.",
            )
        return model_record

    def calculate_prediction(
        self, model_version_id: uuid.UUID, feature_matrix: list
    ) -> float:
        # 1. Look up the model record in the database to find where the .pkl is stored
        model_record = self.repo.get_by_id(self.db, model_version_id)
        if not model_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model version specification data not found.",
            )

        # 2. Load the model.pkl file into memory if it isn't already cached
        if ModelVersionService._loaded_model_cache is None:
            pkl_path = str(model_record.model_path)
            if not os.path.exists(pkl_path):
                project_root = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
                pkl_path = os.path.join(project_root, pkl_path.lstrip("/"))
                if not os.path.exists(pkl_path):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Deployment Error: Binary weights file missing at target path: {pkl_path}",
                    )
            try:
                ModelVersionService._loaded_model_cache = joblib.load(pkl_path)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to load model binary: {str(e)}",
                )

        # 3. Run the prediction using the cached .pkl file
        try:
            import pandas as pd

            feature_names = list(
                ModelVersionService._loaded_model_cache.feature_names_in_
            )
            input_data = pd.DataFrame(feature_matrix, columns=feature_names)
            proba = ModelVersionService._loaded_model_cache.predict_proba(input_data)
            return float(proba[0][1]) * 100
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Model failed to process the provided matrix array: {str(e)}",
            )

    def predict_from_rainfall(
        self,
        model_version_id: uuid.UUID,
        sector_id: uuid.UUID,
        rainfall_observations: list,
    ):
        from models.sectors import Sector

        sector = self.db.get(Sector, sector_id)
        if not sector:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sector not found.",
            )

        if not rainfall_observations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No rainfall observations provided.",
            )

        latest = rainfall_observations[0]
        feature_row = [
            0.0,
            latest["rain_1day_mm"],
            latest["rain_3day_mm"],
            latest["rain_7day_mm"],
            latest["rain_10day_mm"],
            latest["rain_30day_mm"],
            sector.land_cover_class,
        ]
        risk_score = self.calculate_prediction(model_version_id, [feature_row])

        inference = RiskInference(
            sector_id=sector_id,
            model_version_id=model_version_id,
            risk_level=RiskLevel.LOW,
            risk_score=risk_score / 100,
        )
        self.db.add(inference)
        self.db.commit()
        self.db.refresh(inference)
        return {
            "inference_id": inference.inference_id,
            "risk_score": risk_score,
            "prediction_time": inference.prediction_time,
        }
