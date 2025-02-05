from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import uuid
import re
from bs4 import BeautifulSoup

def scrape_nyt_article_with_selenium(url, schema="public"):
    # Configure Selenium to run in headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # You can also add a user agent
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        driver.get(url)
        # Wait for the page to fully render if necessary
        time.sleep(3)  # Adjust the sleep time as needed

        # Get page source after JavaScript has rendered
        page_source = driver.page_source
    finally:
        driver.quit()
    
    # Now parse with BeautifulSoup
    soup = BeautifulSoup(page_source, "html.parser")

    # Generate a random UUID for the article_id
    article_id = uuid.uuid4()

    # Title extraction
    meta_title = soup.find("meta", property="og:title")
    title = meta_title.get("content").strip() if meta_title else (soup.title.string.strip() if soup.title else None)

    guid = url

    meta_description = soup.find("meta", attrs={"name": "description"})
    description = meta_description.get("content").strip() if meta_description else None

    article_body = soup.find("section", {"name": "articleBody"})
    if article_body:
        paragraphs = article_body.find_all("p")
        content = "\n".join(p.get_text(strip=True) for p in paragraphs)
    else:
        content = None

    meta_byline = soup.find("meta", attrs={"name": "byl"})
    if meta_byline:
        raw_authors = meta_byline.get("content").strip().lstrip("By ").strip()
        author = [a.strip() for a in raw_authors.split(" and ")]
    else:
        author = None

    meta_pub_date = soup.find("meta", property="article:published_time")
    pub_date = meta_pub_date.get("content").strip() if meta_pub_date else None

    category_match = re.search(r"https://www.nytimes.com/\d{4}/\d{2}/\d{2}/([^/]+)/", url)
    category = category_match.group(1) if category_match else None

    if category:
        import uuid
        category_id = uuid.uuid5(uuid.NAMESPACE_DNS, category)
    else:
        category_id = None

    meta_keywords = soup.find("meta", attrs={"name": "news_keywords"})
    if meta_keywords:
        keywords = [kw.strip() for kw in meta_keywords.get("content").split(",")]
    else:
        keywords = None

    reading_time_minutes = None

    html_tag = soup.find("html")
    language_code = html_tag.get("lang") if html_tag and html_tag.has_attr("lang") else None

    meta_image = soup.find("meta", property="og:image")
    image_url = meta_image.get("content").strip() if meta_image else None

    sentiment_score = None
    share_count = 0
    view_count = 0
    comment_count = 0

    print("article_id:", article_id)
    print("title:", title)
    print("url:", url)
    print("guid:", guid)
    print("description:", description)
    print("content:", content)
    print("author:", author)
    print("pub_date:", pub_date)
    print("category_id:", category_id)
    print("keywords:", keywords)
    print("reading_time_minutes:", reading_time_minutes)
    print("language_code:", language_code)
    print("image_url:", image_url)
    print("sentiment_score:", sentiment_score)
    print("share_count:", share_count)
    print("view_count:", view_count)
    print("comment_count:", comment_count)

if __name__ == "__main__":
    url = "https://www.nytimes.com/2025/02/01/opinion/rfk-kennedy-vaccines.html"
    scrape_nyt_article_with_selenium(url)
