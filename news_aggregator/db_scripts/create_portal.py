import psycopg2
from data_adapter import Portal, PortalDataAdapter
from db_utils import get_db_connection

def create_portal():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to the database.")
        return

    portal_adapter = PortalDataAdapter(conn)

    portal_name = input("Enter portal name: ")
    portal_domain = input("Enter portal domain: ")
    bucket_prefix = input("Enter bucket prefix: ")

    portal = Portal(portal_id=None, portal_name=portal_name, portal_domain=portal_domain, bucket_prefix=bucket_prefix) # portal_id will be auto-generated

    created_portal = portal_adapter.create(portal)

    if created_portal:
        print(f"Portal '{created_portal.portal_name}' created successfully with ID: {created_portal.portal_id}")
    else:
        print("Failed to create portal.")

    conn.close()

if __name__ == "__main__":
    create_portal()
