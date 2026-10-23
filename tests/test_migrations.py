import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

MIGRATE = "import migrate; migrate.run_migrations()"
CREATE_TABLES = "import models; from database import create_tables; create_tables()"
REPORT = (
    "import models\n"
    "from alembic.autogenerate import compare_metadata\n"
    "from alembic.migration import MigrationContext\n"
    "from sqlalchemy import inspect\n"
    "from database import Base, engine\n"
    "with engine.connect() as connection:\n"
    "    context = MigrationContext.configure(connection)\n"
    "    print(sorted(set(Base.metadata.tables) - set(inspect(engine).get_table_names())))\n"
    "    print(context.get_current_revision())\n"
    "    print(compare_metadata(context, Base.metadata))\n"
)
HEAD = (
    "from alembic.config import Config\n"
    "from alembic.script import ScriptDirectory\n"
    "print(ScriptDirectory.from_config(Config('alembic.ini')).get_current_head())\n"
)


def run(code, database_url):
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip().splitlines()


@pytest.fixture
def database_url(tmp_path):
    return f"sqlite:///{tmp_path / 'migrations.db'}"


@pytest.fixture
def head(database_url):
    return run(HEAD, database_url)[-1]


def test_empty_database_is_built_by_migrations(database_url, head):
    run(MIGRATE, database_url)
    missing, revision, differences = run(REPORT, database_url)[-3:]
    assert missing == "[]"
    assert revision == head
    assert differences == "[]"


def test_database_built_by_create_tables_is_adopted(database_url, head):
    run(CREATE_TABLES, database_url)
    run(MIGRATE, database_url)
    run(MIGRATE, database_url)
    missing, revision, differences = run(REPORT, database_url)[-3:]
    assert missing == "[]"
    assert revision == head
    assert differences == "[]"


def test_migrations_have_a_single_head(database_url):
    heads = run(
        "from alembic.config import Config\n"
        "from alembic.script import ScriptDirectory\n"
        "print(len(ScriptDirectory.from_config(Config('alembic.ini')).get_heads()))\n",
        database_url,
    )
    assert heads[-1] == "1"
