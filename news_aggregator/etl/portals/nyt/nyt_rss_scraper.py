from typing import List, Dict, Any
from bs4 import BeautifulSoup
from etl.common.base.base_rss_scraper import BaseRssScraper
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class NYTRssScraper(BaseRssScraper):
    def __init__(self):
        super().__init__(
            portal_id=1,  # NYT portal_id from news_portals table
            portal_name="New York Times",
            portal_domain="nytimes.com"
        )
        self.rss_list_url = "https://www.nytimes.com/rss"

    def get_categories(self) -> List[Dict[str, Any]]:
        """Dynamically discover and parse NYT RSS categories."""
        categories = []
        try:
            # Fetch RSS listing page
            response = self.request_manager.get(self.rss_list_url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all RSS feed links
            rss_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'rss' in href and href.endswith('.xml'):
                    rss_links.append(href)

            # Process each discovered RSS feed
            unique_rss_links = list(set(rss_links))
            for rss_url in unique_rss_links:
                try:
                    soup = self.get_feed_content(rss_url)
                    if not soup:
                        continue

                    channel = soup.find('channel')
                    if not channel:
                        continue

                    metadata = self.parse_feed_metadata(channel)
                    if not metadata['title']:
                        continue

                    # Clean title and generate slug
                    name = metadata['title'].replace(' - The New York Times', '')
                    slug = self.generate_slug(rss_url, name)

                    categories.append({
                        'name': name,
                        'slug': slug,
                        'portal_id': self.portal_id,
                        'path': self.clean_ltree(name),
                        'level': len(slug.split('_')),
                        'title': metadata['title'],
                        'link': metadata['link'],
                        'atom_link': rss_url,
                        'description': metadata['description'],
                        'language': metadata['language'],
                        'copyright_text': metadata.get('copyright'),
                        'last_build_date': metadata.get('last_build_date'),
                        'pub_date': metadata.get('pub_date'),
                        'image_title': metadata.get('image_title'),
                        'image_url': metadata.get('image_url'),
                        'image_link': metadata.get('image_link')
                    })

                except Exception as e:
                    logger.error(f"Error processing NYT RSS feed {rss_url}: {str(e)}")

        except Exception as e:
            logger.error(f"Error fetching NYT RSS listing page: {str(e)}")

        return categories

    def generate_slug(self, url: str, title: str) -> str:
        """Generate a unique slug from URL and title."""
        if not url:
            return self.clean_ltree(title or 'unknown')
            
        try:
            path = url.split('//')[1].split('/')[1:]
            path = [p for p in path if p and p not in ['index.html', 'rss', 'services', 'xml']]
            if not path:
                return self.clean_ltree(title or 'unknown')
            return '_'.join(path)
        except:
            return self.clean_ltree(title or 'unknown')

    def clean_ltree(self, value: str) -> str:
        """Clean string for use as ltree path."""
        if not value:
            return "unknown"
        value = value.replace(">", ".").strip()
        value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
        value = re.sub(r"[._]{2,}", ".", value)
        return value.strip("._")
