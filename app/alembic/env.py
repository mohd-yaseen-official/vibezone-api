from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
import os
from dotenv import load_dotenv

load_dotenv()

from core.database import Base, sync_engine

from app_users.models import User, PasswordResetToken
from app_goals.models import Goal
from app_tasks.models import Task
from app_reports.models import MonthlyReport, WeeklyReport
from app_subscriptions.models import StripeSubscription

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = os.getenv("database_url").replace("asyncpg", "psycopg2")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = sync_engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()