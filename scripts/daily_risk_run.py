import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from services.risk_run import run_daily_risk

db = SessionLocal()
try:
    summary = run_daily_risk(db, sync="--skip-rainfall" not in sys.argv)
    print(json.dumps(summary, indent=2, default=str))
finally:
    db.close()
