from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

from services.rainfall_math import chunk_days, days_per_chunk

try:
    import ee
except ImportError:
    ee = None


load_dotenv()

logger = logging.getLogger(__name__)

PRECIPITATION_BAND = "precipitation"


@dataclass(frozen=True)
class SectorArea:
    sector_id: str
    geometry: dict
    centroid_lat: float
    centroid_lon: float


class CHIRPSGEEService:
    """Fetch daily CHIRPS rainfall for sectors using Google Earth Engine."""

    def __init__(self, ee_module=ee):
        self._ee = ee_module
        self._initialized = False

        self.chirps_id = os.environ["CHIRPS_ID"]
        self.scale = int(os.environ["CHIRPS_SCALE_M"])
        self.max_features = int(os.environ["GEE_MAX_FEATURES_PER_REQUEST"])
        self.gee_project = os.getenv("GEE_PROJECT")
        self.gee_private_key_path = os.getenv("GEE_PRIVATE_KEY_PATH")
        self.gee_service_account_email = os.getenv("GEE_SERVICE_ACCOUNT_EMAIL")

        self.unresolved: list[tuple[str, date]] = []

    def initialize(self) -> None:
        if self._initialized:
            return

        if self._ee is None:
            raise RuntimeError(
                "earthengine-api is not installed; "
                "install it and configure GEE credentials."
            )

        try:
            kwargs = {}

            if self.gee_project:
                kwargs["project"] = self.gee_project

            credentials = self._credentials()

            if credentials is not None:
                kwargs["credentials"] = credentials

            self._ee.Initialize(**kwargs)

        except (self._ee.EEException, OSError, ValueError) as exc:
            raise RuntimeError(
                f"Could not initialise Google Earth Engine: {exc}"
            ) from exc

        self._initialized = True

    def _credentials(self):
        path = self.gee_private_key_path

        if not path:
            return None

        key_path = Path(path).expanduser()

        if not key_path.exists():
            raise RuntimeError(f"GEE key file not found: {key_path}")

        key_text = key_path.read_text()

        email = self.gee_service_account_email or json.loads(key_text).get(
            "client_email"
        )

        if not email:
            raise RuntimeError(
                "No GEE service account email configured or found in the key file."
            )

        return self._ee.ServiceAccountCredentials(
            email,
            key_data=key_text,
        )

    def latest_available_date(self) -> date:
        self.initialize()

        try:
            millis = (
                self._ee.ImageCollection(self.chirps_id)
                .aggregate_max("system:time_start")
                .getInfo()
            )

        except (self._ee.EEException, OSError) as exc:
            raise RuntimeError(f"Could not read the latest CHIRPS date: {exc}") from exc

        if millis is None:
            raise RuntimeError(f"CHIRPS  {self.chirps_id} returned no images.")

        return datetime.fromtimestamp(
            millis / 1000,
            tz=timezone.utc,
        ).date()

    def fetch_daily_rainfall(
        self,
        areas: Sequence[SectorArea],
        start: date,
        end: date,
    ) -> dict[str, dict[date, float]]:
        if start > end:
            raise ValueError("start must not be after end")

        self.initialize()
        self.unresolved = []

        result: dict[str, dict[date, float]] = {area.sector_id: {} for area in areas}

        if not areas:
            return result

        step = days_per_chunk(len(areas), self.max_features)

        for chunk_start, chunk_end in chunk_days(start, end, step):
            targets = [(area.sector_id, area.geometry) for area in areas]

            rows = self._reduce_chunk(
                targets,
                chunk_start,
                chunk_end,
            )

            missing: set[tuple[str, date]] = set()

            for sector_id, day, mm in rows:
                if mm is None:
                    missing.add((sector_id, day))
                else:
                    result[sector_id][day] = float(mm)

            if missing:
                missing_ids = {sector_id for sector_id, _ in missing}

                points = [
                    (
                        area.sector_id,
                        {
                            "type": "Point",
                            "coordinates": [
                                area.centroid_lon,
                                area.centroid_lat,
                            ],
                        },
                    )
                    for area in areas
                    if area.sector_id in missing_ids
                ]

                fallback_rows = self._reduce_chunk(
                    points,
                    chunk_start,
                    chunk_end,
                )

                for sector_id, day, mm in fallback_rows:
                    if mm is not None and (sector_id, day) in missing:
                        result[sector_id][day] = float(mm)
                        missing.discard((sector_id, day))

            self.unresolved.extend(sorted(missing))

        if self.unresolved:
            logger.warning(
                "%d sector-days had no CHIRPS value",
                len(self.unresolved),
            )

        return result

    def _reduce_chunk(
        self,
        targets: Sequence[tuple[str, dict]],
        start: date,
        end: date,
    ) -> list[tuple[str, date, float | None]]:
        ee_ = self._ee

        try:
            features = ee_.FeatureCollection(
                [
                    ee_.Feature(
                        ee_.Geometry(geometry, None, False),
                        {"sector_id": sector_id},
                    )
                    for sector_id, geometry in targets
                ]
            )

            images = (
                ee_.ImageCollection(self.chirps_id)
                .filterDate(
                    start.isoformat(),
                    (end + timedelta(days=1)).isoformat(),
                )
                .select(PRECIPITATION_BAND)
            )

            def per_image(image):
                day = image.date().format("YYYY-MM-dd")

                reduced = image.reduceRegions(
                    collection=features,
                    reducer=ee_.Reducer.mean(),
                    scale=self.scale,
                )

                return reduced.map(
                    lambda feature: ee_.Feature(
                        None,
                        {
                            "sector_id": feature.get("sector_id"),
                            "day": day,
                            "mm": feature.get("mean"),
                        },
                    )
                )

            table = ee_.FeatureCollection(images.map(per_image)).flatten()

            info = table.getInfo()

        except (ee_.EEException, OSError) as exc:
            raise RuntimeError(
                f"CHIRPS request failed for {start}..{end}: {exc}"
            ) from exc

        rows = []

        for feature in info.get("features", []):
            properties = feature["properties"]

            rows.append(
                (
                    properties["sector_id"],
                    date.fromisoformat(properties["day"]),
                    properties.get("mm"),
                )
            )

        return rows
