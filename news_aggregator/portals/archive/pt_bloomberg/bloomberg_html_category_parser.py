import sys
import os
import re
import time
from typing import List, Dict
from uuid import UUID
import requests
from bs4 import BeautifulSoup
from sqlalchemy import text

# Import pychrome for fetching page content via a real browser session
import pychrome
import json

def patched_recv_loop(self):
    """Patched version of _recv_loop that skips empty/malformed messages."""
    while True:
        try:
            message_json = self._socket.recv()
            if not message_json:
                continue
            try:
                message = json.loads(message_json)
            except json.JSONDecodeError:
                # Ignore empty or malformed JSON messages
                continue
            # Process the message as usual
            self._handle_message(message)
        except Exception as e:
            # Optionally, log the error and break out of the loop if desired
            print(f"Error in patched _recv_loop: {e}")
            break

# Apply the monkey patch:
pychrome.Tab._recv_loop = patched_recv_loop


# Set up package root (adjust if needed)
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import the category model factory and create the Bloomberg model
from db_scripts.models.models import create_portal_category_model
BloombergCategory = create_portal_category_model("pt_bloomberg")


def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
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


class BloombergCategoriesParser:
    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=None):
        self.portal_id = portal_id
        self.env = env
        # Use the Europe edition URL as base
        self.base_url = "https://www.bloomberg.com/europe"
        self.CategoryModel = category_model
        # The headers are not used with pychrome, but kept in case you need them elsewhere.
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        }

    def get_session(self):
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        # Using the context manager __enter__ directly for brevity (adjust as needed)
        return db_context.session().__enter__()

    @staticmethod
    def clean_ltree(value: str) -> str:
        if not value:
            return "unknown"
        value = value.replace('>', '.').strip()
        value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
        value = re.sub(r"[._]{2,}", ".", value)
        return value.strip("._")

    @staticmethod
    def generate_slug(url: str, title: str) -> str:
        if not url:
            return BloombergCategoriesParser.clean_ltree(title or 'unknown')
        try:
            # Attempt to use the URL path for the slug; ignore common segments if present.
            parts = url.split('//')[1].split('/')[1:]
            parts = [p for p in parts if p and p not in ['index.html', 'article', 'articles']]
            if parts:
                return '_'.join(parts)
            else:
                return BloombergCategoriesParser.clean_ltree(title or 'unknown')
        except Exception:
            return BloombergCategoriesParser.clean_ltree(title or 'unknown')

    @staticmethod
    def generate_atom_link(url: str) -> str:
        """
        If the URL is of the form:
            https://www.bloomberg.com/<category>
        (with an optional trailing slash) where <category> is a single word,
        then return the corresponding RSS feed URL:
            https://feeds.bloomberg.com/<category>/news.rss
        Otherwise, return None.
        """
        pattern = r'^https:\/\/www\.bloomberg\.com\/([A-Za-z0-9-]+)\/?$'
        match = re.match(pattern, url)
        if match:
            category = match.group(1)
            return f"https://feeds.bloomberg.com/{category}/news.rss"
        return None

    def fetch_html_content(self) -> str:
        """
        Uses pychrome to open a new Chrome tab, navigate to the Bloomberg Europe page,
        wait for the page to load, remove unwanted elements, and return the cleaned HTML.
        """
        browser = None
        tab = None
        try:
            # Connect to a Chrome instance running with remote debugging enabled
            browser = pychrome.Browser(url="http://127.0.0.1:9222")
            tab = browser.new_tab()

            # Define an exception listener for debugging purposes
            def handle_exception(msg):
                print(f"Debug: {msg}")

            tab.set_listener("exception", handle_exception)
            tab.start()
            tab.Page.enable()
            tab.Runtime.enable()

            # Navigate to the Bloomberg Europe page
            tab.Page.navigate(url=self.base_url)
            time.sleep(15)  # Wait for the page to fully load (adjust if necessary)

            # JavaScript to remove <script>, <style>, <iframe>, <link>, and <meta> elements
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
            return html_content

        except Exception as e:
            raise Exception(f"Failed to fetch Bloomberg page using pychrome: {e}")
        finally:
            # Ensure proper cleanup of the tab and browser connection
            if tab is not None:
                try:
                    tab.stop()
                except Exception as cleanup_e:
                    print(f"Error stopping tab: {cleanup_e}")
            if browser is not None and tab is not None:
                try:
                    browser.close_tab(tab)
                except Exception as cleanup_e:
                    print(f"Error closing tab: {cleanup_e}")

    def extract_categories(self, html_content: str) -> List[Dict]:
        """
        The Bloomberg footer contains several submenu containers. In some containers a header (a <div>
        with a class matching 'media-ui-SubmenuDesktop_submenuText-*') exists—these we treat as a parent
        category (level 1) with the contained links as subcategories (level 2). Other containers that have
        no header will be treated as direct main (level 1) categories.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        # Find the footer container by matching part of its unique class name
        footer = soup.find("div", class_=re.compile("styles_gridFooter__"))
        if not footer:
            raise Exception("Could not find footer container on Bloomberg page.")

        categories = []
        # Each submenu container corresponds to a group of links.
        submenu_containers = footer.find_all("div", attrs={"aria-label": "submenu-desktop"})
        for container in submenu_containers:
            # Look for a header element within the container
            header = container.find("div", class_=re.compile("media-ui-SubmenuDesktop_submenuText-"))
            if header:
                parent_title = header.get_text(strip=True)
                parent_path = self.clean_ltree(parent_title)
                # Create a main category record for the group.
                main_category = {
                    'title': parent_title,
                    'link': '',  # No URL is provided for the group header.
                    'atom_link': "",
                    'path': parent_path,
                    'level': 1,
                    'slug': self.clean_ltree(parent_title),
                    'description': parent_title
                }
                categories.append(main_category)
                print(f"Processing main group: {parent_title}")

                # Now add each subcategory (level 2) from the <a> links
                for a in container.find_all("a"):
                    sub_title = a.get_text(strip=True)
                    sub_href = a.get("href", "")
                    atom_link = self.generate_atom_link(sub_href)
                    sub_path = f"{parent_path}.{self.clean_ltree(sub_title)}"
                    subcategory = {
                        'title': sub_title,
                        'link': sub_href,
                        'atom_link': atom_link if atom_link else "",
                        'path': sub_path,
                        'level': 2,
                        'slug': self.generate_slug(sub_href, sub_title),
                        'description': f"{parent_title} - {sub_title}"
                    }
                    print(f"  Processing subcategory: {sub_title}")
                    categories.append(subcategory)
            else:
                # No header found: treat each <a> as a main category (level 1)
                for a in container.find_all("a"):
                    title = a.get_text(strip=True)
                    href = a.get("href", "")
                    atom_link = self.generate_atom_link(href)
                    path = self.clean_ltree(title)
                    category = {
                        'title': title,
                        'link': href,
                        'atom_link': atom_link if atom_link else "",
                        'path': path,
                        'level': 1,
                        'slug': self.generate_slug(href, title),
                        'description': title
                    }
                    print(f"Processing category: {title}")
                    categories.append(category)
        return categories

    def store_categories(self, categories: List[Dict]):
        session = self.get_session()
        try:
            for category_data in categories:
                # Check for an existing record by slug and portal_id
                existing = session.query(self.CategoryModel).filter(
                    self.CategoryModel.slug == category_data['slug'],
                    self.CategoryModel.portal_id == self.portal_id
                ).first()
                if not existing:
                    # Assuming the model supports the atom_link field.
                    category = self.CategoryModel(
                        name=category_data['title'],
                        slug=category_data['slug'],
                        portal_id=self.portal_id,
                        path=category_data['path'],
                        level=category_data['level'],
                        description=category_data['description'],
                        link=category_data['link'],
                        atom_link=category_data.get('atom_link', None),
                        is_active=True
                    )
                    session.add(category)
            session.commit()
        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to store categories: {e}")
        finally:
            session.close()

    def run(self):
        try:
            # Instead of using requests, use pychrome to fetch the page content.
            html_content = self.fetch_html_content()
            categories = self.extract_categories(html_content)
            self.store_categories(categories)
        except Exception as e:
            raise Exception(f"Error processing categories: {e}")


def main():
    import argparse
    from db_scripts.models.models import Base  # Ensure models are created if needed

    argparser = argparse.ArgumentParser(description="Bloomberg Categories Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_bloomberg", env=args.env)
        parser = BloombergCategoriesParser(
            portal_id=portal_id,
            env=args.env,
            category_model=BloombergCategory
        )
        parser.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
