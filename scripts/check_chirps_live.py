import argparse
import sys
from datetime import timedelta

from config import settings
from database import SessionLocal
from models.sectors import Sector
from services.chirps_gee import CHIRPSGEEService
from services.rainfall_matrices import RainfallService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sectors", type=int, default=3, help="how many sectors to test"
    )
    parser.add_argument(
        "--days", type=int, default=5, help="how many recent days to fetch"
    )
    args = parser.parse_args()

    print(f"GEE project: {settings.gee_project or 'NOT SET'}")
    print(f"Key path:    {settings.gee_private_key_path or 'NOT SET'}")

    db = SessionLocal()
    try:
        sectors = db.query(Sector).limit(args.sectors).all()
        if not sectors:
            sys.exit("No sectors in the database yet.")
        areas = [
            RainfallService()._to_area(s) for s in sectors
        ]  # resolves boundary_ref
    finally:
        db.close()

    service = CHIRPSGEEService()
    latest = service.latest_available_date()
    print(f"Newest CHIRPS day available: {latest}")

    daily = service.fetch_daily_rainfall(
        areas, latest - timedelta(days=args.days - 1), latest
    )
    for sector, area in zip(sectors, areas):
        values = daily[area.sector_id]
        print(f"\n{sector.sector_name} ({sector.district_name}):")
        for day in sorted(values):
            print(f"  {day}  {values[day]:.2f} mm")
    if service.unresolved:
        print(
            f"\nWARNING: {len(service.unresolved)} sector-days had no CHIRPS value (left empty, not zero)."
        )
    print("\nThis is live CHIRPS data from Google Earth Engine.")


if __name__ == "__main__":
    main()
