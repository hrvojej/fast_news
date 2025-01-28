from news_dagster_etl.news_aggregator.db_scripts.db_context import DatabaseContext
from news_dagster_etl.news_aggregator.db_scripts.data_adapter import Category, CategoryDataAdapter

def update_category(category_id: int, category_data: dict, portal_prefix: str):
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()
            category_adapter = CategoryDataAdapter(conn)

            existing_category = category_adapter.get_by_id(portal_prefix, category_id)
            if not existing_category:
                print(f"Category with id {category_id} not found.")
                return

            updated_category_info = {**existing_category._asdict(), **category_data}
            updated_category = Category(**updated_category_info)

            rows_updated = category_adapter.update(portal_prefix, category_id, updated_category)

            if rows_updated > 0:
                print(f"Category with id {category_id} updated successfully.")
            else:
                print(f"Failed to update category with id {category_id}.")

    except Exception as e:
        print(f"Error updating category: {e}")

if __name__ == '__main__':
    # Example usage:
    category_id_to_update = 1
    portal_prefix = "public" # Assuming 'public' is the portal_prefix for the portal you are working with.
    updated_category_info = {
        "name": "Updated Technology",
        "description": "Updated description for technology news."
    }
    update_category(category_id_to_update, updated_category_info, portal_prefix)
