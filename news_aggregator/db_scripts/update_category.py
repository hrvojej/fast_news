from news_dagster_etl.news_aggregator.db_scripts.db_context import DatabaseContext
from news_dagster_etl.news_aggregator.db_scripts.data_adapter import Category, CategoryDataAdapter
from news_dagster_etl.news_aggregator.db_scripts.generic_db_crud import generic_update
from news_dagster_etl.news_aggregator.db_scripts.generic_db_crud import generic_read

def update_category(category_id: int, category_data: dict, portal_prefix: str):
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()

            table_name = f"{portal_prefix}.categories"
            condition = {'category_id': category_id}

            # Fetch existing category data using generic_read
            existing_category_data = generic_read(conn, table_name, condition)
            if not existing_category_data:
                print(f"Category with id {category_id} not found.")
                return

            updated_category_data = {**existing_category_data, **category_data}

            rows_updated = generic_update(conn, table_name, updated_category_data, condition)

            if rows_updated:
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
