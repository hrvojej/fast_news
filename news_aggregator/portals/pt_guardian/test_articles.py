import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

def clean_text(text: str) -> str:
    """Normalize whitespace and trim the text."""
    if text:
        return re.sub(r'\s+', ' ', text.strip())
    return ''

def extract_articles(html: str, base_url: str, category_id) -> list:
    soup = BeautifulSoup(html, 'html.parser')
    articles = []
    
    # Find all divs that represent an article card.
    # Here we use a lambda to check if the "card" word is present in the element's class.
    for card in soup.find_all("div", class_=lambda c: c and "card" in c.split()):
        # Look for the anchor that contains the headline text.
        # In these examples the anchor with class "container__link" contains the headline.
        link_elem = card.find("a", class_=lambda c: c and "container__link" in c)
        if not link_elem or not link_elem.get("href"):
            continue
        relative_url = link_elem.get("href").strip()
        full_url = urljoin(base_url, relative_url)
        
        # Look for the span that holds the headline title.
        title_elem = card.find("span", class_="container__headline-text")
        if not title_elem:
            continue
        title = clean_text(title_elem.get_text())
        if not title or len(title) < 10:
            continue
        
        # Optionally extract image URL if available.
        image_url = None
        # This example shows an <img> tag with class "image__dam-img" somewhere inside the card.
        img_elem = card.find("img", class_="image__dam-img")
        if img_elem:
            image_url = (img_elem.get("data-src") or img_elem.get("src"))
            if image_url:
                image_url = image_url.strip()
        
        # Build the article dictionary to match your model.
        article_data = {
            'title': title,
            'url': full_url,
            'guid': full_url,
            'category_id': category_id,
            'description': None,  # Optionally, extract a summary if available.
            'content': None,      # Full content would require a second fetch.
            'author': [],         # Author extraction could be added if the HTML provided it.
            'pub_date': None,     # Likewise, extract publication date if present.
            'keywords': [],       # You can later use NLP or meta tags for keywords.
            'reading_time_minutes': max(1, round(len(title.split()) / 200)),
            'language_code': 'en',
            'image_url': image_url,
            'sentiment_score': 0.0,
            'share_count': 0,
            'view_count': 0,
            'comment_count': 0
        }
        articles.append(article_data)
    return articles

if __name__ == '__main__':
    # Use a realistic User-Agent header to ensure the full content is returned.
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/85.0.4183.83 Safari/537.36")
    }
    
    # CNN's Business/Tech category page.
    base_url = "https://edition.cnn.com/business/tech"
    category_id = "dummy-uuid-for-example"  # Replace with your actual category UUID.
    
    response = requests.get(base_url, headers=headers, timeout=30)
    response.raise_for_status()
    html_content = response.text
    
    articles = extract_articles(html_content, base_url, category_id)
    
    if articles:
        for art in articles:
            print("Title:", art["title"])
            print("URL:", art["url"])
            print("Image URL:", art["image_url"])
            print("-" * 40)
    else:
        print("No articles found. The content might be loaded dynamically.")
