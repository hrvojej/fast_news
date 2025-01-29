import argparse
from db_scripts.db_context import DatabaseContext
from db_scripts.generic_db_crud import generic_delete

def delete_category(category_id: int, portal_prefix: str, env: str):
    try:
        with DatabaseContext(env=env) as db_context:
            conn = db_context.get_connection()
            table_name = f"{portal_prefix}.categories"
            condition = {'category_id': category_id}
            deleted_category = generic_delete(conn, table_name, condition)

            if deleted_category:
                print(f"Category with id {category_id} deleted successfully.")
            else:
                print(f"Category with id {category_id} not found or failed to delete.")

    except Exception as e:
        print(f"Error deleting category: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Delete a category.")
    parser.add_argument("-env", type=str, default="dev", help="Environment to use (dev or prod)")
    args = parser.parse_args()

    # Example usage:
    category_id_to_delete = 1
    portal_prefix = "public" # Assuming 'public' is the portal_prefix for the portal you are working with.
    delete_category(category_id_to_delete, portal_prefix, args.env)
