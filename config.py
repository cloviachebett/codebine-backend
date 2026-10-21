from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    boundary_base_dir: str = "."
    boundary_sector_property: str = "ADM3_EN"
    boundary_district_property: str = "ADM2_EN"

    rainfall_sync_enabled: bool = False
    rainfall_sync_interval_hours: float = 24
    rainfall_sync_lookback_days: int = 7


settings = Settings()
