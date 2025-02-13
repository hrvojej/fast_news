from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
from db_scripts.db_context import DatabaseContext
from portals.modules.logging_config import setup_script_logging
from sqlalchemy.dialects.postgresql import insert


# Configure logger using the shared logging configuration.
logger = setup_script_logging(__file__)

class BaseRSSParser(ABC):
    """
    Base class for RSS parsers.
    Encapsulates shared functionality:
      - Fetching feeds
      - Parsing XML with BeautifulSoup
      - Managing database sessions
      - Handling errors and logging
      - Upserting items into the database
    """
    def __init__(self, portal_id, env='dev'):
        """
        :param portal_id: Unique identifier for the portal.
        :param env: Environment ('dev' or 'prod').
        """
        self.portal_id = portal_id
        self.env = env
        self.db_context = DatabaseContext.get_instance(env)
        # Subclasses must set this to their specific SQLAlchemy model.
        self.model = None

    def fetch_feed(self, url):
        """
        Fetches the RSS feed from a given URL and returns a BeautifulSoup object.
        :param url: The URL of the RSS feed.
        :return: BeautifulSoup object of the parsed XML.
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'xml')
            logger.info(f"Successfully fetched feed from {url}.")
            return soup
        except Exception as e:
            logger.error(f"Error fetching feed from {url}: {e}")
            raise

    def get_session(self):
        """
        Returns a database session from the DatabaseContext.
        Note: Subclasses can also use context managers (e.g. "with self.db_context.session() as session:")
        """
        return self.db_context.session().__enter__()

    def process_feed(self, feed_url, category_id):
        new_articles_count = 0
        updated_articles_count = 0
        updated_articles_details = []
        try:
            soup = self.fetch_feed(feed_url)
            items = soup.find_all('item')
            logger.info(f"Found {len(items)} items in feed {feed_url}.")
            with self.db_context.session() as session:
                for item in items:
                    item_data = self.parse_item(item, category_id)
                    result, detail = self.upsert_item(item_data, session)
                    if result == 'new':
                        new_articles_count += 1
                    elif result == 'updated':
                        updated_articles_count += 1
                        updated_articles_details.append(detail)  # detail: (title, old_date, new_date)
                session.commit()
                logger.info(f"Successfully processed feed: {feed_url}")
        except Exception as e:
            logger.error(f"Error in process_feed for {feed_url}: {e}")
            raise
        return new_articles_count, updated_articles_count, updated_articles_details


    def process_multiple_feeds(self, feeds):
        """
        Processes multiple feeds.
        :param feeds: List of tuples (feed_url, category_id)
        """
        for feed_url, category_id in feeds:
            try:
                self.process_feed(feed_url, category_id)
            except Exception as e:
                logger.error(f"Error processing feed {feed_url}: {e}")

    @abstractmethod
    def parse_item(self, item, category_id):
        """
        Abstract method to parse a single RSS feed item.
        Subclasses must implement this to extract the necessary fields.
        :param item: A BeautifulSoup element corresponding to an <item>.
        :param category_id: Category identifier associated with the item.
        :return: Dictionary of parsed item data.
        """
        pass



    def upsert_item(self, item_data, session):
        try:
            if self.model is None:
                raise Exception("Model not set in parser. Ensure self.model is defined in the subclass.")
            
            stmt = insert(self.model).values(**item_data)
            # Use the unique index on url
            stmt = stmt.on_conflict_do_update(
                index_elements=[self.model.url],
                set_=item_data,
                where=(self.model.pub_date != stmt.excluded.pub_date)
            ).returning(self.model.pub_date)
            
            result = session.execute(stmt)
            session.commit()
            
            # Optionally, inspect result.fetchone() if needed for logging
            returned_pub_date = result.scalar()  # This is the new pub_date if update happened, or None if no update
            if returned_pub_date is None:
                # No update took place because the pub_date was the same.
                # logger.info(f"No update needed for item: {item_data.get('title')}")
                return 'unchanged', None
            else:
                logger.info(f"Upserted item: {item_data.get('title')}")
                # You can decide here how to report "new" vs "updated"
                # For example, if an existing row was found, treat it as "updated"
                return 'updated', (item_data.get('title'), None, item_data.get('pub_date'))
        except Exception as e:
            logger.error(f"Error upserting item with url {item_data.get('url')}: {e}")
            raise



    def is_update_needed(self, existing, new_data):
        """
        Compares an existing record with new data to decide if an update is required.
        For example, by checking if the publication date has changed.
        :param existing: Existing database record.
        :param new_data: Dictionary with new data.
        :return: Boolean indicating whether an update is necessary.
        """
        if existing.pub_date and new_data.get('pub_date'):
            return existing.pub_date != new_data.get('pub_date')
        return existing.pub_date != new_data.get('pub_date')
    
    
    def run_feeds(self, feeds):
        total_new = 0
        total_updated = 0
        total_updated_details = []
        for category_id, feed_url in feeds:
            try:
                new_count, updated_count, updated_details = self.process_feed(feed_url, category_id)
                total_new += new_count
                total_updated += updated_count
                total_updated_details.extend(updated_details)
            except Exception as e:
                logger.error(f"Error processing feed for category {category_id} at {feed_url}: {e}")
        print("\nFinal Report:")
        print(f"Newly added articles: {total_new}")
        print(f"Updated articles: {total_updated}")
        if total_updated_details:
            print("\nDetails of updated articles:")
            for title, old_date, new_date in total_updated_details:
                print(f" - Article '{title}': pub_date in DB: {old_date}, pub_date online: {new_date}")
        print("All articles processed and committed successfully.")


    @abstractmethod
    def run(self):
        """
        Abstract main method that should be implemented by child classes.
        Typically, this method will call process_feed() (or process_multiple_feeds()) for each feed.
        """
        raise NotImplementedError("Subclasses must implement the run() method.")
