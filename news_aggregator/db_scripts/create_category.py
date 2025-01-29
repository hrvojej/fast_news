from db_scripts.db_context import DatabaseContext
from db_scripts.data_adapter import Category, CategoryDataAdapter

import argparse

def create_category(category_data: dict, env: str, schema: str):
    try:
        with DatabaseContext(env=env) as db_context:
            conn = db_context.get_connection()
            category_adapter = CategoryDataAdapter(conn)

            category = Category(**category_data)
            created_category = category_adapter.create(schema, category)

            if created_category:
                print(f"Category created successfully: {created_category}")
            else:
                print("Failed to create category.")

    except Exception as e:
        print(f"Error creating category: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create a new category.")
    parser.add_argument("-env", type=str, default="dev", help="Environment to use (dev or prod)")
    parser.add_argument("-schema", type=str, default="public", help="Schema to use")
    parser.add_argument("-portal_id", type=int, default=1, help="Portal ID to use")
    args = parser.parse_args()

    # Example usage:
    category_info = {
        "name": "Technology",
        "slug": "technology",
        "portal_id": args.portal_id,
        "path": "technology",
        "level": 1,
        "title": "Technology News",
        "description": "The latest technology news and updates.",
        "category_id": 1
    }
    create_category(category_info, args.env, args.schema)
