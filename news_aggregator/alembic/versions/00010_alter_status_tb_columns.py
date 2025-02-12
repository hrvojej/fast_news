"""
Alter column types for article_status table in all portal schemas

Revision ID: 0010
Revises: 0009
Create Date: 2025-02-12 14:00:00
"""
from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection

revision = '0010'
down_revision = '0009'

def upgrade():
    connection: Connection = op.get_bind()
    # Fetch all portal schemas from public.news_portals
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Altering columns in {portal_schema}.article_status")
        
        # Alter status_type to varchar(10)
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.article_status
            ALTER COLUMN status_type TYPE varchar(10);
        """))
        
        # Alter status to boolean, using a cast to convert the existing value
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.article_status
            ALTER COLUMN status TYPE boolean USING (status::boolean);
        """))
    print("Upgrade complete: column types altered.")


def downgrade():
    connection: Connection = op.get_bind()
    # Fetch all portal schemas from public.news_portals
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Reverting columns in {portal_schema}.article_status")
        
        # Revert status_type to its previous type (e.g. varchar(50))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.article_status
            ALTER COLUMN status_type TYPE varchar(50);
        """))
        
        # Revert status back to varchar(50); use a CASE statement to convert boolean to a text representation
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.article_status
            ALTER COLUMN status TYPE varchar(50) USING (CASE WHEN status THEN 'true' ELSE 'false' END);
        """))
    print("Downgrade complete: column types reverted.")
