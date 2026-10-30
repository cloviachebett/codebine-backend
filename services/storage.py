import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _client():
    import boto3

    return boto3.client("s3", region_name=os.getenv("AWS_REGION") or None)


def split_s3_path(path: str) -> tuple[str, str]:
    bucket, _, key = path.removeprefix("s3://").partition("/")
    if not bucket or not key:
        raise ValueError(f"Not a valid S3 path: {path}")
    return bucket, key


def download_model(path: str) -> str:
    bucket, key = split_s3_path(path)
    folder = os.path.join(tempfile.gettempdir(), "terrawatch-models", bucket)
    os.makedirs(folder, exist_ok=True)
    local = os.path.join(folder, key.replace("/", "_"))
    if not os.path.exists(local):
        _client().download_file(bucket, key, local)
    return local


def save_daily_run(
    summary: dict[str, Any], results: list[dict[str, Any]]
) -> str | None:
    bucket = os.getenv("S3_BUCKET")
    if not bucket:
        return None
    now = datetime.now(timezone.utc)
    key = f"daily-runs/{now:%Y-%m-%d}/{now:%H%M%S}.json"
    body = json.dumps({"summary": summary, "sectors": results}, default=str)
    try:
        _client().put_object(
            Bucket=bucket,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
        )
    except Exception as exc:
        logger.warning("Could not save the daily run to S3: %s", exc)
        return None
    return f"s3://{bucket}/{key}"
