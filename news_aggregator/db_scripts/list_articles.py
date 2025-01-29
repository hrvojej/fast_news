import argparse
from db_scripts.db_context import DatabaseContext
from db_scripts.generic_db_crud import generic_read

def list_articles(portal_prefix: str, filters: dict = None, env: str = 'dev'):
    try:
        with DatabaseContext(env=env) as db_context:
            conn = db_context.get_connection()
            table_name = f"{portal_prefix}.articles"
            articles = generic_read(conn, table_name, condition=filters)

            if articles:
                print("List of articles:")
                for article in articles:
                    print(article)
            else:
                print("No articles found.")

    except Exception as e:
        print(f"Error listing articles: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List articles.")
    parser.add_argument("-env", type=str, default="dev", help="Environment to use (dev or prod)")
    args = parser.parse_args()

    # Example usage:
    portal_prefix = "public" # Assuming 'public' is the portal_prefix for the portal you are working with.
    filters = {"category_id": 1} # Example filter by category_id
    list_articles(portal_prefix, filters, args.env)
