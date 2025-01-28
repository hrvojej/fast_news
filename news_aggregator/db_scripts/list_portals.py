import psycopg2
from data_adapter import PortalDataAdapter
from db_utils import get_db_connection

def list_portals():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to the database.")
        return

    portal_adapter = PortalDataAdapter(conn)

    portals = portal_adapter.list_all()

    if portals:
        print("List of Portals:")
        for portal in portals:
            print(f"  ID: {portal.portal_id}, Name: {portal.portal_name}, Domain: {portal.portal_domain}, Bucket Prefix: {portal.bucket_prefix}")
    else:
        print("No portals found in the database.")

    conn.close()

if __name__ == "__main__":
    list_portals()
