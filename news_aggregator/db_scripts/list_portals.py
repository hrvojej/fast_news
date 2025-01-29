import psycopg2
from news_dagster_etl.news_aggregator.db_scripts.db_utils import get_db_connection
from news_dagster_etl.news_aggregator.db_scripts.generic_db_crud import generic_read

def list_portals():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to the database.")
        return

    table_name = "news_portals"
    portals = generic_read(conn, table_name)

    if portals:
        print("List of Portals:")
        for portal in portals:
            print(f"  ID: {portal['portal_id']}, Name: {portal['portal_name']}, Domain: {portal['portal_domain']}, Bucket Prefix: {portal['bucket_prefix']}")
    else:
        print("No portals found in the database.")

    conn.close()

if __name__ == "__main__":
    list_portals()
