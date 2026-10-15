import enum


class GeologyClass(str, enum.Enum):
    GRANITE = "GRANITE"
    QUARTZITE = "QUARTZITE"
    SCHIST = "SCHIST"
    PEGMATITE = "PEGMATITE"
    ALLUVIUM = "ALLUVIUM"


class ProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class DatasetFactorType(str, enum.Enum):
    RAINFALL = "RAINFALL"
    TERRAIN = "TERRAIN"
    SOIL = "SOIL"
    GEOLOGY = "GEOLOGY"
    LAND_COVER = "LAND_COVER"
    INVENTORY = "INVENTORY"


class ModelStatus(str, enum.Enum):
    TRAINING = "TRAINING"
    READY = "READY"
    DEPLOYED = "DEPLOYED"
    ARCHIVED = "ARCHIVED"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class LandslideSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class IncidentStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"


class AccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class ReviewDecision(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISMISSED = "DISMISSED"


class AlertStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISMISSED = "DISMISSED"


class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertChannel(str, enum.Enum):
    SMS = "SMS"
    EMAIL = "EMAIL"
    PUSH = "PUSH"
