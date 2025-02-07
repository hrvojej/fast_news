
# ###################################### article question ############################
I similar way how nyt article parser (below) is created now I need to create 
fox news article parser from categories atom_link url

So you need to iterate over 
SELECT atom_link FROM pt_fox.categories

Example of atom_link returned:
https://moxie.foxnews.com/google-publisher/travel.xml

# Example source code of RSS category, first few lines with several item elements:
<item>
<link>https://www.foxnews.com/tech/beware-fake-reddit-solutions-delivering-dangerous-malware</link>
<guid isPermaLink="true">https://www.foxnews.com/tech/beware-fake-reddit-solutions-delivering-dangerous-malware</guid>
<title>Beware of fake Reddit solutions delivering dangerous malware</title>
<description>Bad actors are now mimicking Reddit to spread malware that can steal personal information. CyberGuy shares what you need to know about fake Reddit pages.</description>
<content:encoded><p>Sometimes, when you need an answer to a complex life situation or a way to troubleshoot an error on <a href="https://www.foxnews.com/category/tech/topics/computers" target="_blank" rel="noopener">your computer</a>, regular articles on the web don’t help. Some issues are so niche that no one writes about them, and those who do often say nothing useful in 1,000 words. </p><p>In these cases, adding Reddit to your search query can be a game changer. Nine times out of 10, someone on Reddit has faced the same issue, and there's probably a solution. </p><p>But bad actors have caught on to this, too. They’re now mimicking Reddit to spread malware that can steal your personal information.</p><p><a href="https://cyberguy.com/newsletter/" target="_blank" rel="nofollow noopener"><strong><u>GET SECURITY ALERTS, EXPERT TIPS - SIGN UP FOR KURT’S NEWSLETTER - THE CYBERGUY REPORT HERE</u></strong></a></p><p>Hackers are distributing nearly <a href="https://www.foxnews.com/category/tech/topics/hackers" target="_blank" rel="noopener">1,000 fake websites</a> mimicking Reddit and WeTransfer to spread the Lumma Stealer malware. These sites are designed to trick you into downloading malicious software by imitating legitimate discussions and file-sharing services.</p><p>On these fake Reddit pages, attackers create a fabricated discussion where one user asks for help downloading a tool, another offers a WeTransfer link and a third expresses gratitude to make the exchange seem real. Clicking the link redirects victims to a counterfeit WeTransfer site, where the download button delivers the Lumma Stealer malware.</p><p>All these fake pages have the following things in common:</p><p>These fake websites were discovered by <a href="https://x.com/crep1x/status/1881404758843699402" target="_blank" rel="nofollow noopener"><u>Sekoia researcher crep1x</u></a>, who compiled a full list of the pages involved in the scheme. In total, 529 of these sites mimic Reddit, while 407 impersonate WeTransfer to trick users into downloading malware.</p><p>According to <a href="https://www.bleepingcomputer.com/news/security/hundreds-of-fake-reddit-sites-push-lumma-stealer-malware/" target="_blank" rel="nofollow noopener"><u>BleepingComputer</u></a>, hackers may be driving traffic to these fake pages through methods like malicious ads (<a href="https://cyberguy.com/security/older-americans-are-being-targeted-in-a-malvertising-campaign/" target="_blank" rel="nofollow noopener"><u>malvertising</u></a>), search engine manipulation (SEO poisoning), harmful websites, direct messages on social media and other deceptive tactics.</p><p><a href="https://cyberguy.com/privacy/best-services-for-removing-your-personal-information-from-the-internet/" target="_blank" rel="nofollow noopener"><strong><u>HOW TO REMOVE YOUR PRIVATE DATA FROM THE INTERNET</u></strong></a></p><p>Hackers are using fake Reddit pages to spread Lumma Stealer, a powerful malware designed to steal personal data while staying under the radar. Once it infects a device, it can grab passwords stored in web browsers and session tokens, allowing attackers to hijack accounts without even needing a password.</p><p>But Reddit isn’t the only way this malware spreads. Hackers also push it through GitHub comments, deepfake websites and shady online ads. Once they <a href="https://www.foxnews.com/category/tech/topics/security" target="_blank" rel="noopener">steal login credentials</a>, they often sell them on hacker forums, where others can use them for further attacks.</p><p>This type of malware has already played a role in major security breaches, including attacks on <a href="https://cyberguy.com/security/powerschool-data-breach-exposes-student-teacher-records/" target="_blank" rel="nofollow noopener"><u>PowerSchool</u></a>, <a href="https://cyberguy.com/security/data-breach-exposes-56-million-clothing-customers/" target="_blank" rel="nofollow noopener"><u>Hot Topic</u></a>, CircleCI and Snowflake. It’s a growing threat, especially for companies that rely on password-based security.</p><p><a href="https://www.foxnews.com/tech/what-is-ai-artificial-intelligence" target="_blank" rel="noopener"><strong>WHAT IS ARTIFICIAL INTELLIGENCE (AI)?</strong></a></p><p><a href="https://cyberguy.com/security/best-antivirus-protection/" target="_blank" rel="nofollow noopener"><strong><u>BEST ANTIVIRUS FOR MAC, PC, IPHONES AND ANDROIDS - CYBERGUY PICKS</u></strong></a></p><p><strong>1. Be cautious with download links: </strong>Avoid downloading files from random Reddit discussions, social media messages or unfamiliar websites. If an unknown user shares the link or seems out of place in the context, it’s better to err on the side of caution. If the link is directing you to a file-sharing site like WeTransfer or Google Drive, double-check the URL for any signs of manipulation—like random characters added to the domain name.</p><p><strong>2. Have strong antivirus software: </strong>The best way to safeguard yourself from malicious links that install malware originating from these Reddit discussions, potentially accessing your private information, is to have antivirus software installed on all your devices. This protection can also alert you to phishing emails and ransomware scams, keeping your personal information and digital assets safe. <a href="https://cyberguy.com/security/best-antivirus-protection/" target="_blank" rel="nofollow noopener"><u>Get my picks for the best 2025 antivirus protection winners for your Windows, Mac, Android and iOS devices</u></a>.</p><p><a href="https://www.foxbusiness.com/apps-products" target="_blank" rel="noopener"><strong>GET FOX BUSINESS ON THE GO BY CLICKING HERE</strong></a></p><p><strong>3.</strong> <strong>Verify website URLs: </strong>Fake websites often look convincing but have slight differences in their URLs. Check for misspellings, extra characters or unusual domains (e.g., ".org" or ".net" instead of the official ".com").</p><p><strong>4. Use strong, unique passwords and enable 2FA: </strong>A <a href="https://cyberguy.com/security/best-password-managers/" target="_blank" rel="nofollow noopener"><u>password manager</u></a> can help generate and store strong passwords for each site. Meanwhile, enabling two-factor authentication (<a href="https://cyberguy.com/protect-your-devices/what-is-two-factor-authentication-and-why-should-i-enable-it/" target="_blank" rel="nofollow noopener"><u>2FA</u></a>) adds an extra layer of security, making it harder for attackers to hijack your accounts. Get more details about my <a href="https://cyberguy.com/tech-tips-tricks/best-password-managers/" target="_blank" rel="nofollow noopener"><u>best expert-reviewed Password Managers of 2025 here.</u></a></p><p><strong>5. Keep your software updated: </strong>Regularly <a href="https://cyberguy.com/security/how-to-update-your-devices/" target="_blank" rel="nofollow noopener"><u>update</u></a> your operating system, apps, browsers and other software on your PC or mobile devices. Updates often include patches for security vulnerabilities that hackers can exploit.</p><p><strong>6. Watch out for malvertising and SEO traps: </strong>Hackers manipulate search engine results and <a href="https://cyberguy.com/security/older-americans-are-being-targeted-in-a-malvertising-campaign/" target="_blank" rel="nofollow noopener"><u>run deceptive ads to trick users into visiting fake sites</u></a>. Stick to official sources and avoid clicking on ads or search results that seem too good to be true. </p><p><a href="https://cyberguy.com/how-to/fight-back-against-debit-card-hackers-your-money/" target="_blank" rel="nofollow noopener"><strong><u>HOW TO FIGHT BACK AGAINST DEBIT CARD HACKERS WHO ARE AFTER YOUR MONEY</u></strong></a></p><p>Hackers are getting sneakier, using fake Reddit and WeTransfer pages to spread dangerous malware like Lumma Stealer. These sites might look real, but they’re designed to steal your personal info. To stay safe, always double-check links and be cautious about downloading files from unfamiliar sources. Use strong, unique passwords, enable two-factor authentication and keep your software updated to stay one step <a href="https://www.foxnews.com/category/tech/topics/cybercrime" target="_blank" rel="noopener">ahead of cybercriminals</a>.</p><p>Have you ever encountered a suspicious link on Reddit or social media? How did you handle it? Let us know by writing us at <a href="http://cyberguy.com/Contact" target="_blank" rel="nofollow noopener"><strong><u>Cyberguy.com/Contact</u></strong></a><a rel="nofollow noopener"><strong><u>.</u></strong></a></p><p>For more of my tech tips and security alerts, subscribe to my free CyberGuy Report Newsletter by heading to <a href="http://cyberguy.com/Newsletter" target="_blank" rel="nofollow noopener"><strong><u>Cyberguy.com/Newsletter.</u></strong></a></p><p><a href="https://cyberguy.com/contact/" target="_blank" rel="nofollow noopener"><u>Ask Kurt a question or let us know what stories you'd like us to cover</u></a><a rel="nofollow noopener"><u>.</u></a></p><p>Follow Kurt on his social channels:</p><p>Answers to the most asked CyberGuy questions:</p><p>New from Kurt:</p><p><i>Copyright 2025 CyberGuy.com. All rights reserved.</i></p></content:encoded>
<media:content url="https://a57.foxnews.com/static.foxnews.com/foxnews.com/content/uploads/2025/02/931/523/3-beware-of-fake-reddit-solutions-delivering-dangerous-malware-outro.jpg?ve=1&tl=1" type="image/jpeg" expression="full" width="931" height="523"/>
<category domain="foxnews.com/metadata/dc.identifier">20b36c37-8928-5323-a8f0-e29c99bd40bc</category>
<category domain="foxnews.com/metadata/prism.channel">fnc</category>
<category domain="foxnews.com/metadata/dc.source">Fox News</category>
<category domain="foxnews.com/taxonomy">fox-news/tech</category>
<category domain="foxnews.com/taxonomy">fox-news/tech/topics/security</category>
<category domain="foxnews.com/taxonomy">fox-news/tech/topics/privacy</category>
<category domain="foxnews.com/taxonomy">fox-news/tech/topics/cybercrime</category>
<category domain="foxnews.com/taxonomy">fox-news/tech/topics/hackers</category>
<category domain="foxnews.com/section-path">fox-news/tech</category>
<category domain="foxnews.com/content-type">article</category>
<pubDate>Thu, 06 Feb 2025 10:00:55 -0500</pubDate>
</item>


Use this part:
<category domain="foxnews.com/taxonomy">fox-news/tech/topics/security</category>
<category domain="foxnews.com/taxonomy">fox-news/tech/topics/privacy</category>
<category domain="foxnews.com/taxonomy">fox-news/tech/topics/cybercrime</category>
<category domain="foxnews.com/taxonomy">fox-news/tech/topics/hackers</category>
to fill in keywords field


Leave default or empty fields that are not present. 

This is pub_date
<pubDate>Thu, 06 Feb 2025 10:00:55 -0500</pubDate>





Make sure you use all fields from article model as is.
In case script is run several times it should not make dupes , just insert new records if there is need for that.


# NYT Article Parser Example - follow this example to implement all core other functionalities except extraction logic
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

