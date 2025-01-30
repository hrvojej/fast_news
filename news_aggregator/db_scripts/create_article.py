import argparse
from db_scripts.db_context import DatabaseContext
from db_scripts.data_adapter import Article, ArticleDataAdapter
from db_scripts.generic_db_crud import generic_create

def create_article(article_data: dict, env: str, schema: str):
    try:
        with DatabaseContext(env=env) as db_context:
            conn = db_context.get_connection()
            article = Article(**article_data)
            table_name = "articles"
            created_article = generic_create(env, schema, table_name, article.__dict__)

            if created_article:
                print(f"Article created successfully: {created_article}")
            else:
                print("Failed to create article.")

    except Exception as e:
        print(f"Error creating article: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create a new article.")
    parser.add_argument("-env", type=str, default="dev", help="Environment to use (dev or prod)")
    parser.add_argument("-schema", type=str, default="public", help="Schema to use")
    args = parser.parse_args()

    # Example usage:
    article_info = Article(
        url="https://example.com/article1",
        category_id=1,
        title="Example Article",
        description="This is an example article.",
        guid="some-guid",
        author=["John Doe"],
        pub_date="2024-01-28 10:00:00",
        keywords=["example", "article"],
        image_url="https://example.com/image.jpg",
        image_width=600,
        image_credit="Example Credit",
        article_id=1
    )
    create_article(article_info.__dict__, args.env, args.schema)
