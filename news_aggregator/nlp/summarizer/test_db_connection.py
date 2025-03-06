# test_db_connection.py
import os
import sys

# Import path configuration first
from summarizer_path_config import configure_paths
configure_paths()

# Now import db_scripts
from db_scripts.db_context import DatabaseContext
from sqlalchemy import text

# Get database context instance
db_context = DatabaseContext.get_instance('dev')

# Test connection by attempting to create a session and execute a simple query
try:
    with db_context.session() as session:
        # Use the text() function to properly format the SQL query
        result = session.execute(text("SELECT 1 AS connection_test")).scalar()
        if result == 1:
            print("Database connection successful!")
            # Print connection details for verification
            print(f"Environment: {db_context.env}")
            print(f"Connection string: {db_context.get_connection_string().replace(':'+db_context.get_connection_string().split(':')[2].split('@')[0]+'@', ':***@')}")
        else:
            print(f"Database connection test returned unexpected result: {result}")
except Exception as e:
    print(f"Database connection failed: {e}")
    import traceback
    traceback.print_exc()