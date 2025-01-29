import argparse
from db_scripts.db_context import DatabaseContext
from db_scripts.generic_db_crud import generic_read

def list_categories(portal_prefix: str, env: str):
    try:
        with DatabaseContext(env=env) as db_context:
            conn = db_context.get_connection()
            table_name = f"{portal_prefix}.categories"
            categories = generic_read(conn, table_name)

            if categories:
                print("List of categories:")
                for category in categories:
                    print(category)
            else:
                print("No categories found.")

    except Exception as e:
        print(f"Error listing categories: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List categories.")
    parser.add_argument("-env", type=str, default="dev", help="Environment to use (dev or prod)")
    args = parser.parse_args()

    # Example usage:
    portal_prefix = "public" # Assuming 'public' is the portal_prefix for the portal you are working with.
    list_categories(portal_prefix, args.env)
