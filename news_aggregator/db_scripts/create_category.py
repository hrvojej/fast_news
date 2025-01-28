from news_dagster_etl.news_aggregator.db_scripts.db_context import DatabaseContext
from news_dagster_etl.news_aggregator.db_scripts.data_adapter import Category, CategoryDataAdapter

def create_category(category_data: dict, portal_prefix: str):
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()
            category_adapter = CategoryDataAdapter(conn)

            category = Category(**category_data)
            created_category = category_adapter.create(portal_prefix, category)

            if created_category:
                print(f"Category created successfully: {created_category}")
            else:
                print("Failed to create category.")

    except Exception as e:
        print(f"Error creating category: {e}")

if __name__ == '__main__':
    # Example usage:
    category_info = {
        "name": "Technology",
        "slug": "technology",
        "portal_id": 1, 
        "path": "/technology",
        "level": 1,
        "title": "Technology News",
        "description": "The latest technology news and updates."
    }
    portal_prefix = "public" # Assuming 'public' is the portal_prefix for the portal you are working with.
    create_category(category_info, portal_prefix)
