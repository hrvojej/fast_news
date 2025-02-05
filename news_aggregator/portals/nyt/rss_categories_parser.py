#!/usr/bin/env python3
"""
NYT RSS Categories Parser
Fetches and stores NYT RSS feed categories using SQLAlchemy ORM.
"""

import requests
from bs4 import BeautifulSoup
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import re
from typing import List, Dict, Optional
from uuid import UUID

from news_aggregator.db_scripts.models.models import Base, create_portal_category_model
from news_aggregator.db_scripts.db_context import DatabaseContext

class NYTRSSCategoriesParser:
    """Parser for NYT RSS feed categories"""
    
    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=None):
        """
        Initialize the parser
        
        Args:
            portal_id: UUID of the NYT portal in news_portals table
            env: Environment to use (dev/prod)
        """
        self.portal_id = portal_id
        self.env = env
        self.base_url = "https://www.nytimes.com/rss"
        self.NYTCategory = category_model

    def get_session(self) -> sessionmaker:
        """Create a database session"""
        with DatabaseContext(self.env) as db_context:
            engine = sa.create_engine(db_context.get_connection())
            Session = sessionmaker(bind=engine)
            return Session()

    @staticmethod
    def clean_ltree(value: str) -> str:
        """
        Convert category title into valid ltree path
        
        Args:
            value: String to convert
            
        Returns:
            Cleaned string suitable for ltree path
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
        Fetch and parse NYT RSS feeds
        
        Returns:
            List of dictionaries containing RSS feed metadata
        
        Raises:
            requests.exceptions.RequestException: If RSS feeds cannot be fetched
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
        Parse RSS feeds and extract category metadata
        
        Args:
            rss_links: List of RSS feed URLs to parse
            
        Returns:
            List of dictionaries containing category data
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
                    }
                    
                    # Extract path components for ltree
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
        Store categories using SQLAlchemy ORM
        
        Args:
            categories: List of category dictionaries to store
            
        Raises:
            Exception: If categories cannot be stored
        """
        session = self.get_session()
        
        try:
            print("Storing categories in database...")
            for category_data in categories:
                # Create category instance
                category = self.NYTCategory(
                    name=category_data['title'],
                    slug=self.clean_ltree(category_data['title']),
                    portal_id=self.portal_id,
                    path=category_data['path'],
                    level=category_data['level'],
                    description=category_data['description'],
                    link=category_data['link'],
                    is_active=True
                )
                
                # Add to session
                session.add(category)
            
            # Commit changes
            session.commit()
            print(f"Successfully stored {len(categories)} categories")
        
        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to store categories: {e}")
        
        finally:
            session.close()

    def run(self):
        """
        Main method to fetch and store NYT categories
        """
        try:
            # Fetch and parse RSS feeds
            categories = self.fetch_rss_feeds()
            
            # Store categories
            self.store_categories(categories)
            
            print("Category processing completed successfully")
        
        except Exception as e:
            print(f"Error processing categories: {e}")
            raise

def main():
    """
    Script entry point
    """
    # TODO: Get portal_id from configuration
    NYT_PORTAL_ID = "your-nyt-portal-uuid"  # Replace with actual UUID
    
    try:
        parser = NYTRSSCategoriesParser(portal_id=NYT_PORTAL_ID)
        parser.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()