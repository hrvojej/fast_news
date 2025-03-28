# path: /home/opc/news_dagster-etl/news_aggregator/alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from db_scripts.models.models import Base  # Ensure Base is your declarative base
from sqlalchemy import text


target_metadata = Base.metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Step 1: Create necessary schemas BEFORE migrations
        required_schemas = ['analysis', 'events', 'comments', 'topics', 'social', 'entities']
        for schema in required_schemas:
            print(f"Ensuring schema exists: {schema}")
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS {schema};'))

        # Step 2: Configure Alembic and apply migrations
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema='public',
            compare_type=True
        )

        with context.begin_transaction():
            print("Running Alembic migrations...")
            context.run_migrations()
            connection.execute(text("COMMIT;"))

        print("Schema initialization complete!")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
