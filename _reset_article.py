import sys, os
sys.path.insert(0, 'news_aggregator')
from db_scripts.db_context import DatabaseContext
from sqlalchemy import text

db = DatabaseContext.get_instance('dev')
with db.session() as s:
    # Reset the article so it can be claimed again
    s.execute(text(
        "UPDATE pt_bbc.article_status SET html_processing_status = false "
        "WHERE url = (SELECT url FROM pt_bbc.articles WHERE article_id = :aid)"
    ), {"aid": "194bce4c-be26-4773-b808-6bca2d37b868"})
    # Clear the file location
    s.execute(text(
        "UPDATE pt_bbc.articles SET article_html_file_location = NULL "
        "WHERE article_id = :aid"
    ), {"aid": "194bce4c-be26-4773-b808-6bca2d37b868"})
    s.commit()
    print("Article reset for re-processing")
