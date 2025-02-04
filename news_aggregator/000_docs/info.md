# venv and sys
conda activate pytorch_env
Public IPv4 address:  
129.213.125.118
Private IPv4 address: 
10.0.0.182

# dagster vm
ocid1.instance.oc1.iad.anuwcljt62g7x7ycs2ahtlwnqxbyu22ap4zlfsosnt2thb7k43a6dbvbea5q
ocid1.tenancy.oc1..aaaaaaaazwnzfsshem5h3phaphasftvjdtnqwwly6nd2jwekakr4vdp7s34q
ocid1.user.oc1..aaaaaaaaxuuxwp42n366bedbjmmfsjwpnt6cralaie5sk5dzod5p4skwxmxq

fingerprint: 24:13:1a:df:44:7a:db:e6:5e:d9:82:56:00:e7:34:d4

[DEFAULT]
user=ocid1.user.oc1..aaaaaaaaxuuxwp42n366bedbjmmfsjwpnt6cralaie5sk5dzod5p4skwxmxq
fingerprint=24:13:1a:df:44:7a:db:e6:5e:d9:82:56:00:e7:34:d4
tenancy=ocid1.tenancy.oc1..aaaaaaaazwnzfsshem5h3phaphasftvjdtnqwwly6nd2jwekakr4vdp7s34q
region=us-ashburn-1
key_file=~/.oci/keys/oci_api_key.pem

# pg
CREATE DATABASE news_aggregator;
CREATE USER news_admin WITH PASSWORD 'fasldkflk423mkj4k24jk242';
sudo -u postgres psql
\c news_aggregator
PGPASSWORD='fasldkflk423mkj4k24jk242' psql -U news_admin_dev -d news_aggregator_dev -h localhost
\dn - list schemas
\d+ pt_bbc.categories
\d+ pt_bbc.articles
\di pt_bbc.*



## show all tables even if they are emtpy
PGPASSWORD='fasldkflk423mkj4k24jk242' psql -U news_admin_dev -d news_aggregator_dev -h localhost -c "
SELECT schemaname, tablename, COALESCE(reltuples, 0) AS approximate_row_count
FROM pg_catalog.pg_tables 
LEFT JOIN pg_class ON pg_tables.tablename = pg_class.relname
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename;"

## show all tables even if they are emtpy + fn + trgg
PGPASSWORD='fasldkflk423mkj4k24jk242' psql -U news_admin_dev -d news_aggregator_dev -h localhost -c "
SELECT 'TABLE' AS type, schemaname, tablename AS name 
FROM pg_catalog.pg_tables 
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
UNION ALL
SELECT 'SEQUENCE' AS type, schemaname, sequencename AS name 
FROM pg_catalog.pg_sequences 
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
UNION ALL
SELECT 'FUNCTION' AS type, n.nspname AS schemaname, p.proname AS name
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
UNION ALL
SELECT 'TRIGGER' AS type, event_object_schema AS schemaname, trigger_name AS name
FROM information_schema.triggers
WHERE event_object_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY type,schemaname, name;"





# Image details
Image details
Operating system:
Oracle Linux
Version:8
Image:
Oracle-Linux-8.10-aarch64-2024.10.31-0
Shape configuration
Shape: VM.Standard.A2.Flex
OCPU count:2
Memory (GB):12


# db
## db setup:
sudo -u postgres /home/opc/miniforge3/envs/pytorch_env/bin/python \
    /home/opc/news_dagster-etl/news_aggregator/db_scripts/setup_database.py dev

ALTER USER news_admin_prod WITH PASSWORD 'fasldkflk423mkj4k24jk242';



Dosljedni tipovi ID-jeva: Trenutačno se miješaju tipovi (neke tablice imaju INT, neke TEXT, neke SERIAL). U većim sustavima korisno je preći na UUID ili bar dosljedno BIGINT.
Normalizacija: Za polja poput event_type, content_type, relationship_type i slično moglo bi se razmisliti o posebnim lookup tablicama radi veće fleksibilnosti i održavanja.

# Alembic Migrations Tutorial

This tutorial provides a comprehensive guide on how to use Alembic for database migrations in your project.

# Migrations
0001_initial_public.py: Creates the base news_portals table in public schema

0002_base_schemas.py: Creates necessary schemas (events, comments, analysis, topics, social, entities)

0003_create_tables_from_models.py: Creates all tables from SQLAlchemy models including:
Static tables in various schemas
Dynamic portal-specific tables (categories and articles) with proper indexes

0004_load_portal_data.py: Loads initial portal configuration data

0005_functions_triggers.py: Creates all necessary functions and triggers for:
Data validation
Reference integrity
Search functionality
Preventing cycles in hierarchical relationships
Automatic updates of search vectors

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

