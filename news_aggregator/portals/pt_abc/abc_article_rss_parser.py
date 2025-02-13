#!/usr/bin/env python
import argparse
from uuid import UUID
import sys
import os

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)


from portals.modules.base_parser import BaseRSSParser
from portals.modules.portal_db import fetch_portal_id_by_prefix, get_active_categories
from portals.modules.rss_parser_utils import parse_rss_item
from db_scripts.models.models import create_portal_article_model, create_portal_category_model

from portals.modules.logging_config import setup_script_logging
logger = setup_script_logging(__file__)


# Dynamically create models for the portal.
ABCCategory = create_portal_category_model("pt_abc")
ABCArticle = create_portal_article_model("pt_abc")


class ABCRSSArticlesParser(BaseRSSParser):
    def __init__(self, portal_id: UUID, env: str = 'dev'):
        super().__init__(portal_id, env)
        self.model = ABCArticle

    def parse_item(self, item, category_id):
        """
        Uses the generic RSS parser utility to parse an item.
        """
        return parse_rss_item(item, category_id)

    def run(self):
        feeds = get_active_categories("pt_abc", self.env)
        self.run_feeds(feeds)



def main():
    argparser = argparse.ArgumentParser(description="ABC RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    portal_id = fetch_portal_id_by_prefix("pt_abc", env=args.env)
    parser = ABCRSSArticlesParser(portal_id=portal_id, env=args.env)
    parser.run()

if __name__ == "__main__":
    main()
