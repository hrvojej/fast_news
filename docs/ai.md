# Categories question
I need to parse RSS categories from:
abcnews

base url:
https://abcnews.go.com/Site/page/rss-feeds-3520115

RSS feeds are stored in that page in elements like:
<a target="_blank" href="https://feeds.abcnews.com/abcnews/usheadlines"><img src="https://s.abcnews.com/images/technology/rss_chicklet.jpg"></a>
Leave default or empty fields that are not present. 

In case there i pub_date or similar field to fill in - never put timestamp there if data is not present in source parsed. Just leave that date field empty. 

portal prefix:
pt_abc

Make sure you use all fields from model.py :
def create_portal_categorymodel(schema: str):
    return type(
        f'Category{schema}',
        (Base,),
        {
            'tablename': 'categories',
            'table_args': (
                UniqueConstraint('slug', 'portalid', name=f'uq{schema}_categories_slug_portalid'),
                Index(f'idx{schema}_category_path', 'path', postgresqlusing='btree'),
                Index(f'idx{schema}_category_portal', 'portal_id'),
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

In case script is run several times it should not make dupes , just insert new records if there is need for that.

Look at example of 
NYT Category Parser and make similar:
# path: news_dagster-etl/news_aggregator/portals/nyt/rss_categories_parser.py
"""
NYT RSS Categories Parser
Fetches and stores NYT RSS feed categories using SQLAlchemy ORM.
"""

import sys
import os

# Add the package root (news_aggregator) to sys.path.
current_dir = os.path.dirname(os.path.abspath(__file__))
# news_aggregator is two directories up from portals/nyt/
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

import argparse
import requests
from bs4 import BeautifulSoup
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import re
from typing import List, Dict
from uuid import UUID
from sqlalchemy import text

# Import the dynamic model factory from your models file.
from db_scripts.models.models import create_portal_category_model

# Create the dynamic category model for the NYT portal.
# Here the schema is "pt_nyt" as used in your queries.
NYTCategory = create_portal_category_model("pt_nyt")


def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """
    Fetches the portal_id from the news_portals table for the given portal_prefix.

    Args:
        portal_prefix: The prefix of the portal (e.g., 'pt_nyt')
        env: The environment to use ('dev' or 'prod')

    Returns:
        The UUID of the portal.

    Raises:
        Exception: If no portal with the given prefix is found.
    """
    # Import DatabaseContext from your db_context module.
    from db_scripts.db_context import DatabaseContext
    db_context = DatabaseContext.get_instance(env)
    with db_context.session() as session:
        result = session.execute(
            text("SELECT portal_id FROM public.news_portals WHERE portal_prefix = :prefix"),
            {'prefix': portal_prefix}
        ).fetchone()
        if result:
            return result[0]
        else:
            raise Exception(f"Portal with prefix '{portal_prefix}' not found.")

class NYTRSSCategoriesParser:
    """Parser for NYT RSS feed categories"""

    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=None):
        """
        Initialize the parser

        Args:
            portal_id: UUID of the NYT portal in news_portals table
            env: Environment to use (dev/prod)
            category_model: SQLAlchemy ORM model for categories (if applicable)
        """
        self.portal_id = portal_id
        self.env = env
        self.base_url = "https://www.nytimes.com/rss"
        self.NYTCategory = category_model

    def get_session(self):
        """
        Obtain a database session from the DatabaseContext.
        """
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        # Directly enter the session context to get a session object.
        return db_context.session().__enter__()

    @staticmethod
    def clean_ltree(value: str) -> str:
        """
        Convert category title into valid ltree path.
        """
        if not value:
            return "unknown"

        # Replace "U.S." with "U_S"
        value = value.replace('U.S.', 'U_S')
        # Replace slashes with dots
        value = value.replace('/', '.').replace('\\', '.')
        # Replace arrow indicators with dots
        value = value.replace('>', '.').strip()
        # Convert to lowercase
        value = value.lower()
        # Replace any non-alphanumeric characters (except dots) with underscores
        value = re.sub(r'[^a-z0-9.]+', '_', value)
        # Replace multiple dots or underscores with a single one
        value = re.sub(r'[._]{2,}', '.', value)
        # Remove leading/trailing dots or underscores
        return value.strip('._')

    def fetch_rss_feeds(self) -> List[Dict]:
        """
        Fetch and parse NYT RSS feeds.
        """
        try:
            print(f"Fetching RSS feeds from {self.base_url}")
            response = requests.get(self.base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            rss_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'rss' in href and href.endswith('.xml'):
                    rss_links.append(href)

            unique_rss_links = list(set(rss_links))
            print(f"Found {len(unique_rss_links)} unique RSS feeds")
            return self.parse_rss_feeds(unique_rss_links)

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch RSS feeds: {e}")

    def parse_rss_feeds(self, rss_links: List[str]) -> List[Dict]:
        """
        Parse RSS feeds and extract category metadata.
        """
        categories = []
        for rss_url in rss_links:
            try:
                print(f"Processing RSS feed: {rss_url}")
                response = requests.get(rss_url)
                response.raise_for_status()
                rss_soup = BeautifulSoup(response.content, 'xml')

                channel = rss_soup.find('channel')
                if channel:
                    category = {
                        'title': channel.find('title').text if channel.find('title') else None,
                        'link': channel.find('link').text if channel.find('link') else None,
                        'description': channel.find('description').text if channel.find('description') else None,
                        'language': channel.find('language').text if channel.find('language') else None,
                        'atom_link': channel.find('atom:link', href=True)['href'] if channel.find('atom:link', href=True) else None
                    }

                    # Create ltree path and level.
                    path = self.clean_ltree(category['title']) if category['title'] else 'unknown'
                    category['path'] = path
                    category['level'] = len(path.split('.'))

                    categories.append(category)

            except Exception as e:
                print(f"Error processing RSS feed {rss_url}: {e}")
                continue

        return categories
    
    def store_categories(self, categories: List[Dict]):
        """
        Store categories using SQLAlchemy ORM.
        """
        session = self.get_session()

        try:
            print("Storing categories in database...")
            count_added = 0
            for category_data in categories:
                slug = self.clean_ltree(category_data['title']) if category_data['title'] else 'unknown'

                existing = session.query(self.NYTCategory).filter(
                    self.NYTCategory.slug == slug,
                    self.NYTCategory.portal_id == self.portal_id
                ).first()
                if existing:
                    print(f"Category with slug '{slug}' already exists. Skipping insertion.")
                    continue

                category = self.NYTCategory(
                    name=category_data['title'],
                    slug=slug,
                    portal_id=self.portal_id,
                    path=category_data['path'],
                    level=category_data['level'],
                    description=category_data['description'],
                    link=category_data['link'],
                    atom_link=category_data['atom_link'],
                    is_active=True
                )
                session.add(category)
                count_added += 1

            session.commit()
            print(f"Successfully stored {count_added} new categories")

        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to store categories: {e}")

        finally:
            session.close()
    
    def run(self):
        """
        Main method to fetch and store NYT categories.
        """
        try:
            categories = self.fetch_rss_feeds()
            self.store_categories(categories)
            print("Category processing completed successfully")
        except Exception as e:
            print(f"Error processing categories: {e}")
            raise


def main():
    """
    Script entry point.
    """
    import argparse
    # Import Base from your models file to inspect the metadata
    from db_scripts.models.models import Base
    print("Registered tables in metadata:", Base.metadata.tables.keys())

    argparser = argparse.ArgumentParser(description="NYT RSS Categories Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment to load data (default: dev)"
    )
    args = argparser.parse_args()

    portal_prefix = "pt_nyt"  # The portal prefix.
    try:
        portal_id = fetch_portal_id_by_prefix(portal_prefix, env=args.env)
        print(f"Using portal_id: {portal_id} for portal_prefix: {portal_prefix}")

        parser_instance = NYTRSSCategoriesParser(portal_id=portal_id, env=args.env, category_model=NYTCategory)
        parser_instance.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()



# ###################################### article question ############################
I similar way how nyt article parser (below) is created now I need to create 
abc article parser from categories atom_link url

So you need to iterate over 
SELECT atom_link FROM pt_abc.categories

Example of atom_link returned:
https://feeds.abcnews.com/abcnews/primetimeheadlines

# Example source code of RSS category, first few lines with several item elements:
This XML file does not appear to have any style information associated with it. The document tree is shown below.
<rss xmlns:media="http://search.yahoo.com/mrss/" xmlns:abcnews="http://abcnews.com/content/" version="2.0">
<channel>
<title>ABC News: Entertainment</title>
<link>http://abcnews.go.com</link>
<description/>
<image>
<title>ABC News: Entertainment</title>
<url>https://s.abcnews.com/images/site/abcnews_google_rss_logo.png</url>
<link>http://abcnews.go.com</link>
</image>
<item>
<media:thumbnail url="https://s.abcnews.com/images/Entertainment/wirestory_feacbe92d0d147b01b6005b5e3d91abb_4x3_384.jpg" width="384" height="288"/>
<media:thumbnail url="https://s.abcnews.com/images/Entertainment/wirestory_feacbe92d0d147b01b6005b5e3d91abb_4x3_144.jpg" width="144" height="108"/>
<media:thumbnail url="https://s.abcnews.com/images/Entertainment/wirestory_feacbe92d0d147b01b6005b5e3d91abb_4x3_384.jpg" width="384" height="288"/>
<media:thumbnail url="https://s.abcnews.com/images/Entertainment/wirestory_feacbe92d0d147b01b6005b5e3d91abb_16x9_240.jpg" width="240" height="135"/>
<media:thumbnail url="https://s.abcnews.com/images/Entertainment/wirestory_feacbe92d0d147b01b6005b5e3d91abb_4x3_608.jpg" width="608" height="456"/>
<media:thumbnail url="https://s.abcnews.com/images/Entertainment/wirestory_feacbe92d0d147b01b6005b5e3d91abb_16x9_992.jpg" width="992" height="558"/>
<media:thumbnail url="https://s.abcnews.com/images/Entertainment/wirestory_feacbe92d0d147b01b6005b5e3d91abb_16x9_1600.jpg" width="1600" height="900"/>
<media:keywords>1</media:keywords>
<title>
<![CDATA[ John Irving's 'Queen Esther' returns readers to setting of 'The Cider House Rules' ]]>
</title>
<link>
<![CDATA[ https://abcnews.go.com/Entertainment/wireStory/john-irvings-queen-esther-returns-readers-setting-cider-118523918 ]]>
</link>
<guid>
<![CDATA[ https://abcnews.go.com/Entertainment/wireStory/john-irvings-queen-esther-returns-readers-setting-cider-118523918 ]]>
</guid>
<pubDate>Thu, 06 Feb 2025 08:42:28 -0500</pubDate>
<description>
<![CDATA[ In John Irving&rsquo;s next book, the author is returning to St_ Cloud&rsquo;s, Maine, and to the orphanage made famous in his acclaimed &ldquo;The Cider House Rules.&rdquo; ]]>
</description>
<category>Entertainment</category>
</item>




Leave default or empty fields that are not present. 

In case there i pub_date or similar field to fill in - never put timestamp there if data is not present in source parsed. Just leave that date field empty. 

portal prefix:
pt_abc



Make sure you use all fields from article model as is.
In case script is run several times it should not make dupes , just insert new records if there is need for that.


# NYT Article Parser Example
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

# Model from model.py - you need to use them
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

