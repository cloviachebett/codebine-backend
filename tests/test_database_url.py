import os
import subprocess
import sys

import pytest

CHECK = "import database; print(database.DATABASE_URL, database.engine.url.get_backend_name())"


@pytest.mark.parametrize(
    "given",
    [
        "postgres://user:secret@db.example.com:5432/app",
        "postgresql://user:secret@db.example.com:5432/app",
    ],
)
def test_database_url_works_with_heroku_format(given):
    result = subprocess.run(
        [sys.executable, "-c", CHECK],
        env={**os.environ, "DATABASE_URL": given},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.split() == [
        "postgresql://user:secret@db.example.com:5432/app",
        "postgresql",
    ]
