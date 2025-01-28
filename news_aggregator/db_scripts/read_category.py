from news_dagster_etl.news_aggregator.db_scripts.db_context import DatabaseContext
from news_dagster_etl.news_aggregator.db_scripts.data_adapter import CategoryDataAdapter

def read_category(category_id: int, portal_prefix: str):
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()
            category_adapter = CategoryDataAdapter(conn)

            category = category_adapter.get_by_id(portal_prefix, category_id)

            if category:
                print(f"Category details: {category}")
            else:
                print(f"Category with id {category_id} not found.")

    except Exception as e:
        print(f"Error reading category: {e}")

if __name__ == '__main__':
    # Example usage:
    category_id_to_read = 1
    portal_prefix = "public" # Assuming 'public' is the portal_prefix for the portal you are working with.
    read_category(category_id_to_read, portal_prefix)
