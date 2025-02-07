# Categories question
I need to parse categories from:
https://www.aljazeera.com/

Category info is stored in elements like:
<header class="header-menu site-header container__inner" role="banner"><div class="bypass-block-links-container"><span class="screen-reader-text" tabindex="-1">Skip links</span><a class="bypass-block-link" aria-hidden="false" href="#featured-news-container">Skip to Featured Content</a><a class="bypass-block-link" aria-hidden="false" href="#news-feed-container">Skip to Content Feed</a></div><div class="site-header__logo css-0"><a aria-label="al jazeera, link to home page" href="/"><figure aria-hidden="true" class="css-v2kfba"><span class="site-logo"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 166 60"><g fill="none"><path fill="#fa9000" d="M118.38 27.06V24h-8.2v2.63h4.22l-4.34 6.3V36h8.42v-2.65h-4.43l4.33-6.29zm29.3 1.35c-.18.23-.42.33-1 .39h-1.14v-2.4h.89l.21.02c.46.01.65.07.85.21.5.32.62 1.2.19 1.78zm2.78 3.24c-.46-1.06-.62-1.28-1.06-1.48a1 1 0 00.21-.09c1.37-.61 2.02-2.16 1.5-3.88-.42-1.42-1.53-2.2-3.64-2.2h-4.94v12h3.14v-4.49h.71c.51 0 .82.22 1.08.86l.17.38.09.22L148.9 36h3.25l-1.52-3.93c-.06-.15-.1-.28-.17-.42zm7.1-.45l1.2-3.6 1.21 3.6h-2.4zm2.92-7.2h-3.5l-4.22 12h3.18l.71-2.2h4.07l.7 2.2h3.36l-4.3-12zm-60.05 7.2l1.2-3.6 1.2 3.6h-2.4zm-.6-7.2l-4.2 12h3.17l.72-2.2h4.06l.7 2.2h3.37l-4.3-12h-3.51zm-27.66 7.2l1.2-3.6 1.2 3.6h-2.4zm-.6-7.2l-4.21 12h3.18l.71-2.2h4.07l.69 2.2h3.37l-4.3-12h-3.51zm63.3 7.37h4.16v-2.56h-4.15v-2.18h4.82V24h-8v12h8.43v-2.55h-5.25v-2.08zm-10.82 0h4.16v-2.56h-4.16v-2.18h4.83V24h-8v12h8.42v-2.55h-5.25v-2.08zm-33.22 4.1c0 1.87-.65 2.55-2.08 2.12a1.05 1.05 0 01-.24-.08l-.7 2.66c.15.08.31.15.48.22 3.34 1.3 5.53-.63 5.53-4.04V24h-3v11.47zm-2.42-2.15h-3.97V24h-3.25v12h7.22v-2.68z" style="fill: rgb(250, 144, 0);"></path><path fill="#fa9000" d="M0 0h60.14v60H0z"></path><path d="M34.13 48.03c-.07.03-.1.16-.05.33l.33.87c.2.53.52 1.15.97 1.46.47.34.72.22.82.18.07-.04.37-.22.26-.7a2.99 2.99 0 00-.27-.85c-.1-.18-.22-.3-.3-.27-.04 0 0 .18 0 .28 0 .2-.07.33-.23.4-.14.06-.48.18-.74-.28-.22-.38-.4-.87-.49-1.08-.06-.15-.16-.34-.26-.34h-.04zm-7.47 1.38l1.59 1.32 1.54-1.87-1.59-1.32-1.54 1.87zm.35-3.26l1.59 1.31 1.55-1.86-1.6-1.32-1.54 1.87zm10.14-4.6l1.87.88 1.03-2.2-1.86-.88-1.04 2.2zM27.5 40a12.75 12.75 0 003.36 4.63c.14-.97.3-1.65.44-2.13-1.4-1-2.4-2.1-3.05-3.18l-.75.68zm3.54-2.35l1.86.88 1.04-2.2-1.87-.88-1.03 2.2zm-9-8.75s-1.17.83-1.64 1.92a2.4 2.4 0 00-.1 1.75c.16.35.55.68 1.06.28.35-.28.5-.68.58-1.01.05-.2.06-.33.06-.43 0-.12-.04-.22-.15-.2-.34.11-.14.57-.38.79-.18.1-.66.05-.75-.42-.1-.47.27-1.07.6-1.47.32-.4.9-.92.9-.92s.4-.34.27-.51l-.04-.01c-.12 0-.41.23-.41.23zM33.5 27.7l-1.44 1.57-1.24 1.35c-.27.3-.41.6-.38.76l.17.82c.04-.15.22-.43.4-.64.14-.15.8-.89 1.45-1.58l1.23-1.35c.27-.3.41-.6.38-.76l-.17-.81c-.04.15-.21.42-.4.64zM17.97 39.53c.22-.72.64-1.37 1.35-1.78 1.18-.55 1.64.86 1.64.86-.08.95-.8 1.45-1.61 1.45-.47 0-.98-.17-1.38-.53zm8.75-22.88a1.45 1.45 0 101.16 2.38l.03-.04c.17 1.16-.38 2.08-1.67 3.15-1.31 1.12-4.4 2.56-6.58 4.3a9.8 9.8 0 00-3.68 10.51 13.93 13.93 0 00.86 2.44 14.3 14.3 0 00.87 5.79c1.08 2.42 3.01 4.4 5.79 3.82 2.8-.66 3.12-5.22 3.43-8.55.09-.55.17-.65.34-.79.45-.38 1.54-1.4 2.06-1.86.32-.29.6-.57.79-.94.23-.44.1-1.02.1-1.02l-.3-2.2c-.09.31-.47.75-1 1.29-.56.56-2.05 1.84-2.19 1.98-.13.14-.61.5-.82 2.17-.54 4.55-1.43 6.7-3.04 7.43-.43.2-.9.3-1.43.3-2.95-.02-3.73-3.62-3.72-5.59 0-.12 0-.24.02-.34.68.92 1.7 1.84 2.94 1.65 2-.3 1.37-3.67 1.08-4.45-.28-.78-1.05-3.13-2.72-3.01-1.18.08-1.73 1.47-1.99 2.64a9.49 9.49 0 01-.27-2.86c.17-2.04.87-4.58 3.83-7.08 2.1-1.78 4.5-3.06 5.82-4.1a5.35 5.35 0 001.66-2.12 9.58 9.58 0 01-.57 2.27c-1.23 3.23-4.95 8.57-5 16.1 0 2.32.22 4.32.59 6.03.2-.13.39-.32.57-.53-.26-1.23-.4-2.58-.4-4.03 0-7.52 3.69-12.84 4.89-16.07.63-1.7.65-2.93.65-4.15 0-1.5-.34-3.07-.65-3.68-.34-.58-.75-.84-1.38-.84h-.07zm3.63-10.3c-.74.51-1.36 1.7-1.36 3.5 0 1.1.32 2.43 1.17 3.92-1.15 1.56-1.36 3-.87 4.38.37 1.05.56 1.32.73 1.95.42 1.6-.05 3.5-1.3 6.46-1.02 2.4-2.35 4.92-2.35 7.98 0 .7.07 1.39.17 2.06.11-.12.37-.35.67-.64-.15-2.4.8-4.81 1.98-6.98 1.7-3.17 1.92-6.39 1.59-8.15 1.2 1.28 3.22 3.2 4.4 5.16.4.66.64 1.29.7 1.93a5.04 5.04 0 01-1.39 3.76c-.8.92-.53 1.73-.5 1.9.07.25.4 1.26.63 1.91.9-1.75 3.36-2.73 4.48-4.19.25 1.8-1.1 3.5-2.1 4.64-.23.26-.5.52-.79.8-1.9 1.82-3.14 3.06-3.8 4.22-.16.26-.44.83-.57 1.27-.2.56-.44 1.5-.65 3.15a75.6 75.6 0 00-.39 2.66c-.13 1.19-.48 3.06-1.94 3.6-.07.03-.15.05-.23.06v.01c-1.39.3-2.8-.86-3.83-2.94-.22.16-.45.3-.7.42 1.4 3.3 3.5 4.81 5.33 4.81 1.4 0 2.5-.7 2.85-2.75.18-1.03.31-2.18.43-3.29.06-.53.32-3.55.8-4.65.6-1.23 1.92-2.41 3.88-4.43 1.2-1.25 1.87-2.3 2.21-3.14 1.14-2.08-.27-7.04-.55-7.94 0-.03 0-.04-.03-.04-.02 0-.03.01-.05.05l-.01.02c-.5.82-1.4 1.57-2.25 2.18.48-1.29.35-2.27.16-3.1l-.04-.15c-.85-3.29-4.21-6.22-5.73-7.9-1.98-2.2-1.3-3.6-.58-4.5l.44.63c2.69 3.64 7.74 9.41 10.4 14.91a18.44 18.44 0 011.46 4.06c1.05 5.7-2.93 11.49-8.9 9.86l-.11-.03c-.16.5-.31 1.31-.46 2.41.9.39 1.88.62 2.83.66h.21c4.9.06 8.73-3.6 8.03-11.3 0 0-.3-3.2-1.95-6.58-2.65-5.92-7.56-11.78-10.57-15.57a10.04 10.04 0 01-1.8-3.14c-.56-1.75-.2-3.11.52-3.7.16-.13.35-.28.53-.37.1-.06.06-.18-.01-.2h-.07c-.1 0-.3.05-.72.34zm-5.5 12.8c-.8.02-1.44.69-1.41 1.5a1.45 1.45 0 102.9-.1 1.45 1.45 0 00-1.45-1.4h-.05z" fill="#FFF"></path></g></svg></span></figure></a></div><div class="site-header__live-menu"><div class="site-header__live-cta--mobile"><div class="css-0"><a class="live-cta" aria-label="link to live stream video player" href="/live"><div class="live-cta__icon-wrapper"><svg class="icon icon--play icon--primary icon--24 " viewBox="0 0 20 20" version="1.1" aria-hidden="true"><title>play</title><path class="icon-main-color" d="M0 10a10 10 0 1 1 10 10A10 10 0 0 1 0 10zm7.92 4.27a.48.48 0 0 0 .23-.07L14 10.35a.42.42 0 0 0 0-.7L8.15 5.8a.42.42 0 0 0-.43 0 .4.4 0 0 0-.22.36v7.7a.4.4 0 0 0 .22.36.36.36 0 0 0 .2.05z"></path></svg></div><span class="live-cta__title live-cta__title--black"> Live </span></a></div></div><button aria-expanded="true" aria-label="Close navigation menu" data-testid="menu-trigger" class="site-header__menu-trigger"><svg class="icon icon--close icon--black icon--24 " viewBox="0 0 20 20" version="1.1" aria-hidden="true"><title>Close navigation menu</title><polygon class="icon-main-color" points="8.66 10.1 0 1.44 1.24 0.2 9.9 8.86 18.56 0.2 19.8 1.44 11.14 10.1 19.8 18.76 18.56 20 9.9 11.34 1.24 20 0 18.76 8.66 10.1"></polygon></svg></button></div><nav class="site-header__navigation css-15ru6p1" aria-label="Primary navigation menu"><span class="screen-reader-text">Navigation menu</span><ul class="menu header-menu"><li class="menu__item menu__item--aje menu__item--has-submenu" data-testid="sub-menu-item"><a href="/news/"><span>News</span></a><button aria-expanded="false" class="no-styles-button expand-button"><svg class="icon icon--caret-down icon--grey icon--16 " viewBox="0 0 20 20" version="1.1" aria-hidden="true"><path class="icon-main-color" d="M10 12.92l8.3-8.86L20 5.87l-8.3 8.86-1.7 1.83-1.7-1.81L0 5.87l1.7-1.81z"></path></svg><span class="screen-reader-text">Show more news sections</span></button><div class="submenu_wrapper"><ul class="menu menu__submenu"><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/africa/"><span>Africa</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/asia/"><span>Asia</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/us-canada/"><span>US &amp; Canada</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/latin-america/"><span>Latin America</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/europe/"><span>Europe</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/asia-pacific/"><span>Asia Pacific</span></a></li></ul></div></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/middle-east/"><span>Middle East</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/tag/explainer/"><span>Explained</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/opinion/"><span>Opinion</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/sports/"><span>Sport</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/videos/"><span>Video</span></a></li><li class="menu__item menu__item--aje menu__item--has-submenu" data-testid="sub-menu-item"><button class="no-styles-button">More</button><button aria-expanded="false" class="no-styles-button expand-button"><svg class="icon icon--caret-down icon--grey icon--16 " viewBox="0 0 20 20" version="1.1" aria-hidden="true"><path class="icon-main-color" d="M10 12.92l8.3-8.86L20 5.87l-8.3 8.86-1.7 1.83-1.7-1.81L0 5.87l1.7-1.81z"></path></svg><span class="screen-reader-text">Show more sections</span></button><div class="submenu_wrapper"><ul class="menu menu__submenu"><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/features/"><span>Features</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/economy/"><span>Economy</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/tag/human-rights/"><span>Human Rights</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/climate-crisis"><span>Climate Crisis</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/investigations/"><span>Investigations</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/interactives/"><span>Interactives</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/gallery/"><span>In Pictures</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/tag/science-and-technology/"><span>Science &amp; Technology</span></a></li><li class="menu__item menu__item--aje" data-testid="sub-menu-item"><a href="/audio/podcasts"><span>Podcasts</span></a></li></ul></div></li></ul></nav><div class="site-header__live-menu--desktop"><div class="site-header__live-cta"><div class="css-0"><a class="live-cta" aria-label="link to live stream video player" href="/live"><div class="live-cta__icon-wrapper"><svg class="icon icon--play icon--primary icon--24 " viewBox="0 0 20 20" version="1.1" aria-hidden="true"><title>play</title><path class="icon-main-color" d="M0 10a10 10 0 1 1 10 10A10 10 0 0 1 0 10zm7.92 4.27a.48.48 0 0 0 .23-.07L14 10.35a.42.42 0 0 0 0-.7L8.15 5.8a.42.42 0 0 0-.43 0 .4.4 0 0 0-.22.36v7.7a.4.4 0 0 0 .22.36.36.36 0 0 0 .2.05z"></path></svg></div><span class="live-cta__title live-cta__title--black"> Live </span></a></div></div><div class="site-header__search-trigger"><button type="button" class="no-styles-button" aria-pressed="false"><span class="screen-reader-text">Click here to search</span><svg class="icon icon--search icon--grey icon--24 " viewBox="0 0 20 20" version="1.1" aria-hidden="true"><title>search</title><path class="icon-main-color" d="M3.4 11.56a5.77 5.77 0 1 1 8.16 0 5.78 5.78 0 0 1-8.16 0zM20 18.82l-6.68-6.68a7.48 7.48 0 1 0-1.18 1.18L18.82 20 20 18.82z"></path></svg></button></div><div class="site-header__account"><button class="auth-btn">Sign up</button></div></div></header>

RSS feeds are stored in that page in elements like:
<a target="_blank" href="https://feeds.abcnews.com/abcnews/usheadlines"><img src="https://s.abcnews.com/images/technology/rss_chicklet.jpg"></a>

Aditionally only sports have categories and when opened:
https://www.aljazeera.com/sports/
They are conteind in:
<div class="container"><div class="container__inner container__inner--no-pad-mobile"><div class="navigation-bar-container u-bottom-border"><div class="navigation-bar u-hide-scrollbar u-smooth-scrolling" data-testid="scrollable-element"><nav aria-label="Secondary navigation menu"><span class="screen-reader-text">Navigation menu</span><button tabindex="-1" aria-hidden="true" class="navigation-bar__arrow-icon navigation-bar__arrow-icon--left"><svg class="icon icon--caret-left icon--grey icon--16 " viewBox="0 0 20 20" version="1.1" aria-hidden="true"><title>caret-left</title><polygon fill="#595959" class="icon-main-color" transform="scale(0.36)" points="30 3.08091249 26.9190875 0 0.919087508 26 26.9190875 52 30 48.9190875 7.08091249 26"></polygon></svg></button><ul class="menu navigation-bar__menu"><li class="menu__item"><a target="" href="/tag/cricket/">Cricket</a></li><li class="menu__item"><a target="" href="/tag/football/">Football</a></li><li class="menu__item"><a target="" href="/tag/basketball/">Basketball</a></li><li class="menu__item"><a target="" href="/tag/motorsports/">Motorsports</a></li><li class="menu__item"><a target="" href="/tag/boxing/">Boxing</a></li><li class="menu__item"><a target="" href="/tag/mma/">MMA</a></li></ul><button tabindex="-1" aria-hidden="true" class="navigation-bar__arrow-icon navigation-bar__arrow-icon--right"><svg class="icon icon--caret-right icon--grey icon--16 " viewBox="0 0 20 20" version="1.1" aria-hidden="true"><title>caret-right</title><polygon fill="#595959" class="icon-main-color" transform="scale(0.36) rotate(180 16 26)" points="30 3.08091249 26.9190875 0 0.919087508 26 26.9190875 52 30 48.9190875 7.08091249 26"></polygon></svg></button></nav></div></div></div></div>

Leave default or empty fields that are not present. 

In case there i pub_date or similar field to fill in - never put timestamp there if data is not present in source parsed. Just leave that date field empty. 

portal prefix:
pt_aljazeera

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




