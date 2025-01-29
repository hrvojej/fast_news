from news_dagster_etl.news_aggregator.db_scripts.db_context import DatabaseContext
from news_dagster_etl.news_aggregator.db_scripts.generic_db_crud import generic_update, generic_read

def update_article(article_id: int, article_data: dict, portal_prefix: str):
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()
            table_name = f"{portal_prefix}.articles"
            condition = {'article_id': article_id}
            existing_article = generic_read(conn, table_name, condition=condition)
            if not existing_article:
                print(f"Article with id {article_id} not found.")
                return
            
            updated_article_info = {**existing_article[0], **article_data}
            rows_updated = generic_update(conn, table_name, updated_article_info, condition)

            if rows_updated:
                print(f"Article with id {article_id} updated successfully.")
            else:
                print(f"Failed to update article with id {article_id}.")

    except Exception as e:
        print(f"Error updating article: {e}")

if __name__ == '__main__':
    # Example usage:
    article_id_to_update = 1
    portal_prefix = "public" # Assuming 'public' is the portal_prefix for the portal you are working with.
    updated_article_info = {
        "title": "Updated Example Article Title",
        "description": "Updated description for the example article."
    }
    update_article(article_id_to_update, updated_article_info, portal_prefix)
