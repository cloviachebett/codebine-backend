import os
import uuid
import joblib
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from repositories.model_version_repository import model_version_repository
from models._enums import ModelStatus, RiskLevel
from models.model_versions import ModelVersion
from models.risk_inferences import RiskInference
from repositories.risk_inference_repository import risk_inference_repository
from repositories.sectors import sector_repository
from services import storage


class ModelVersionService:
    # Cache loaded models keyed by model_version_id so each version
    # loads into memory exactly once and is never confused with another.
    _loaded_model_cache: dict = {}

    def __init__(self, db: Session):
        self.repo = model_version_repository
        self.db = db

    def _get_model(self, model_record):
        # Get model from cache, loading if needed.
        if model_record.model_version_id not in ModelVersionService._loaded_model_cache:
            ModelVersionService._loaded_model_cache[model_record.model_version_id] = (
                self._load_model(model_record)
            )
        return ModelVersionService._loaded_model_cache[model_record.model_version_id]

    def _load_model(self, model_record):
        # Load a model from disk, resolving paths safely inside the project.
        pkl_path = str(model_record.model_path)

        if pkl_path.startswith("s3://"):
            try:
                pkl_path = storage.download_model(pkl_path)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Could not download the model from S3: {e}",
                )
        elif os.path.isabs(pkl_path) and pkl_path.startswith("/assets/"):
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

    def active_model(self) -> ModelVersion:
        wanted = os.getenv("RISK_MODEL_VERSION_ID")
        if wanted:
            model = self.repo.get_by_id(self.db, uuid.UUID(wanted))
            if model is None:
                raise LookupError(f"RISK_MODEL_VERSION_ID {wanted} was not found")
            return model
        for model_status in (
            ModelStatus.DEPLOYED,
            ModelStatus.READY,
            ModelStatus.TRAINING,
        ):
            model = self.repo.newest_with_status(self.db, model_status)
            if model is not None:
                return model
        raise LookupError("No model version is registered")

    def fetch_active(self) -> ModelVersion:
        try:
            return self.active_model()
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc

    def predict_from_request(self, model_version_id: uuid.UUID, payload):
        return self.predict_from_rainfall(
            model_version_id,
            payload.sector_id,
            [obs.model_dump() for obs in payload.rainfall_observations],
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
            if name == "land_cover_class":
                row.append(sector.land_cover_class or "Cropland")
            elif name == "mean_slope_deg":
                row.append(
                    float(sector.mean_slope_deg) if sector.mean_slope_deg else 22.0
                )
            elif name == "month":
                obs_time = latest_obs.get("observation_time")
                if not obs_time:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Missing feature value for month",
                    )
                try:
                    dt = datetime.fromisoformat(obs_time.replace("Z", "+00:00"))
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid observation_time format: {obs_time}",
                    )
                row.append(dt.month)
            else:
                value = latest_obs.get(name)
                if value is None:
                    value = self._sector_feature(sector, name)
                if value is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Missing feature value for {name}",
                    )
                row.append(value)
        return row

    @staticmethod
    def _sector_feature(sector, name: str):
        soil = sector.soil_features if isinstance(sector.soil_features, dict) else {}
        if name in soil:
            return soil[name]
        if name.startswith("soil_") and name[5:] in soil:
            return soil[name[5:]]
        if name in sector.__table__.columns.keys():
            value = getattr(sector, name)
            if hasattr(value, "value"):
                return value.value
            if isinstance(value, Decimal):
                return float(value)
            return value
        return None

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
        sector = sector_repository.get(self.db, sector_id)
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
        model_inputs = dict(zip(model.feature_names_in_, feature_row))
        risk_score = self.calculate_prediction(model_version_id, [feature_row])

        inference = RiskInference(
            sector_id=sector_id,
            model_version_id=model_version_id,
            risk_score=risk_score,
            risk_level=self._classify_risk(risk_score),
        )
        risk_inference_repository.save_with_snapshot(
            self.db,
            inference,
            {
                "rainfall_observations": rainfall_observations,
                "sector_id": str(sector_id),
                "landcover": sector.land_cover_class,
                "model_inputs": model_inputs,
            },
        )
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
