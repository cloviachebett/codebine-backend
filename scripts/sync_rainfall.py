import argparse
import json
from datetime import date
from uuid import UUID

from database import SessionLocal
from services.scheduler import run_rainfall_sync


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--start", type=date.fromisoformat, help="YYYY-MM-DD")
    parser.add_argument("--end", type=date.fromisoformat, help="YYYY-MM-DD")
    parser.add_argument("--sector-id", type=UUID)
    args = parser.parse_args()

    summary = run_rainfall_sync(
        SessionLocal,
        sector_ids=[args.sector_id] if args.sector_id else None,
        start=args.start,
        end=args.end,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
