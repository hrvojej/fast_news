
# ###################################### article question ############################
I need to create 
reuters news article parser from sitemap links.

So you need to iterate over pages from 1  to 50 one by one, pause 5-9 seconds between pages:
https://www.reuters.com/sitemap/2025-02/07/1/
...
to the last
https://www.reuters.com/sitemap/2025-02/07/50/

and look for:

# Find all article elements in pages like this:
<li class="story-card__tpl-common__1Q7br story-card__tpl-feed-media-on-right-image-landscape-big__34KGa story-card__transition-no-description-for-mobile__2uxm- feed-list__card__Praes" data-are-authors="false" data-testid="FeedListItem"><p data-testid="Description" class="text__text__1FZLe text__dark-grey__3Ml43 text__regular__2N1Xr text__small__1kGq2 body__full_width__ekUdw body__small_body__2vQyf story-card__area-description__2JiBp">Prime Minister Justin Trudeau on Friday said U.S. President Donald Trump's talk about absorbing Canada "is a real thing" and is linked to the country's rich natural resources, a government source said.</p><div class="title__title__29EfZ story-card__area-headline__2ZAtJ"><a data-testid="TitleLink" href="/world/americas/canada-could-face-long-term-political-challenges-with-us-says-trudeau-2025-02-07/" class="text__text__1FZLe text__inherit-color__3208F text__inherit-font__1Y8w3 text__inherit-size__1DZJi link__link__3Ji6W link__underline_on_hover__2zGL4"><span data-testid="TitleHeading" class="text__text__1FZLe text__inherit-color__3208F text__medium__1kbOh text__heading_6__1qUJ5 heading__base__2T28j heading__heading_6__RtD9P title__heading__s7Jan">Trudeau says Trump talk of absorbing Canada is 'a real thing', says source</span></a></div><div class="kicker-date__kicker-date__2VBU4 story-card__area-kicker-date__2Fgfs"><span data-testid="KickerLabel" class="text__text__1FZLe text__dark-grey__3Ml43 text__light__1nZjX text__extra_small__1Mw6v label__label__f9Hew label__kicker__RW9aE"><span data-testid="KickerText" class="text__text__1FZLe text__inherit-color__3208F text__inherit-font__1Y8w3 text__inherit-size__1DZJi">World</span></span><span data-testid="Text" class="text__text__1FZLe text__dark-grey__3Ml43 text__regular__2N1Xr text__default__UPMUu">·</span><time data-testid="DateLineText" class="text__text__1FZLe text__dark-grey__3Ml43 text__light__1nZjX text__extra_small__1Mw6v" style="display: block;">a few seconds ago</time></div><div class=" image-container no-caption story-card__area-media__3P0qM" data-testid="MediaImage"><a data-testid="MediaImageLink" aria-hidden="true" tabindex="-1" href="/world/americas/canada-could-face-long-term-political-challenges-with-us-says-trudeau-2025-02-07/" class="text__text__1FZLe text__dark-grey__3Ml43 text__medium__1kbOh text__default__UPMUu link__link__3Ji6W link__underline_default__2prE_ image__container__30dKZ story-card__image-link__3uceD"><div data-testid="Image" class="image story-card__image__2XuiU"><div class="styles__image-container__3hkY5 styles__cover__34fjZ styles__center_center__1CNY5 styles__apply-ratio__1JYnB styles__transition__3hwoa" style="--aspect-ratio: 1.5;"><img sizes="(min-width: 1024px) 680px, 100vw" srcset="https://www.reuters.com/resizer/v2/KFIEGKRPNFKJPBEZGTC3NGV64A.jpg?auth=81eb307a404ed4825c03f7f4aee8d14dea11ee8582a23520760d7c6fe6cb3255&amp;width=120&amp;quality=80 120w,https://www.reuters.com/resizer/v2/KFIEGKRPNFKJPBEZGTC3NGV64A.jpg?auth=81eb307a404ed4825c03f7f4aee8d14dea11ee8582a23520760d7c6fe6cb3255&amp;width=240&amp;quality=80 240w,https://www.reuters.com/resizer/v2/KFIEGKRPNFKJPBEZGTC3NGV64A.jpg?auth=81eb307a404ed4825c03f7f4aee8d14dea11ee8582a23520760d7c6fe6cb3255&amp;width=480&amp;quality=80 480w,https://www.reuters.com/resizer/v2/KFIEGKRPNFKJPBEZGTC3NGV64A.jpg?auth=81eb307a404ed4825c03f7f4aee8d14dea11ee8582a23520760d7c6fe6cb3255&amp;width=960&amp;quality=80 960w,https://www.reuters.com/resizer/v2/KFIEGKRPNFKJPBEZGTC3NGV64A.jpg?auth=81eb307a404ed4825c03f7f4aee8d14dea11ee8582a23520760d7c6fe6cb3255&amp;width=1200&amp;quality=80 1200w" src="https://www.reuters.com/resizer/v2/KFIEGKRPNFKJPBEZGTC3NGV64A.jpg?auth=81eb307a404ed4825c03f7f4aee8d14dea11ee8582a23520760d7c6fe6cb3255&amp;width=1200&amp;quality=80" width="5000" height="3335" alt="Economic summit in Canada"></div></div></a></div></li>


Leave default or empty fields that are not present. 

Try to find all elements from our model like images, publication date (pub_date), author and others.


Make sure you use all fields from article model as is.
In case script is run several times it should not make dupes , just insert new records if there is need for that.


# NYT Article Parser Example -from this example take only  core other functionalities -model and database management etc. All other stuff should be done as explained by me. 
"""
NYT RSS Articles Parser
Fetches and stores NYT RSS feed articles using SQLAlchemy ORM.
"""

import sys
import os
from datetime import datetime
from typing import List, Dict
from uuid import UUID
import requests
from bs4 import BeautifulSoup
import argparse
from sqlalchemy import text

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)
    
# Category model creation
from db_scripts.models.models import create_portal_category_model
NYTCategory = create_portal_category_model("pt_nyt")

# Import the dynamic model factory
from db_scripts.models.models import create_portal_article_model

# Create the dynamic article model for NYT portal
NYTArticle = create_portal_article_model("pt_nyt")

def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """Fetches the portal_id from news_portals table."""
    from db_scripts.db_context import DatabaseContext
    db_context = DatabaseContext.get_instance(env)
    with db_context.session() as session:
        result = session.execute(
            text("SELECT portal_id FROM public.news_portals WHERE portal_prefix = :prefix"),
            {'prefix': portal_prefix}
        ).fetchone()
        if result:
            return result[0]
        raise Exception(f"Portal with prefix '{portal_prefix}' not found.")

class NYTRSSArticlesParser:
    """Parser for NYT RSS feed articles"""

    def __init__(self, portal_id: UUID, env: str = 'dev', article_model=None):
        self.portal_id = portal_id
        self.env = env
        self.NYTArticle = article_model

    def get_session(self):
        """Get database session from DatabaseContext."""
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        return db_context.session().__enter__()

    def parse_article(self, item: BeautifulSoup, category_id: UUID) -> Dict:
        """Parse a single NYT RSS item."""
        # Required fields
        title = item.find('title').text.strip() if item.find('title') else 'Untitled'
        link = item.find('link').text.strip() if item.find('link') else 'https://www.nytimes.com'
        guid = item.find('guid').text.strip() if item.find('guid') else link  # Use URL as fallback GUID
        
        # Optional fields with defaults
        description = item.find('description').text.strip() if item.find('description') else None
        content = description  # Using description as content fallback
        pub_date_str = item.find('pubDate').text.strip() if item.find('pubDate') else None
        pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z') if pub_date_str else datetime.utcnow()
        
        # Arrays with empty list defaults
        authors = [creator.text.strip() for creator in item.find_all('dc:creator')] or []
        keywords = [cat.text.strip() for cat in item.find_all('category') 
                   if cat.text.strip() and len(cat.text.strip()) > 2] or []
        
        # Get image information
        image_url = None
        media_contents = item.find_all('media:content')
        if media_contents:
            valid_media = [(m.get('url'), int(m.get('width'))) 
                          for m in media_contents 
                          if m.get('width') and m.get('width').isdigit()]
            if valid_media:
                image_url = max(valid_media, key=lambda x: x[1])[0]

        # Calculate reading time (rough estimate: 200 words per minute)
        text_content = f"{title} {description or ''} {content or ''}"
        word_count = len(text_content.split())
        reading_time = max(1, round(word_count / 200))

        return {
            # Required fields
            'title': title,
            'url': link,
            'guid': guid,
            'category_id': category_id,
            
            # Optional fields
            'description': description,
            'content': content,
            'author': authors,
            'pub_date': pub_date,
            'keywords': keywords,
            'reading_time_minutes': reading_time,
            'language_code': 'en',
            'image_url': image_url,
            'sentiment_score': 0.0,  # Neutral sentiment as default
            'share_count': 0,
            'view_count': 0,
            'comment_count': 0
        }

    def fetch_and_store_articles(self):
        """Fetch and store articles from all RSS feeds."""
        print("Starting fetch_and_store_articles...")
        session = self.get_session()
        print("Executing categories query...")
        try:
            # Get all active categories
            categories = session.execute(
                text("""
                    SELECT category_id, atom_link 
                    FROM pt_nyt.categories 
                    WHERE is_active = true AND atom_link IS NOT NULL 
                """)
            ).fetchall()
            print(f"Found {len(categories)} categories")

            for category_id, atom_link in categories:
                print("Processing category:", category_id)
                try:
                    response = requests.get(atom_link, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'xml')
                    
                    for item in soup.find_all('item'):
                        article_data = self.parse_article(item, category_id)
                        existing = session.query(self.NYTArticle).filter(
                            self.NYTArticle.guid == article_data['guid']
                        ).first()

                        if not existing:
                            article = self.NYTArticle(**article_data)
                            session.add(article)
                        elif existing.pub_date != article_data['pub_date']:
                            for key, value in article_data.items():
                                setattr(existing, key, value)                 

                        print(f"Processing article: {article_data['title']}")
                    
                    session.commit()
                    
                except Exception as e:
                    print(f"Error processing feed {atom_link}: {e}")
                    session.rollback()
                    continue

        except Exception as e:
            print(f"Error in fetch_and_store_articles: {e}")
            session.rollback()
            raise
        finally:
            session.close()


    def run(self):
        """Main method to fetch and store NYT articles."""
        try:
            self.fetch_and_store_articles()
            print("Article processing completed successfully")
        except Exception as e:
            print(f"Error processing articles: {e}")
            raise

def main():
    """Script entry point."""
    argparser = argparse.ArgumentParser(description="NYT RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_nyt", env=args.env)
        parser = NYTRSSArticlesParser(portal_id=portal_id, env=args.env, article_model=NYTArticle)
        parser.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()

# Model from model.py - you need to use this models to store data in db
class NewsPortal(Base):
    __tablename__ = 'news_portals'
    __table_args__ = (
        Index('idx_portal_status', 'active_status'),
        Index('idx_portal_prefix', 'portal_prefix'),
        {'schema': 'public'}
    )

    portal_id = sa.Column(UUID(as_uuid=True), primary_key=True,
                          server_default=sa.text("gen_random_uuid()"))
    portal_prefix = sa.Column(sa.String(50), nullable=False, unique=True)
    name = sa.Column(sa.String(255), nullable=False)
    base_url = sa.Column(sa.Text, nullable=False)
    rss_url = sa.Column(sa.Text)
    scraping_enabled = sa.Column(sa.Boolean, server_default=sa.text("true"))
    portal_language = sa.Column(sa.String(50))
    timezone = sa.Column(sa.String(50), server_default=sa.text("'UTC'"))
    active_status = sa.Column(sa.Boolean, server_default=sa.text("true"))
    scraping_frequency_minutes = sa.Column(sa.Integer, server_default=sa.text("60"))
    last_scraped_at = sa.Column(TIMESTAMP(timezone=True))


# ───────────────────────────────────── Dynamic Portal Models (Categories & Articles) ─────────────────────────────

def create_portal_category_model(schema: str):
    return type(
        f'Category_{schema}',
        (Base,),
        {
            '__tablename__': 'categories',
            '__table_args__': (
                UniqueConstraint('slug', 'portal_id', name=f'uq_{schema}_categories_slug_portal_id'),
                Index(f'idx_{schema}_category_path', 'path', postgresql_using='btree'),
                Index(f'idx_{schema}_category_portal', 'portal_id'),
                {'schema': schema}
            ),
            'category_id': sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            'name': sa.Column(sa.String(255), nullable=False),
            'slug': sa.Column(sa.String(255), nullable=False),
            'portal_id': sa.Column(UUID(as_uuid=True), nullable=False),
            'path': sa.Column(sa.Text, nullable=False),
            'level': sa.Column(sa.Integer, nullable=False),
            'description': sa.Column(sa.Text),
            'link': sa.Column(sa.Text),
            'atom_link': sa.Column(sa.Text),
            'is_active': sa.Column(sa.Boolean, server_default=sa.text("true"))
        }
    )

def create_portal_article_model(schema: str):
    return type(
        f'Article_{schema}',
        (Base,),
        {
            '__tablename__': 'articles',
           '__table_args__': (
                Index(f'idx_{schema}_articles_pub_date', 'pub_date'),
                Index(f'idx_{schema}_articles_category', 'category_id'),
                sa.ForeignKeyConstraint(
                    ['category_id'], 
                    [f'{schema}.categories.category_id'],
                    name=f'fk_{schema}_article_category'
                ),
                {'schema': schema}
            ),
            'article_id': sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            'title': sa.Column(sa.Text, nullable=False),
            'url': sa.Column(sa.Text, nullable=False),
            'guid': sa.Column(sa.Text, unique=True),
            'description': sa.Column(sa.Text),
            'content': sa.Column(sa.Text),
            'author': sa.Column(ARRAY(sa.Text)),
            'pub_date': sa.Column(TIMESTAMP(timezone=True)),            
            'category_id': sa.Column(UUID(as_uuid=True), nullable=False),            
            'keywords': sa.Column(ARRAY(sa.Text)),
            'reading_time_minutes': sa.Column(sa.Integer),
            'language_code': sa.Column(sa.String(10)),
            'image_url': sa.Column(sa.Text),
            'sentiment_score': sa.Column(sa.Float, CheckConstraint('sentiment_score BETWEEN -1 AND 1')),
            'share_count': sa.Column(sa.Integer, server_default=sa.text("0")),
            'view_count': sa.Column(sa.Integer, server_default=sa.text("0")),
            'comment_count': sa.Column(sa.Integer, server_default=sa.text("0"))
        }
    )

Also for opening pages you need to open them with random 8-17 seconds delay with this method:
import pychrome
import time
import threading

def main():
   try:
       browser = pychrome.Browser(url="http://127.0.0.1:9222")
       tab = browser.new_tab()
       
       def handle_exception(msg):
           print(f"Debug: {msg}")
       
       tab.set_listener("exception", handle_exception)
       tab.start()
       
       tab.Page.enable()
       tab.Runtime.enable()
       
       url = "https://edition.cnn.com/2025/02/04/politics/cia-workforce-buyouts/index.html"
       tab.Page.navigate(url=url)
       
       time.sleep(5)
       
       clean_html_js = """
       function cleanHTML() {
           const elements = document.querySelectorAll('script, style, iframe, link, meta');
           elements.forEach(el => el.remove());
           return document.documentElement.outerHTML;
       }
       cleanHTML();
       """
       
       result = tab.Runtime.evaluate(expression=clean_html_js)
       html_content = result["result"]["value"]

       with open("cnn.html", "w", encoding="utf-8") as f:
           f.write(html_content)
           
   except Exception as e:
       print(f"Error: {e}")
   finally:
       tab.stop()
       browser.close_tab(tab)

if __name__ == "__main__":
   main()




# Important!!!
Make sure you ignore how sample script is using web scraping, you must not use BeautifulSoup or requests. You need to use Chromium dev browser as explained. Make sure there are pauses between requests. 