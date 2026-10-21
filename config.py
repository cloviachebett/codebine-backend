from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Google Earth Engine / CHIRPS
    chirps_collection: str = "UCSB-CHG/CHIRPS/DAILY"
    chirps_scale_m: int = 5566  # CHIRPS native pixel size (0.05 degrees)
    gee_max_features_per_request: int = 4000  # Earth Engine getInfo() allows 5000 rows
    gee_project: str | None = None
    gee_private_key_path: str | None = None
    gee_service_account_email: str | None = None

    # Where sector boundaries come from. sectors.boundary_ref is a path/URI to a GeoJSON file
    boundary_base_dir: str = "."
    boundary_sector_property: str = "ADM3_EN"
    boundary_district_property: str = "ADM2_EN"

    rainfall_sync_enabled: bool = False
    rainfall_sync_interval_hours: float = 24
    rainfall_sync_lookback_days: int = 7


settings = Settings()
