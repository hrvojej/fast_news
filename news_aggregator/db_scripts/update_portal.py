from news_dagster_etl.news_aggregator.db_scripts.data_adapter import Portal, PortalDataAdapter
from news_dagster_etl.news_aggregator.db_scripts.db_utils import get_db_connection
from news_dagster_etl.news_aggregator.db_scripts.generic_db_crud import generic_update

def update_portal():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to the database.")
        return

    portal_id = input("Enter portal ID to update: ")
    portal_name = input("Enter new portal name: ")
    portal_domain = input("Enter new portal domain: ")
    bucket_prefix = input("Enter new bucket prefix: ")

    portal = Portal(portal_id=portal_id, portal_name=portal_name, portal_domain=portal_domain, bucket_prefix=bucket_prefix)

    condition = {'portal_id': portal_id}
    updated_portal = generic_update(conn, "news_portals", portal.__dict__, condition)

    if updated_portal:
        print(f"Portal '{portal.portal_name}' with ID: {updated_portal['portal_id']} updated successfully.")
    else:
        print(f"Failed to update portal with ID: {portal_id}.")

    conn.close()

if __name__ == "__main__":
    update_portal()
