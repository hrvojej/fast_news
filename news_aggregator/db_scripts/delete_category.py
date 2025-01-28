from news_dagster_etl.news_aggregator.db_scripts.db_context import DatabaseContext
from news_dagster_etl.news_aggregator.db_scripts.data_adapter import CategoryDataAdapter

def delete_category(category_id: int, portal_prefix: str):
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()
            category_adapter = CategoryDataAdapter(conn)

            deleted_rows = category_adapter.delete(portal_prefix, category_id)

            if deleted_rows > 0:
                print(f"Category with id {category_id} deleted successfully.")
            else:
                print(f"Category with id {category_id} not found or failed to delete.")

    except Exception as e:
        print(f"Error deleting category: {e}")

if __name__ == '__main__':
    # Example usage:
    category_id_to_delete = 1
    portal_prefix = "public" # Assuming 'public' is the portal_prefix for the portal you are working with.
    delete_category(category_id_to_delete, portal_prefix)
