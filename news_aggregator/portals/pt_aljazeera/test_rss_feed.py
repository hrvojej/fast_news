#!/usr/bin/env python
import requests
import logging
import sys

def setup_logging():
    # Configure logging to output to the console.
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

def fetch_feed(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses.
        logging.debug("HTTP Status Code: %s", response.status_code)
        return response.text
    except Exception as e:
        logging.error("Error fetching URL %s: %s", url, e)
        sys.exit(1)

def main():
    setup_logging()
    feed_url = "https://www.aljazeera.com/xml/rss/all.xml"
    content = fetch_feed(feed_url)
    
    print("Fetched Content:\n")
    print(content)

if __name__ == "__main__":
    main()
