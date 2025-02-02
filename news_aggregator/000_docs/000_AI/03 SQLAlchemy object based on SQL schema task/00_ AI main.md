Code-First Approach based on create_schemas.sql

# Database Credentials Location
File: config/database/database_config.yaml 

Identify Database Connection Details: You'll need to know how your project connects to the database.

Inspect db_utils.py: We need to read /home/opc/news_dagster-etl/news_aggregator/db_scripts/db_utils.py to understand how database configurations are loaded (e.g., from environment variables, config files). This will be crucial for connecting to the database to create it and later for Alembic configuration:

So here is content of those files:
##### Content of: /home/opc/news_dagster-etl/news_aggregator/db_scripts/db_context.py :
from db_scripts.db_utils import get_db_connection

class DatabaseContext:
    def __init__(self, env: str):
        self.conn = get_db_connection(env)
        if not self.conn:
            raise Exception("Failed to initialize database context due to connection error.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def get_connection(self):
        return self.conn

# Example usage (can be removed later):
if __name__ == '__main__':
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()
            if conn:
                print("Database context initialized and connection obtained successfully.")
            else:
                print("Failed to get database connection from context.")
    except Exception as e:
        print(f"Exception during database context initialization: {e}")


#### Content of: /home/opc/news_dagster-etl/news_aggregator/db_scripts/db_utils.py :
import psycopg2
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config"

def load_db_config():
    config_path = CONFIG_PATH / "database" / "database_config.yaml"
    with open(config_path, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            return None

def get_db_connection(env='dev'):
    db_config = load_db_config()
    if not db_config:
        print("Failed to load database config.")
        return None

    try:
        db_params = db_config[env]
        conn = psycopg2.connect(
            user=db_params['user'],
            password=db_params['password'],
            host=db_params['host'],
            port=db_params['port'],
            database=db_params['name']
        )
        return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        return None

def execute_query(conn, query, params=None):
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Query execution error: {e}")
        return None
    finally:
        cursor.close()



#### Content of: /home/opc/news_dagster-etl/news_aggregator/config/database/database_config.yaml :
dev:
  name: news_aggregator_dev
  user: news_admin_dev
  password: fasldkflk423mkj4k24jk242
  host: localhost
  port: 5432
  pool:
    min_connections: 1
    max_connections: 10
    idle_timeout: 300

production:
  name: news_aggregator_prod
  user: news_admin_prod  
  password: fasldkflk423mkj4k24jk242
  host: localhost
  port: 5432
  pool:
    min_connections: 5
    max_connections: 50
    idle_timeout: 300

shared:
  application_name: news_aggregator
  connect_timeout: 10
  statement_timeout: 30000
  idle_in_transaction_session_timeout: 60000
  ssl_mode: disable


# Project Structure
project structure looks like this:

news_dagster-etl/
└── news_aggregator/
    ├── alembic/             # Alembic directory (if initialized already)
    ├── db_scripts/
    │   ├── models/         # Directory for SQLAlchemy models (to be created)
    │   ├── schemas/
    │   │   └── create_schemas.sql # Your SQL schema file
    │   └── db_utils.py     # Database utility functions (for config loading)
    ├── config/
    │   └── database/
    │       └── alembic_migration_guide.md # Documentation (to be created)
    └── ... (other project files)

# Explore database schema creted for building SQLAlchemy
Use read_file to read the content of /home/opc/news_dagster-etl/news_aggregator/db_scripts/schemas/create_schemas.sql.
We will then analyze the content of create_schemas.sql and outline the SQLAlchemy models.

This schema should not be deployed - its purpose is to serve code first approacha and we need to use it to build SQLAlchemy models in
/home/opc/news_dagster-etl/news_aggregator/db_scripts/schemas/create_schemas.sql: We will first read the contents of your create_schemas.sql file to thoroughly understand the database schema you have designed. This will involve identifying:

Tables and their names
Columns for each table, including names, data types, and constraints (like NOT NULL, UNIQUE, etc.)
Primary key columns
Foreign key relationships between tables
Define SQLAlchemy Models (based on create_schemas.sql): Based on our understanding of create_schemas.sql, we will then outline the SQLAlchemy models. This will involve:


# Creating a Python class for each table identified in create_schemas.sql
For each class, defining SQLAlchemy Column objects that correspond to the columns in the SQL tables, ensuring we match data types and constraints.
Defining primary keys and foreign key relationships using SQLAlchemy's relationship features.
We will aim to create a models.py file in /home/opc/news_dagster-etl/news_aggregator/db_scripts/models/ that accurately represents the schema in create_schemas.sql using SQLAlchemy model definitions.


# Configure Alembic for SQLAlchemy

 After defining the models, we will configure Alembic to work with SQLAlchemy, as outlined in the detailed steps previously. This includes:

Installing SQLAlchemy and Alembic - done by user.
Configuring alembic.ini with database connection details (using db_utils.py if possible).

File: config/database/database_config.yaml - EXPLORE THIS FILE SICE IT HAS DEV AND PROD DATABASE CREDENTIALS WHICH YOU NEED. 

Identify Database Connection Details: You'll need to know how your project connects to the database.

Inspect db_utils.py: We need to read /home/opc/news_dagster-etl/news_aggregator/db_scripts/db_utils.py to understand how database configurations are loaded (e.g., from environment variables, config files). This will be crucial for connecting to the database to create it and later for Alembic configuration.

Configuring alembic/env.py to point to our SQLAlchemy models and set up the database connection.
Generate Initial Migration: We will use Alembic's autogenerate feature to create the initial migration script by comparing our SQLAlchemy models to the (empty) database.

Apply Migrations and Document: Finally, we will apply the migration to create the database schema and document the Alembic migration process in alembic_migration_guide.md.



After outlining the models, we can proceed with creating models.py and configuring Alembic.

# COMPLETED BY USER
Clean Up Existing Alembic Installations
pip install sqlalchemy alembic psycopg2-binary pyyaml
rm -rf /home/opc/alembic
rm -rf /home/opc/news_dagster-etl/news_aggregator/alembic
