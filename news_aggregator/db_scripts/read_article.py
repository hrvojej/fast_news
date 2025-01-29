from news_dagster_etl.news_aggregator.db_scripts.db_context import DatabaseContext
from news_dagster_etl.news_aggregator.db_scripts.generic_db_crud import generic_read

def read_article(article_id: int, portal_prefix: str):
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()
            table_name = f"{portal_prefix}.articles"
            condition = {'article_id': article_id}
            article = generic_read(conn, table_name, condition=condition)

            if article:
                print(f"Article details: {article[0]}")
            else:
                print(f"Article with id {article_id} not found.")

    except Exception as e:
        print(f"Error reading article: {e}")

if __name__ == '__main__':
    # Example usage:
    article_id_to_read = 1
    portal_prefix = "public" # Assuming 'public' is the portal_prefix for the portal you are working with.
    read_article(article_id_to_read, portal_prefix)
