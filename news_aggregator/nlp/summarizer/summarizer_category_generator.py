# path: fast_news/news_aggregator/nlp/summarizer/summarizer_category_generator.py
r"""
Module for generating a minimal category page.
This script loads the category template, renders it with dummy data,
and writes the output to the final location:
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\categories\category_test.html
"""


import os
import sys
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape
# Removed redundant import statement
from summarizer_category_utilities import ensure_category_images_folder, crop_and_resize_image

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Initialize logger at DEBUG level
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define directories
BASE_DIR = os.path.abspath(os.path.join(package_root, "frontend"))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
# The final output directory for category pages
OUTPUT_CATEGORY_DIR = os.path.join(BASE_DIR, "web", "categories")
if not os.path.exists(OUTPUT_CATEGORY_DIR):
    os.makedirs(OUTPUT_CATEGORY_DIR)
    logger.debug(f"Created output directory: {OUTPUT_CATEGORY_DIR}")

# Setup Jinja2 environment
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)

# Dummy data for testing
dummy_category = {
    "name": "Test Category"
}

# Hardcoded articles data from database (10 records)
articles_data = [
    {
        "summary_article_gemini_title": "The Hidden Hazard in Your Backyard: Unmasking the Environmental Cost of Dog Poop and the Quest for Greener Disposal",
        "article_html_file_location": "climate/The_Hidden_Hazard_in_Your_Backyard_Unmasking_the_E.html",
        "summary_featured_image": {"url": "What_Kind_of_Dog_Poop_Bags_Sho_1.jpg", "alt": "LGDPoopBagsSign", "caption": "LGDPoopBagsSign"},
        "popularity_score": 75
    },
    {
        "summary_article_gemini_title": "Political Firestorm Ignites: Top Prosecutors Resign as DOJ Moves to Dismiss Charges Against NYC Mayor Adams Over Alleged Political Interference",
        "article_html_file_location": "nyregion/Political_Firestorm_Ignites_Top_Prosecutors_Resign.html",
        "summary_featured_image": None,
        "popularity_score": 88
    },
    {
        "summary_article_gemini_title": "NCAA's Amateurism Shattered? $2.8 Billion Payout Sparks Epic Battle Over Athlete Employment !",
        "article_html_file_location": "business/NCAAs_Amateurism_Shattered_28_Billion_Payout_Spark.html",
        "summary_featured_image": {
            "url": "The_NCAA_Agreed_to_Pay_Players_1.jpg",
            "alt": "Flickr - Official U.S. Navy Imagery - The Superintendent, SECNAV and CNO salute and pay respect during the singing of the Irish and U.S. national anthems. (1)",
            "caption": "Flickr - Official U.S. Navy Imagery - The Superintendent, SECNAV and CNO salute and pay respect during the singing of the Irish and U.S. national anthems. (1)"
        },
        "popularity_score": 88
    },
    {
        "summary_article_gemini_title": "Bernie Sanders' Unyielding Crusade: Battling Billionaire Power and a Broken System for America's Working Class",
        "article_html_file_location": "us/politics/Bernie_Sanders_Unyielding_Crusade_Battling_Billion.html",
        "summary_featured_image": {
            "url": "Bernie_Sanders_Isnt_Giving_Up__1.jpg",
            "alt": "Senator of Vermont Bernie Sanders at Derry Town Hall, Pinkerton Academy NH October 30th, 2015 by Michael Vadon a 01",
            "caption": "Senator of Vermont Bernie Sanders at Derry Town Hall, Pinkerton Academy NH October 30th, 2015 by Michael Vadon a 01"
        },
        "popularity_score": 85
    },
    {
        "summary_article_gemini_title": "Whispers of Peace, Roars of War: Russia Eyes Normalcy Amidst High-Stakes US Talks and Ukraine Conflict",
        "article_html_file_location": "world/europe/Whispers_of_Peace_Roars_of_War_Russia_Eyes_Normalc.html",
        "summary_featured_image": {
            "url": "As_Moscow_and_Washington_Discu_1.jpg",
            "alt": "Embassy of Ukraine in Moscow",
            "caption": "Embassy of Ukraine in Moscow"
        },
        "popularity_score": 85
    },
    {
        "summary_article_gemini_title": "Maastricht's Subterranean Secrets : Unveiling the Labyrinth of History and Intrigue Beneath Limburg's Hills",
        "article_html_file_location": "arts/design/Maastrichts_Subterranean_Secrets_Unveiling_the_Lab.html",
        "summary_featured_image": None,
        "popularity_score": 78
    },
    {
        "summary_article_gemini_title": "Screen Savvy: Your Guide to This Week's Must-Watch TV - Gripping Dramas , Hilarious Comedy , and Unforgettable Specials Await!",
        "article_html_file_location": "arts/television/Screen_Savvy_Your_Guide_to_This_Weeks_Must-Watch_T.html",
        "summary_featured_image": {
            "url": "Everybodys_Live_With_John_Mula_1.jpg",
            "alt": "Oddball Comedy Tour (9594925893)",
            "caption": "Oddball Comedy Tour (9594925893)"
        },
        "popularity_score": 78
    },
    {
        "summary_article_gemini_title": "Celestial Spectacles Unveiled: Never Miss Earth's Most Dramatic Sky Events!",
        "article_html_file_location": "Celestial_Spectacles_Unveiled_Never_Miss_Earths_Mo.html",
        "summary_featured_image": {
            "url": "Sync_Your_Calendar_With_the_So_1.png",
            "alt": "LeapSecondDE",
            "caption": "LeapSecondDE"
        },
        "popularity_score": 88
    },
    {
        "summary_article_gemini_title": "Fashion's Revolution : The Rise of the Power Curve and the Redefinition of Feminine Strength for Fall 2025",
        "article_html_file_location": "style/Fashions_Revolution_The_Rise_of_the_Power_Curve_an.html",
        "summary_featured_image": None,
        "popularity_score": 80
    },
    {
        "summary_article_gemini_title": "From Music Mogul to Sports Scandal: The Tumultuous Tale of Norby Walters and the Collapse of an Empire",
        "article_html_file_location": "sports/ncaafootball/From_Music_Mogul_to_Sports_Scandal_The_Tumultuous_.html",
        "summary_featured_image": None,
        "popularity_score": 35
    },
    {
        "summary_article_gemini_title": "Echoes of Existence: Miguel Gutierrez 's Super Nothing Confronts Grief and Explodes with Queer Survival",
        "article_html_file_location": "arts/dance/Echoes_of_Existence_Miguel_Gutierrez_s_Super_Nothi.html",
        "summary_featured_image": {
            "url": "Miguel_Gutierrezs_Super_Nothin_1.jpg",
            "alt": "Miguel Sánchez-Ostiz",
            "caption": "Miguel Sánchez-Ostiz"
        },
        "popularity_score": 68
    },
    {
        "summary_article_gemini_title": "Urinetown's Revival : A Scathingly Funny , Shockingly Relevant Dive into Dystopia",
        "article_html_file_location": "theater/Urinetowns_Revival_A_Scathingly_Funny_Shockingly_R.html",
        "summary_featured_image": None,
        "popularity_score": 78
    },
    {
        "summary_article_gemini_title": "Texas Education Board Backs Bible-Infused Lessons in Public Schools",
        "article_html_file_location": "us/Texas_Education_Board_Backs_Bible-Infused_Lessons_.html",
        "summary_featured_image": None,
        "popularity_score": 0
    },
    {
        "summary_article_gemini_title": "Beyond Traditional Walls: How Microschools Are Redefining Education Amidst Choice, Controversy, and Parental Demand",
        "article_html_file_location": "us/Beyond_Traditional_Walls_How_Microschools_Are_Rede.html",
        "summary_featured_image": None,
        "popularity_score": 85
    },
    {
        "summary_article_gemini_title": "Alarm Bells Ring: Critics Denounce Trump Cabinet Nominees as Unqualified Sycophants Posing Unprecedented Danger",
        "article_html_file_location": "opinion/Alarm_Bells_Ring_Critics_Denounce_Trump_Cabinet_No.html",
        "summary_featured_image": None,
        "popularity_score": 85
    },
    {
        "summary_article_gemini_title": "Crisis Ignited: Trump Administration's Swift Cuts Imperil U.S. Wildfire Defenses, Sparking Fears of Uncontrollable Blazes",
        "article_html_file_location": "climate/Crisis_Ignited_Trump_Administrations_Swift_Cuts_Im.html",
        "summary_featured_image": None,
        "popularity_score": 78
    },
    {
        "summary_article_gemini_title": "The Unpredictable Arena: Why Expert Forecasts Often Fail and Surprises Reign Supreme",
        "article_html_file_location": "The_Unpredictable_Arena_Why_Expert_Forecasts_Often.html",
        "summary_featured_image": None,
        "popularity_score": 85
    },
    {
        "summary_article_gemini_title": "Terror in Room 1214 : A Teacher's Courage and a Lifeline Forged in the Parkland Massacre",
        "article_html_file_location": "health/Terror_in_Room_1214_A_Teachers_Courage_and_a_Lifel.html",
        "summary_featured_image": None,
        "popularity_score": 78
    },
    {
        "summary_article_gemini_title": "Ice Wars Erupt: Every Skater Ejected in Unprecedented NHL Chaos During Panthers vs. Senators Meltdown!",
        "article_html_file_location": "sports/hockey/Ice_Wars_Erupt_Every_Skater_Ejected_in_Unprecedent.html",
        "summary_featured_image": None,
        "popularity_score": 78
    },
    {
        "summary_article_gemini_title": "Diamond District Under Siege : Fencing Duo Accused of Fueling Transnational Burglary Ring Targeting Elite Homes, Linked to NFL Star Joe Burrow's Mansion Heist!",
        "article_html_file_location": "nyregion/Diamond_District_Under_Siege_Fencing_Duo_Accused_o.html",
        "summary_featured_image": None,
        "popularity_score": 78
    },
    {
        "summary_article_gemini_title": "Daughter of Pelicot Accuses Him of Rape in Police Complaint",
        "article_html_file_location": "world/europe/Daughter_of_Pelicot_Accuses_Him_of_Rape_in_Police_.html",
        "summary_featured_image": None,
        "popularity_score": 0
    },
    {
        "summary_article_gemini_title": "¡Revoluciona Tu Plato! Descubre las Potentes Proteínas que Destronan a la Carne Roja y Transforman Tu Salud",
        "article_html_file_location": "espanol/estilos-de-vida/Revoluciona_Tu_Plato_Descubre_las_Potentes_Proteín.html",
        "summary_featured_image": None,
        "popularity_score": 88
    },
    {
        "summary_article_gemini_title": "Bridget's Back! Navigating Love, Loss, and Laughter in \" Mad About the Boy \"",
        "article_html_file_location": "books/Bridgets_Back_Navigating_Love_Loss_and_Laughter_in.html",
        "summary_featured_image": None,
        "popularity_score": 88
    },
    {
        "summary_article_gemini_title": "Tragedy Amidst Turmoil: Inmate's Death at Auburn Facility Spotlights Deepening Crisis in New York Prisons",
        "article_html_file_location": "nyregion/Tragedy_Amidst_Turmoil_Inmates_Death_at_Auburn_Fac.html",
        "summary_featured_image": None,
        "popularity_score": 85
    },
    {
        "summary_article_gemini_title": "Transatlantic Tremors: How Trump Allies Shook the German Election with Far-Right Endorsements",
        "article_html_file_location": "world/europe/Transatlantic_Tremors_How_Trump_Allies_Shook_the_G.html",
        "summary_featured_image": None,
        "popularity_score": 75
    },
    {
        "summary_article_gemini_title": "The Calculated Ascent of Xabi Alonso: Patience, Pedigree, and the Explosion onto Europe's Coaching Scene",
        "article_html_file_location": "world/europe/The_Calculated_Ascent_of_Xabi_Alonso_Patience_Pedi.html",
        "summary_featured_image": None,
        "popularity_score": 95
    },
    {
        "summary_article_gemini_title": "‘Urinetown’ and Other Plays and Musicals to See in February",
        "article_html_file_location": "theater/Urinetown_and_Other_Plays_and_Musicals_to_See_in_F.html",
        "summary_featured_image": None,
        "popularity_score": 0
    },
    {
        "summary_article_gemini_title": "Metropolitan Opera Bets Big on Modernity: 2025-26 Season Blends Daring Premieres with Timeless Classics Amid Financial Realities",
        "article_html_file_location": "arts/music/Metropolitan_Opera_Bets_Big_on_Modernity_2025-26_S.html",
        "summary_featured_image": None,
        "popularity_score": 78
    },
    {
        "summary_article_gemini_title": "From Despair to Destiny: How a Letter to a Hockey Hero Saved a Life",
        "article_html_file_location": "From_Despair_to_Destiny_How_a_Letter_to_a_Hockey_H.html",
        "summary_featured_image": None,
        "popularity_score": 75
    },
    {
        "summary_article_gemini_title": "Shock Sentence : Pipe Bomber Who Targeted Japanese PM Gets 10 Years as Nation Grapples with Political Violence",
        "article_html_file_location": "world/asia/Shock_Sentence_Pipe_Bomber_Who_Targeted_Japanese_P.html",
        "summary_featured_image": None,
        "popularity_score": 65
    },
    {
        "summary_article_gemini_title": "Sarandí's Crimson Tide: Residents Horrified as Local Stream Turns Blood Red , Blame Industrial Pollution",
        "article_html_file_location": "world/americas/Sarandís_Crimson_Tide_Residents_Horrified_as_Local.html",
        "summary_featured_image": None,
        "popularity_score": 45
    },
    {
        "summary_article_gemini_title": "The Incredible Edible Egg : Debunking Cholesterol Myths and Unveiling a Nutritional Powerhouse",
        "article_html_file_location": "well/eat/The_Incredible_Edible_Egg_Debunking_Cholesterol_My.html",
        "summary_featured_image": None,
        "popularity_score": 82
    },
    {
        "summary_article_gemini_title": "Puerto Vallarta: From Hollywood Hideaway to Authentic Mexican Escape",
        "article_html_file_location": "travel/Puerto_Vallarta_From_Hollywood_Hideaway_to_Authentic.html",
        "summary_featured_image": None,
        "popularity_score": 78
    },
    {
        "summary_article_gemini_title": "Grit and Grace: Ashley Bouder's Turbulent Farewell from New York City Ballet After 25 Years",
        "article_html_file_location": "arts/dance/Grit_and_Grace_Ashley_Bouders_Turbulent_Farewell_f.html",
        "summary_featured_image": None,
        "popularity_score": 75
    },
    {
        "summary_article_gemini_title": "Tampa's Forgotten Fight: How Student Courage at a Woolworth's Counter Ignited Desegregation and Inspired a Landmark Play",
        "article_html_file_location": "theater/Tampas_Forgotten_Fight_How_Student_Courage_at_a_Wo.html",
        "summary_featured_image": None,
        "popularity_score": 65
    },
    {
        "summary_article_gemini_title": "Obsession & Artistry: Unmasking the Grueling World of Nick Gaga, Master Lady Gaga Impersonator",
        "article_html_file_location": "nyregion/Obsession_Artistry_Unmasking_the_Grueling_World_of.html",
        "summary_featured_image": None,
        "popularity_score": 65
    },
    {
        "summary_article_gemini_title": "Geopolitical Tensions Surge: The High-Stakes Scramble for Ukraine's Mineral Wealth Amid Shifting US-Russia Dynamics",
        "article_html_file_location": "business/dealbook/Geopolitical_Tensions_Surge_The_High-Stakes_Scramb.html",
        "summary_featured_image": None,
        "popularity_score": 85
    },
    {
        "summary_article_gemini_title": "Cupid Cancelled : Inside the Explosive Rise of Anti-Valentine's Day Events Defying Romance's Reign",
        "article_html_file_location": "dining/Cupid_Cancelled_Inside_the_Explosive_Rise_of_Anti-.html",
        "summary_featured_image": None,
        "popularity_score": 75
    },
    {
        "summary_article_gemini_title": "AI Funding Frenzy Rattled: DeepSeek's Low-Cost Breakthrough Sends Shockwaves Through Venture Capital",
        "article_html_file_location": "technology/AI_Funding_Frenzy_Rattled_DeepSeeks_Low-Cost_Break.html",
        "summary_featured_image": None,
        "popularity_score": 75
    },
    {
        "summary_article_gemini_title": "The Yellowjackets Are Back. Here’s Where They Left Off.",
        "article_html_file_location": "arts/television/The_Yellowjackets_Are_Back_Heres_Where_They_Left_O.html",
        "summary_featured_image": None,
        "popularity_score": 0
    },
    {
        "summary_article_gemini_title": "Seized Secrets Returned : FBI Delivers Mar-a-Lago Boxes to Trump After Explosive Charges Dropped",
        "article_html_file_location": "us/politics/Seized_Secrets_Returned_FBI_Delivers_Mar-a-Lago_Bo.html",
        "summary_featured_image": None,
        "popularity_score": 78
    },
    {
        "summary_article_gemini_title": "Trump Ignites Education Wars : Executive Orders Challenge Local Control and Spark Fierce Debate Over Race, Gender, and School Choice",
        "article_html_file_location": "us/Trump_Ignites_Education_Wars_Executive_Orders_Chal.html",
        "summary_featured_image": None,
        "popularity_score": 85
    },
    {
        "summary_article_gemini_title": "Unveiling the Shifting Face of Power: Documenting the Aesthetic Transformation of Federal Buildings During the Trump Transition",
        "article_html_file_location": "upshot/Unveiling_the_Shifting_Face_of_Power_Documenting_t.html",
        "summary_featured_image": None,
        "popularity_score": 65
    },
    {
        "summary_article_gemini_title": "Midlife Melancholy and Marital Mayhem: Inside Edward Burns's Millers in Marriage",
        "article_html_file_location": "movies/Midlife_Melancholy_and_Marital_Mayhem_Inside_Edwar.html",
        "summary_featured_image": None,
        "popularity_score": 45
    },
    {
        "summary_article_gemini_title": "Emerald Ambition, Golden Illusions: The Untold Story Behind the Witches of Oz",
        "article_html_file_location": "books/review/Emerald_Ambition_Golden_Illusions_The_Untold_Story.html",
        "summary_featured_image": None,
        "popularity_score": 95
    },
    {
        "summary_article_gemini_title": "The Fentanyl Nightmare: An Underused Lifeline in America's Deadliest Drug Crisis",
        "article_html_file_location": "magazine/The_Fentanyl_Nightmare_An_Underused_Lifeline_in_Am.html",
        "summary_featured_image": None,
        "popularity_score": 92
    },
    {
        "summary_article_gemini_title": "Love, Laughs, and Live Comedy : NYC's Valentine's Weekend Comedy Extravaganza",
        "article_html_file_location": "arts/Love_Laughs_and_Live_Comedy_NYCs_Valentines_Weeken.html",
        "summary_featured_image": None,
        "popularity_score": 78
    },
    {
        "summary_article_gemini_title": "High-Stakes Showdown: Ukraine Weighs Punishing US Deal Demanding Resource Billions Amidst War",
        "article_html_file_location": "world/europe/High-Stakes_Showdown_Ukraine_Weighs_Punishing_US_D.html",
        "summary_featured_image": None,
        "popularity_score": 75
    },
    {
        "summary_article_gemini_title": "Beyond the Fumble: How Rival Fans Rallied Around NFL Star Mark Andrews in an Unprecedented Act of Charity and Humanity After Playoff Heartbreak",
        "article_html_file_location": "sports/football/Beyond_the_Fumble_How_Rival_Fans_Rallied_Around_NF.html",
        "summary_featured_image": None,
        "popularity_score": 85
    },
    {
        "summary_article_gemini_title": "From Subway Shadow to Viral Spotlight: The Astonishing Saga of La Noxe, NYC's Secret Speakeasy Below the Sidewalk",
        "article_html_file_location": "realestate/From_Subway_Shadow_to_Viral_Spotlight_The_Astonish.html",
        "summary_featured_image": None,
        "popularity_score": 85
    }
]


# Sort articles by popularity (descending)
articles_data = sorted(articles_data, key=lambda x: x.get("popularity_score", 0), reverse=True)


# Preserve the original image URL in a new key if not already set
for article in articles_data:
    if article.get("summary_featured_image") and article["summary_featured_image"].get("url"):
        if "original_url" not in article["summary_featured_image"]:
            article["summary_featured_image"]["original_url"] = article["summary_featured_image"]["url"]



# Build featured_articles: take top 4 articles with a valid summary_featured_image
featured_articles = []
for article in articles_data:
    if article.get("summary_featured_image"):
        featured_articles.append(article)
    if len(featured_articles) >= 4:
        break

# Build additional_articles: remaining articles (up to 10) that are not in the featured list
featured_ids = {id(a) for a in featured_articles}
additional_articles = [a for a in articles_data if id(a) not in featured_ids][:10]


# Define directories for static images and category images
STATIC_IMAGE_DIR = os.path.join(package_root, "frontend", "web", "static", "images")
CATEGORY_IMAGES_DIR = os.path.join(package_root, "frontend", "web", "categories", "images")

# Define dimensions for top-level and subcategory images
# Define dimensions for main (top-level) and subcategory images
# Now main category images will be processed as 300x200
# and subcategory images as 400x300
TOP_LEVEL_WIDTH = 300
TOP_LEVEL_HEIGHT = 200
SUBCAT_WIDTH = 400
SUBCAT_HEIGHT = 300



def get_subcategory(article_html_file_location):
    parts = article_html_file_location.split("/")
    if len(parts) >= 3:
        return parts[1]  # using the second segment as subcategory
    elif len(parts) == 2:
        return parts[0]
    else:
        return "Uncategorized"

subcategories = {}
for article in articles_data:
    subcat = get_subcategory(article["article_html_file_location"])
    if subcat not in subcategories:
        subcategories[subcat] = []
    subcategories[subcat].append(article)

# For each subcategory, sort articles by popularity (descending) and split into "featured" and "others"
for key in subcategories:
    sorted_articles = sorted(subcategories[key], key=lambda x: x.get("popularity_score", 0), reverse=True)
    # Select only articles that have a valid featured image as featured articles (up to 2)
    featured = [art for art in sorted_articles if art.get("summary_featured_image")][:2]
    # All articles not in the featured list become others (preserving the original relevance order)
    others = [art for art in sorted_articles if art not in featured]
    subcategories[key] = {"featured": featured, "others": others}



# Removed the misplaced import statement
ensure_category_images_folder(CATEGORY_IMAGES_DIR)

# Process featured article images (for the top 4 articles)
for article in featured_articles:
    if article.get("summary_featured_image") and article["summary_featured_image"].get("url"):
        original_url = article["summary_featured_image"]["url"]
        if f"_{TOP_LEVEL_WIDTH}x{TOP_LEVEL_HEIGHT}" in original_url:
            logger.debug(f"Image already processed for article: {article['summary_article_gemini_title']}")
            article.setdefault("summary_featured_image_large", {})["url"] = original_url
            article.setdefault("summary_featured_image_large", {})["alt"] = article["summary_featured_image"].get("alt", "")
            article.setdefault("summary_featured_image_large", {})["caption"] = article["summary_featured_image"].get("caption", "")
        else:
            input_image = os.path.join(STATIC_IMAGE_DIR, original_url)
            output_image = os.path.join(CATEGORY_IMAGES_DIR, original_url)
            success = crop_and_resize_image(input_image, output_image, target_width=TOP_LEVEL_WIDTH, target_height=TOP_LEVEL_HEIGHT)
            if success:
                base, ext = os.path.splitext(original_url)
                new_filename = f"{base}_{TOP_LEVEL_WIDTH}x{TOP_LEVEL_HEIGHT}{ext}"
                article.setdefault("summary_featured_image_large", {})["url"] = new_filename
                article.setdefault("summary_featured_image_large", {})["alt"] = article["summary_featured_image"].get("alt", "")
                article.setdefault("summary_featured_image_large", {})["caption"] = article["summary_featured_image"].get("caption", "")
            else:
                logger.error(f"Failed to process top-level image for article: {article['summary_article_gemini_title']}")


relative_static_path = "../static"

# Process top-level featured article images with dimensions 400x300
for article in featured_articles:
    if article.get("summary_featured_image") and article["summary_featured_image"].get("url"):
        input_image = os.path.join(STATIC_IMAGE_DIR, article["summary_featured_image"]["url"])
        output_image = os.path.join(CATEGORY_IMAGES_DIR, article["summary_featured_image"]["url"])
        success = crop_and_resize_image(input_image, output_image, target_width=TOP_LEVEL_WIDTH, target_height=TOP_LEVEL_HEIGHT)
        if success:
            base, ext = os.path.splitext(article["summary_featured_image"]["url"])
            new_filename = f"{base}_{TOP_LEVEL_WIDTH}x{TOP_LEVEL_HEIGHT}{ext}"
            article.setdefault("summary_featured_image_large", {})["url"] = new_filename
            article.setdefault("summary_featured_image_large", {})["alt"] = article["summary_featured_image"].get("alt", "")
            article.setdefault("summary_featured_image_large", {})["caption"] = article["summary_featured_image"].get("caption", "")
        else:
            logger.error(f"Failed to process top-level image for article: {article['summary_article_gemini_title']}")

# Process subcategory featured article images with dimensions 300x200
# Process subcategory featured article images with dimensions 400x300 (SUBCAT dimensions)
for subcat, group in subcategories.items():
    for article in group.get("featured", []):
        # Use the preserved original URL
        if article.get("summary_featured_image") and article["summary_featured_image"].get("original_url"):
            original_url = article["summary_featured_image"]["original_url"]
        elif article.get("summary_featured_image") and article["summary_featured_image"].get("url"):
            original_url = article["summary_featured_image"]["url"]
        else:
            continue  # Skip if no image is available

        # Check if already processed for subcategory dimensions
        if f"_{SUBCAT_WIDTH}x{SUBCAT_HEIGHT}" in original_url:
            logger.debug(f"Subcategory image already processed for article: {article['summary_article_gemini_title']}")
            article.setdefault("summary_featured_image_small", {})["url"] = original_url
            article.setdefault("summary_featured_image_small", {})["alt"] = article["summary_featured_image"].get("alt", "")
            article.setdefault("summary_featured_image_small", {})["caption"] = article["summary_featured_image"].get("caption", "")
        else:
            input_image = os.path.join(STATIC_IMAGE_DIR, original_url)
            output_image = os.path.join(CATEGORY_IMAGES_DIR, original_url)
            success = crop_and_resize_image(input_image, output_image, target_width=SUBCAT_WIDTH, target_height=SUBCAT_HEIGHT)
            if success:
                base, ext = os.path.splitext(original_url)
                new_filename = f"{base}_{SUBCAT_WIDTH}x{SUBCAT_HEIGHT}{ext}"
                article.setdefault("summary_featured_image_small", {})["url"] = new_filename
                article.setdefault("summary_featured_image_small", {})["alt"] = article["summary_featured_image"].get("alt", "")
                article.setdefault("summary_featured_image_small", {})["caption"] = article["summary_featured_image"].get("caption", "")
            else:
                logger.error(f"Failed to process subcategory image for article: {article['summary_article_gemini_title']}")


# Prepare context for the template
context = {
    "category": {"name": "Top News"},  # or use a real category record
    "featured_articles": featured_articles,
    "subcategories": subcategories,
    "additional_articles": additional_articles,
    "relative_static_path": relative_static_path,
    "relative_articles_path": "../articles/",
    "relative_category_images_path": "images"
}


# Load and render the category template
try:
    template = jinja_env.get_template("category.html")
    rendered_html = template.render(context)
    logger.debug("Successfully rendered the category template.")
except Exception as e:
    logger.error(f"Error rendering template: {e}")
    sys.exit(1)

# Define the output file path
output_file_path = os.path.join(OUTPUT_CATEGORY_DIR, "category_test.html")

# Write the rendered HTML to the output file
try:
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    logger.debug(f"Category page generated at: {output_file_path}")
except Exception as e:
    logger.error(f"Error writing category page to file: {e}")
    sys.exit(1)
