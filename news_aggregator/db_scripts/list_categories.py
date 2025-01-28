from news_dagster_etl.news_aggregator.db_scripts.db_context import DatabaseContext
from news_dagster_etl.news_aggregator.db_scripts.data_adapter import CategoryDataAdapter

def list_categories(portal_prefix: str):
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()
            category_adapter = CategoryDataAdapter(conn)

            categories = category_adapter.get_all(portal_prefix)

            if categories:
                print("List of categories:")
                for category in categories:
                    print(category)
            else:
                print("No categories found.")

    except Exception as e:
        print(f"Error listing categories: {e}")

if __name__ == '__main__':
    # Example usage:
    portal_prefix = "public" # Assuming 'public' is the portal_prefix for the portal you are working with.
    list_categories(portal_prefix)
