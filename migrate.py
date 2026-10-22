import importlib

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from database import Base, engine

importlib.import_module("models")


def run_migrations(config_path: str = "alembic.ini") -> None:
    config = Config(config_path)
    tables = set(inspect(engine).get_table_names())
    if "alembic_version" not in tables and tables & set(Base.metadata.tables):
        command.stamp(config, ScriptDirectory.from_config(config).get_base())
    command.upgrade(config, "head")


if __name__ == "__main__":
    run_migrations()
