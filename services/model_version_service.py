import os
import uuid
import joblib
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from repositories.model_version_repository import model_version_repository
from models._enums import RiskLevel
from models.risk_inferences import RiskInference
from models.prediction_features import PredictionFeature


class ModelVersionService:
    # Cache loaded models keyed by model_version_id so each version
    # loads into memory exactly once and is never confused with another.
    _loaded_model_cache: dict = {}

    def __init__(self, db: Session):
        self.repo = model_version_repository
        self.db = db

    def _get_model(self, model_record):
        #Get model from cache, loading if needed.
        if model_record.model_version_id not in ModelVersionService._loaded_model_cache:
            ModelVersionService._loaded_model_cache[model_record.model_version_id] = (
                self._load_model(model_record)
            )
        return ModelVersionService._loaded_model_cache[model_record.model_version_id]

    def _load_model(self, model_record):
        # Load a model from disk, resolving paths safely inside the project.
        pkl_path = str(model_record.model_path)
        
        if os.path.isabs(pkl_path) and pkl_path.startswith("/assets/"):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            pkl_path = os.path.join(project_root, pkl_path.lstrip("/"))
        elif not os.path.isabs(pkl_path):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            pkl_path = os.path.join(project_root, pkl_path.lstrip("/"))
        
        if not os.path.exists(pkl_path):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Deployment Error: Binary weights file missing at target path: {pkl_path}",
            )
        try:
            return joblib.load(pkl_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load model binary: {str(e)}",
            )

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

    @staticmethod
    def _validate_rainfall_observation(obs: dict) -> dict:
        required_keys = [
            "rain_1day_mm",
            "rain_3day_mm",
            "rain_7day_mm",
            "rain_10day_mm",
            "rain_30day_mm",
        ]
        for key in required_keys:
            value = obs.get(key)
            if value is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required rainfall field: {key}",
                )
            if (
                not isinstance(value, (int, float))
                or value < 0
                or not (
                    value == value and value != float("inf") and value != float("-inf")
                )
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid rainfall value for {key}: {value!r}",
                )
        return obs

    def _get_latest_observation(self, rainfall_observations: list) -> dict:
        if not rainfall_observations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No rainfall observations provided.",
            )

        valid_observations = []
        for obs in rainfall_observations:
            obs_time = obs.get("observation_time")
            if not obs_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each observation must have an observation_time",
                )
            try:
                dt = datetime.fromisoformat(obs_time.replace("Z", "+00:00"))
                valid_observations.append((dt, obs))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid observation_time format: {obs_time}",
                )

        latest = max(valid_observations, key=lambda x: x[0])[1]
        return self._validate_rainfall_observation(latest)

    def _build_feature_row(self, model, sector, latest_obs: dict) -> list:
        feature_names = list(model.feature_names_in_)
        row = []
        for name in feature_names:
            if name == "percentage":
                row.append(0.0)
            elif name == "landcover":
                row.append(sector.land_cover_class)
            else:
                value = latest_obs.get(name)
                if value is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Missing feature value for {name}",
                    )
                row.append(value)
        return row

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

            model = self._get_model(model_record)
            feature_names = list(model.feature_names_in_)
            input_data = pd.DataFrame(feature_matrix, columns=feature_names)
            proba = model.predict_proba(input_data)
            return float(proba[0][1])
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

        latest_obs = self._get_latest_observation(rainfall_observations)

        model_record = self.repo.get_by_id(self.db, model_version_id)
        if not model_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model version specification data not found.",
            )
        model = self._get_model(model_record)

        feature_row = self._build_feature_row(model, sector, latest_obs)
        risk_score = self.calculate_prediction(model_version_id, [feature_row])

        inference = RiskInference(
            sector_id=sector_id,
            model_version_id=model_version_id,
            risk_score=risk_score,
            risk_level=self._classify_risk(risk_score),
        )
        self.db.add(inference)
        self.db.flush()

        feature_snapshot = PredictionFeature(
            inference_id=inference.inference_id,
            historical_features={
                "rainfall_observations": rainfall_observations,
                "sector_id": str(sector_id),
                "landcover": sector.land_cover_class,
            },
        )
        self.db.add(feature_snapshot)
        self.db.flush()
        self.db.refresh(feature_snapshot)

        inference.feature_snapshot_id = feature_snapshot.feature_snapshot_id

        self.db.commit()
        self.db.refresh(inference)
        return {
            "inference_id": inference.inference_id,
            "risk_score": risk_score,
            "risk_level": inference.risk_level.value,
            "prediction_time": inference.prediction_time,
            "feature_snapshot_id": inference.feature_snapshot_id,
        }

    @staticmethod
    def _classify_risk(score: float) -> RiskLevel:
        if score >= 0.7:
            return RiskLevel.EXTREME
        if score >= 0.5:
            return RiskLevel.HIGH
        if score >= 0.25:
            return RiskLevel.MODERATE
        return RiskLevel.LOW
