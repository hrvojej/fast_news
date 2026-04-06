from db_scripts.db_context import DatabaseContext
db = DatabaseContext()
rows = db.fetch_all("SELECT url, article_html_file_location, summary_article_gemini_title FROM pt_reuters.articles WHERE article_html_file_location != '' LIMIT 10")
for r in rows:
    url = r.get('url', '')
    # Extract category from Reuters URL like /sports/... /business/...
    parts = url.replace('https://www.reuters.com/', '').split('/')
    cat = parts[0] if parts else '?'
    title = (r.get('summary_article_gemini_title') or 'N/A')[:50]
    print(f"{cat:20s} | {title}")
