from news_dagster_etl.news_aggregator.db_scripts.db_context import DatabaseContext
from news_dagster_etl.news_aggregator.db_scripts.data_adapter import ArticleDataAdapter

def delete_article(article_id: int, portal_prefix: str):
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()
            article_adapter = ArticleDataAdapter(conn)

            deleted_rows = article_adapter.delete(portal_prefix, article_id)

            if deleted_rows > 0:
                print(f"Article with id {article_id} deleted successfully.")
            else:
                print(f"Article with id {article_id} not found or failed to delete.")

    except Exception as e:
        print(f"Error deleting article: {e}")

if __name__ == '__main__':
    # Example usage:
    article_id_to_delete = 1
    portal_prefix = "public" # Assuming 'public' is the portal_prefix for the portal you are working with.
    delete_article(article_id_to_delete, portal_prefix)
