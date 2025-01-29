from news_dagster_etl.news_aggregator.db_scripts.data_adapter import Portal, PortalDataAdapter
from news_dagster_etl.news_aggregator.db_scripts.db_utils import get_db_connection
from news_dagster_etl.news_aggregator.db_scripts.generic_db_crud import generic_create

def create_portal():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to the database.")
        return

    portal_name = input("Enter portal name: ")
    portal_domain = input("Enter portal domain: ")
    bucket_prefix = input("Enter bucket prefix: ")

    portal = Portal(portal_id=None, portal_name=portal_name, portal_domain=portal_domain, bucket_prefix=bucket_prefix)

    created_portal = generic_create(conn, "news_portals", portal.__dict__)

    if created_portal:
        print(f"Portal '{portal.portal_name}' created successfully with ID: {created_portal['portal_id']}")
    else:
        print("Failed to create portal.")

    conn.close()

if __name__ == "__main__":
    create_portal()
