import psycopg2
import argparse
from db_scripts.db_utils import get_db_connection
from db_scripts.generic_db_crud import generic_delete
from db_scripts.db_context import DatabaseContext

def delete_portal(env: str):
    with DatabaseContext(env=env) as db_context:
        conn = db_context.get_connection()
        if not conn:
            print("Failed to connect to the database.")
            return

    portal_id = input("Enter portal ID to delete: ")
    table_name = "news_portals"
    condition = {'portal_id': portal_id}
    deleted_portal = generic_delete(conn, table_name, condition)

    if deleted_portal:
        print(f"Portal with ID: {portal_id} deleted successfully.")
    else:
        print(f"Failed to delete portal with ID: {portal_id}. Portal not found or deletion failed.")

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete a portal.")
    parser.add_argument("-env", type=str, default="dev", help="Environment to use (dev or prod)")
    args = parser.parse_args()
    delete_portal(args.env)
