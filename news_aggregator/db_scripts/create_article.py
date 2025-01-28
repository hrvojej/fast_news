from news_dagster_etl.news_aggregator.db_scripts.db_context import DatabaseContext
from news_dagster_etl.news_aggregator.db_scripts.data_adapter import Article, ArticleDataAdapter

def create_article(article_data: dict, portal_prefix: str):
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()
            article_adapter = ArticleDataAdapter(conn)

            article = Article(**article_data)
            created_article = article_adapter.create(portal_prefix, article)

            if created_article:
                print(f"Article created successfully: {created_article}")
            else:
                print("Failed to create article.")

    except Exception as e:
        print(f"Error creating article: {e}")

if __name__ == '__main__':
    # Example usage:
    article_info = {
        "url": "https://example.com/article1",
        "portal_id": 1,
        "category_id": 1,
        "title": "Example Article",
        "description": "This is an example article.",
        "body": "Article body content goes here.",
        "published_at": "2024-01-28 10:00:00",
        "scraped_at": "2024-01-28 10:00:00"
    }
    portal_prefix = "public" # Assuming 'public' is the portal_prefix for the portal you are working with.
    create_article(article_info, portal_prefix)
