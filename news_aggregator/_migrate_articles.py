"""
One-time migration: move existing flat article HTML files into category subdirectories
and update article_html_file_location in the DB accordingly.
"""
import os, sys, shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nlp', 'summarizer'))
from summarizer_html import get_subfolder_from_url

import psycopg2

DB_CONN = "host=localhost port=5432 dbname=news_aggregator_dev user=news_admin_dev password=fasldkflk423mkj4k24jk242"
ARTICLES_DIR = os.path.join(os.path.dirname(__file__), 'frontend', 'web', 'articles')
SCHEMA = "pt_reuters"

conn = psycopg2.connect(DB_CONN)
cur = conn.cursor()

# Get all articles with their URL and current file location
cur.execute(f"""
    SELECT article_id, url, article_html_file_location
    FROM {SCHEMA}.articles
    WHERE article_html_file_location IS NOT NULL
      AND article_html_file_location != ''
""")

rows = cur.fetchall()
print(f"Found {len(rows)} articles to migrate")

moved = 0
skipped = 0
errors = 0

for article_id, url, current_location in rows:
    subfolder = get_subfolder_from_url(url)
    filename = os.path.basename(current_location)
    new_location = f"{subfolder}/{filename}" if subfolder else filename

    if current_location == new_location:
        skipped += 1
        continue

    # Move file on disk
    old_path = os.path.join(ARTICLES_DIR, current_location.replace('/', os.sep))
    new_dir = os.path.join(ARTICLES_DIR, subfolder) if subfolder else ARTICLES_DIR
    new_path = os.path.join(new_dir, filename)

    if not os.path.exists(old_path):
        print(f"  SKIP (file not found): {old_path}")
        skipped += 1
        continue

    os.makedirs(new_dir, exist_ok=True)
    shutil.move(old_path, new_path)

    # Update DB
    cur.execute(f"""
        UPDATE {SCHEMA}.articles
        SET article_html_file_location = %s
        WHERE article_id = %s
    """, (new_location, article_id))

    print(f"  MOVED: {current_location} -> {new_location}")
    moved += 1

conn.commit()
cur.close()
conn.close()

print(f"\nDone: {moved} moved, {skipped} skipped, {errors} errors")
