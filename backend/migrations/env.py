import re
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.db.models import *  # noqa: F401,F403 — registers all models with SQLModel.metadata
from sqlmodel import SQLModel
from app.config import Config

# Convert the async URL to a psycopg2 sync URL for Alembic.
# psycopg2 is the most reliable driver for running Alembic migrations and
# doesn't support the channel_binding param (a psycopg3-only feature).
_async_url: str = Config.DATABASE_URL or ""
_sync_url = re.sub(r"postgresql\+psycopg[^:]*://", "postgresql+psycopg2://", _async_url)
# Strip channel_binding=require (psycopg3-only, breaks psycopg2)
_sync_url = re.sub(r"[&?]channel_binding=[^&]*", "", _sync_url)

config = context.config
config.set_main_option("sqlalchemy.url", _sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

