import itertools
from datetime import date
from decimal import Decimal

from models import (
    EmergencyAlert,
    IncidentReport,
    LandslideInventory,
    ModelVersion,
    PredictionFeature,
    RainfallMatrix,
    RiskInference,
    RiskReview,
    Sector,
    SystemAuditLog,
    User,
)
from models._enums import (
    AlertChannel,
    AlertSeverity,
    GeologyClass,
    ReviewDecision,
    RiskLevel,
)

_counter = itertools.count(1)


def _n() -> int:
    return next(_counter)


def make_sector(**overrides) -> Sector:
    n = _n()
    defaults = {
        "province_name": "Western",
        "district_name": f"District {n}",
        "sector_name": f"Sector {n}",
        "boundary_ref": f"boundaries/sector_{n}.geojson",
        "mean_slope_deg": Decimal("23.50"),
        "geology_class": GeologyClass.GRANITE,
        "soil_features": {"texture": "clay loam", "depth_cm": 120},
        "land_cover_class": "Cropland",
    }
    return Sector(**{**defaults, **overrides})


def make_user(**overrides) -> User:
    n = _n()
    defaults = {
        "full_name": f"Test User {n}",
        "email": f"user{n}@example.com",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        "phone": None,
        "mfa_enrolled": False,
        "failed_login_attempts": 0,
        "locked_until": None,
    }
    return User(**{**defaults, **overrides})


def make_rainfall(sector: Sector, **overrides) -> RainfallMatrix:
    defaults = {"sector": sector, "observation_date": date(2026, 4, 1)}
    return RainfallMatrix(**{**defaults, **overrides})


def make_landslide(sector: Sector, **overrides) -> LandslideInventory:
    defaults = {
        "sector": sector,
        "event_date": date(2023, 5, 3),
        "source_name": "RNRA inventory",
    }
    return LandslideInventory(**{**defaults, **overrides})


def make_model_version(**overrides) -> ModelVersion:
    n = _n()
    defaults = {
        "model_name": f"landslide-rf-{n}",
        "version_code": "v1.0.0",
        "model_type": "RandomForest",
        "model_path": f"models/landslide_rf_{n}.joblib",
    }
    return ModelVersion(**{**defaults, **overrides})


def make_inference(sector: Sector, **overrides) -> RiskInference:
    defaults = {
        "sector": sector,
        "risk_level": RiskLevel.HIGH,
        "risk_score": Decimal("0.78000"),
    }
    return RiskInference(**{**defaults, **overrides})


def make_feature_snapshot(inference: RiskInference, **overrides) -> PredictionFeature:
    defaults = {
        "inference": inference,
        "historical_features": {"rain_7day": 84.2, "slope": 23.5},
    }
    return PredictionFeature(**{**defaults, **overrides})


def make_alert(inference: RiskInference, **overrides) -> EmergencyAlert:
    defaults = {
        "inference": inference,
        "sector": inference.sector,
        "alert_message": "High landslide risk forecast for the next 24 hours.",
        "severity": AlertSeverity.HIGH,
        "channel": AlertChannel.SMS,
    }
    return EmergencyAlert(**{**defaults, **overrides})


def make_review(reviewer: User, **overrides) -> RiskReview:
    defaults = {"reviewed_by_user": reviewer, "decision": ReviewDecision.APPROVED}
    return RiskReview(**{**defaults, **overrides})


def make_incident(sector: Sector, **overrides) -> IncidentReport:
    defaults = {
        "sector": sector,
        "event_date": date(2026, 4, 2),
        "description": "Slope failure blocked the road above the market.",
    }
    return IncidentReport(**{**defaults, **overrides})


def make_audit_log(**overrides) -> SystemAuditLog:
    defaults = {"action_type": "LOGIN", "entity_type": "USER"}
    return SystemAuditLog(**{**defaults, **overrides})
