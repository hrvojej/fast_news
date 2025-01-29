import argparse
from db_scripts.db_context import DatabaseContext
from db_scripts.data_adapter import Article
from db_scripts.generic_db_crud import generic_create, generic_read

def verify_article(env: str):
    try:
        with DatabaseContext(env=env) as db_context:
            conn = db_context.get_connection()
            
            article_info = {
                "url": "https://example.com/test-article",
                "portal_id": 1,
                "category_id": 1,
                "title": "Test Article",
                "description": "This is a test article.",
                "body": "Test article body content goes here.",
                "published_at": "2024-01-28 10:00:00",
                "scraped_at": "2024-01-28 10:00:00"
            }
            portal_prefix = "public"
            table_name = f"{portal_prefix}.articles"
            created_article = generic_create(env, table_name, article_info)

            if created_article:
                print(f"Article created successfully: {created_article}")
                
                condition = {'article_id': created_article['article_id']}
                retrieved_article = generic_read(env, table_name, condition=condition)
                if retrieved_article:
                    print("Retrieved article from database:")
                    print(retrieved_article[0])
                    print("Verification successful.")
                else:
                    print("Failed to retrieve article from database.")
            else:
                print("Failed to create article.")

    except Exception as e:
        print(f"Error creating or verifying article: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Verify article creation.")
    parser.add_argument("-env", type=str, default="dev", help="Environment to use (dev or prod)")
    args = parser.parse_args()
    verify_article(args.env)
