import psycopg2
from data_adapter import PortalDataAdapter
from db_utils import get_db_connection

def delete_portal():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to the database.")
        return

    portal_adapter = PortalDataAdapter(conn)

    portal_id = input("Enter portal ID to delete: ")

    deleted = portal_adapter.delete(portal_id)

    if deleted:
        print(f"Portal with ID: {portal_id} deleted successfully.")
    else:
        print(f"Failed to delete portal with ID: {portal_id}. Portal not found or deletion failed.")

    conn.close()

if __name__ == "__main__":
    delete_portal()
