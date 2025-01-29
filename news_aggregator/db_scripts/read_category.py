from news_dagster_etl.news_aggregator.db_scripts.db_context import DatabaseContext
from news_dagster_etl.news_aggregator.db_scripts.data_adapter import CategoryDataAdapter
from news_dagster_etl.news_aggregator.db_scripts.generic_db_crud import generic_read

def read_category(category_id: int, portal_prefix: str):
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()

            table_name = f"{portal_prefix}.categories"
            condition = {'category_id': category_id}
            category_data = generic_read(conn, table_name, condition)

            if category_data:
                category = CategoryDataAdapter.from_dict(category_data) # Assuming you have a from_dict method in CategoryDataAdapter or a similar way to instantiate Category from dict
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
