I need to parse articles from:
https://www.aljazeera.com/xml/rss/all.xml

Portal prefix: pt_aljazeera

# Example source code of RSS category, first few lines with several item elements:
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/"
	
	xmlns:georss="http://www.georss.org/georss"
	xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#"
	>
	<channel>
		<atom:link href="https://www.aljazeera.com/xml/rss/all.xml" rel="self" type="application/rss+xml"/>
		<title>Al Jazeera &#8211; Breaking News, World News and Video from Al Jazeera</title>
		<link>https://www.aljazeera.com</link>
		<managingEditor>apps.support@aljazeera.net (Apps Support)</managingEditor>
		<webMaster>apps.support@aljazeera.net (Apps Support)</webMaster>
		<description>Breaking News, World News and Video from Al Jazeera</description>
		<copyright>© 2025 Al Jazeera Media Network</copyright>
		<lastBuildDate>Thu, 06 Feb 2025 23:41:21 +0000</lastBuildDate>
		<language>en</language>
		<image>
			<url>https://www.aljazeera.com/images/logo_aje.png</url>
			<title>Al Jazeera &#8211; Breaking News, World News and Video from Al Jazeera</title>
			<link>https://www.aljazeera.com</link>
			<description>Breaking News, World News and Video from Al Jazeera</description>
		</image>
		<generator>https://wordpress.org/?v=6.7.1</generator>
<site xmlns="com-wordpress:feed-additions:1">213497099</site>			<item>
				<link>https://www.aljazeera.com/sports/2025/2/6/torres-hattrick-leads-barcelona-copa-del-rey-rout-at-valencia?traffic_source=rss</link>
				<title>Torres hat-trick leads Barcelona Copa del Rey rout at Valencia</title>
				<description><![CDATA[Ferran Torres scores three of Barcelona&#039;s first four goals in a 5-0 Copa del Rey quarterfinal win at Valencia.]]></description>
				<pubDate>Thu, 06 Feb 2025 23:41:21 +0000</pubDate>
				<category>Sport</category>
				<guid isPermaLink="false">https://www.aljazeera.com/?t=1738882009</guid>
				<post-id xmlns="com-wordpress:feed-additions:1">3494040</post-id>			</item>
					<item>
				<link>https://www.aljazeera.com/news/2025/2/6/us-judge-delays-trump-buyout-offer-meant-to-thin-out-public-servants?traffic_source=rss</link>
				<title>US judge delays Trump buyout offer meant to thin out public servants</title>
				<description><![CDATA[Trump and allies such as billionaire Elon Musk have carried out blitz campaign meant to thin the government workforce. ]]></description>
				<pubDate>Thu, 06 Feb 2025 23:17:37 +0000</pubDate>
				<category>News</category>
				<guid isPermaLink="false">https://www.aljazeera.com/?t=1738873949</guid>
				<post-id xmlns="com-wordpress:feed-additions:1">3494040</post-id>			</item>



Leave default or empty fields that are not present. 

In case there i pub_date or similar field to fill in - never put timestamp there if data is not present in source parsed. Just leave that date field empty. 

Make sure you use all fields from article model as is, do not omit nor add any other fields. 
In case script is run several times it should not make dupes , just insert new records if there is need for that.

category_id field should be looked up in category table based on <category>Sport</category> from RSS - this is actually "name" field in Category table. 
SELECT category_id, name FROM pt_aljazeera.categories
limit 2
"9ee233bc-71e9-4567-9bc9-890469e15ba3"	"News"
"3257a678-59a2-46b9-bf8f-d4cb125019ca"	"Africa"

# NYT Article Parser Example - follow this example to implement all other functionalities except extraction logic - 
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

