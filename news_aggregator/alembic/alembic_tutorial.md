# Alembic Migrations Tutorial

This tutorial provides a comprehensive guide on how to use Alembic for database migrations in your project.

## Basic Commands

### 1. Create a new migration

Use this command to generate a new migration script. Alembic will automatically detect changes in your models and generate the necessary SQL statements.

```bash
alembic revision -m "Your migration message"
```

   - `-m`:  Specifies a message describing the migration. This is important for tracking changes.
   - Example: `alembic revision -m "Add new column to users table"`

### 2. Upgrade to the latest revision

Use this command to apply all pending migrations to your database.

```bash
alembic upgrade head
```

   - `head`: Refers to the latest revision available.

### 3. Downgrade to a specific revision

Use this command to revert your database to a previous state.

```bash
alembic downgrade <revision_id>
```

   - `<revision_id>`: The specific revision ID to downgrade to.
   - Example: `alembic downgrade 0002`

### 4. Show migration history

Use this command to view the history of your migrations.

```bash
alembic history
```

   - This will show you the revision IDs, messages, and the order in which migrations were applied.

### 5. Show current revision

Use this command to see the current revision of the database.

```bash
alembic current
```

   - This will show you the current revision ID.

### 6. Autogenerate migrations

Use this command to automatically generate migrations based on changes in your models.

```bash
alembic revision --autogenerate -m "Your migration message"
```

   - `--autogenerate`: Tells Alembic to automatically detect changes.
   - `-m`: Specifies a message describing the migration.

### 7. Stamp the database with a specific revision

Use this command to mark the database as being at a specific revision without actually running the migrations. This is useful when you are starting with an existing database.

```bash
alembic stamp <revision_id>
```

   - `<revision_id>`: The specific revision ID to stamp the database with.
   - Example: `alembic stamp head`

## Important Notes

-   Always run migrations in the correct order.
-   Use descriptive messages for your migrations.
-   Test your migrations in a development environment before applying them to production.
-   Be careful when downgrading, as it can lead to data loss.

## Example Workflow

1.  Make changes to your SQLAlchemy models.
2.  Run `alembic revision --autogenerate -m "Your migration message"` to generate a new migration script.
3.  Review the generated script and make any necessary adjustments.
4.  Run `alembic upgrade head` to apply the migration to your database.
5.  Test your changes thoroughly.

## Configuration

-   The `alembic.ini` file contains the configuration for Alembic.
-   The `alembic/env.py` file contains the environment setup for Alembic.
-   The migration scripts are located in the `alembic/versions` directory.

This tutorial should help you understand the basic commands for using Alembic migrations. If you have any further questions, please let me know.