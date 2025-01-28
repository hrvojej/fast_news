import psycopg2
from data_adapter import Portal, PortalDataAdapter
from db_utils import get_db_connection

def update_portal():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to the database.")
        return

    portal_adapter = PortalDataAdapter(conn)

    portal_id = input("Enter portal ID to update: ")
    portal_name = input("Enter new portal name: ")
    portal_domain = input("Enter new portal domain: ")
    bucket_prefix = input("Enter new bucket prefix: ")

    portal = Portal(portal_id=portal_id, portal_name=portal_name, portal_domain=portal_domain, bucket_prefix=bucket_prefix)

    updated_portal = portal_adapter.update(portal_id, portal)

    if updated_portal:
        print(f"Portal '{updated_portal.portal_name}' with ID: {updated_portal.portal_id} updated successfully.")
    else:
        print(f"Failed to update portal with ID: {portal_id}.")

    conn.close()

if __name__ == "__main__":
    update_portal()
