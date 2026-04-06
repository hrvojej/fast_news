import sys
sys.path.insert(0, 'news_aggregator')
from db_scripts.db_context import DatabaseContext
from sqlalchemy import text

db = DatabaseContext.get_instance('dev')
with db.session() as s:
    r = s.execute(text(
        "SELECT article_id, title, LENGTH(content) as content_len, "
        "LEFT(content, 500) as content_preview "
        "FROM pt_bbc.articles WHERE article_id = :aid"
    ), {"aid": "194bce4c-be26-4773-b808-6bca2d37b868"}).fetchone()
    if r:
        print(f"ID: {r[0]}")
        print(f"Title: {r[1]}")
        print(f"Content length: {r[2]}")
        print(f"Content preview:")
        print(r[3])
    else:
        print("Article not found")
