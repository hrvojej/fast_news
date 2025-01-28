from news_dagster_etl.news_aggregator.db_scripts.db_context import DatabaseContext
from news_dagster_etl.news_aggregator.db_scripts.data_adapter import ArticleDataAdapter

def list_articles(portal_prefix: str, filters: dict = None):
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()
            article_adapter = ArticleDataAdapter(conn)

            articles = article_adapter.get_all(portal_prefix, filters=filters)

            if articles:
                print("List of articles:")
                for article in articles:
                    print(article)
            else:
                print("No articles found.")

    except Exception as e:
        print(f"Error listing articles: {e}")

if __name__ == '__main__':
    # Example usage:
    portal_prefix = "public" # Assuming 'public' is the portal_prefix for the portal you are working with.
    filters = {"category_id": 1} # Example filter by category_id
    list_articles(portal_prefix, filters)
