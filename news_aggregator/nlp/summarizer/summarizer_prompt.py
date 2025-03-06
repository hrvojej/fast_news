"""
Module for generating prompts for the article summarization system.
This handles creation of prompts with appropriate formatting instructions.
Note: All inline styling has been extracted into CSS classes.
"""

from summarizer_logging import get_logger

logger = get_logger(__name__)

def create_prompt(content, article_length, include_images=True, enable_entity_links=True):
    """
    Create a detailed prompt for summarizing article content with advanced formatting.
    
    Args:
        content (str): The article content to be summarized.
        article_length (int): The length of the article in characters.
        include_images (bool): Whether to include image suggestions.
        enable_entity_links (bool): Whether to generate hyperlinks for entities.
    
    Returns:
        str: A formatted prompt for the language model, or None if creation fails.
    """
    if not content or not isinstance(content, str):
        logger.error("Invalid content provided to create_prompt: empty or not a string")
        return None
    
    if not isinstance(article_length, int) or article_length <= 0:
        logger.error(f"Invalid article_length provided: {article_length}")
        return None
    
    try:
        # Base prompt with main topic identification
        prompt = (
            "Create a focused, visually enhanced summary of the main topic from the following text using these guidelines:\n\n"
            
            "MAIN TOPIC IDENTIFICATION:\n"
            "1. Determine the central topic by analyzing the article title, introductory paragraphs, and recurring themes or keywords.\n"
            "2. Focus exclusively on the main narrative thread of the article, ignoring unrelated content that appears later.\n"
            "3. Pay attention to structural indicators that signal the end of the main article content.\n"
            "4. IMPORTANT: Only extract and include entities that are directly relevant to the core topic. DO NOT include entities that are merely mentioned in passing, appear in sidebar content, or are irrelevant to the main narrative.\n"
            "5. When writing the summary, NEVER refer to the source material using phrases like \"The article discusses...\" or \"The text explains...\" - instead, present information directly as facts about the subject matter.\n"
            "Example: Instead of identifying 'company's financial turnaround as discussed in the article', simply identify 'company's financial turnaround' as the central topic.\n\n"
        )
        
        # Add format restrictions for longer articles
        if article_length > 5000:
            prompt += (
                "CRITICAL FOR LONGER ARTICLES - FORMAT RESTRICTIONS:\n"
                "1. Return ONLY valid, complete HTML content with no markdown formatting whatsoever.\n"
                "2. DO NOT start your response with titles or headings outside of HTML tags.\n"
                "3. Ensure ALL formatting is done using HTML elements only.\n"
                "4. Wrap your entire response in a single <div> element.\n"
                "5. Do not include ```html code blocks or any markdown syntax.\n"
                "6. Never use 'The article discusses the' or similar phrases to start your response. Just give summary without relating to source. \n"
                "Example: <div><h1>Example Title</h1><p>Content here...</p></div>\n\n"
            )
        
        # Add title formatting instructions
        prompt += (
            "ENGAGING TITLE:\n"
            "1. Create a visually distinctive title using: '<h1 class=\"article-title\">[Title text]</h1>'\n"
            "2. The title should directly relate to the central issue or conflict in the article.\n"
            "3. Make it compelling and descriptive; it can be longer if needed and does not have to be in question format.\n"
            "4. Consider adding subtle emphasis to key words in the title using: '<span class=\"emphasis-keyword\">[key word]</span>'\n"
            "Example: <h1 class=\"article-title\">The <span class=\"emphasis-keyword\">Rise</span> and <span class=\"emphasis-keyword\">Fall</span> of a Tech Giant: A Story of Innovation and Intrigue</h1>\n\n"
        )
        
        # Add source attribution section
        prompt += (
            "SOURCE ATTRIBUTION SECTION:\n"
            "1. Immediately after the title, create a visually distinct source attribution block using a <div> element.\n"
            "2. Use a styled paragraph with class \"source-attribution\" to display the source info.\n"
            "3. Add a subtle label (with class \"label\") for Source and another for Published.\n"
            "Example: <div><p class=\"source-attribution\"><span class=\"label\">Source:</span> <span>[ORIGINAL SOURCE]</span> <span>|</span> <span class=\"label\">Published:</span> <span>[DATE]</span></p></div>\n"
        )
        
        # Add source attribution guidelines
        prompt += (
            "8. For the original source, apply these STRICT guidelines:\n"
            "   - NEVER attribute to any news portals, websites, news organizations, or media outlets (such as The New York Times, BBC, PBS, etc.)\n"
            "   - NEVER attribute to photography sources, photographers, or image credits\n"
            "   - When source is known, attribute to the specific originating organization\n"
            "   - When source is unknown, attribute to ALL organizations mentioned in the title (separated by commas)\n"
            "   - If no organizations appear in the title, attribute to up to THREE most important organizations from the article body\n"
            "   - For government sources, ALWAYS specify which government (e.g., 'U.S. Department of Treasury' not just 'Government')\n"
            "   - Valid sources include: specific companies, named government agencies, industry associations, research institutions, regulatory bodies\n"
            "9. For the date:\n"
            "   - Use the format 'Month DD, YYYY' if the exact date is available\n"
            "   - If only the month and year are known, use 'Month YYYY'\n"
            "   - If date is completely unknown, use the current month and year (e.g., 'March 2025')\n"
            "10. Examples of CORRECT attribution:\n"
            "   - <div><p class=\"source-attribution\"><span class=\"label\">Source:</span> <span>Tesla, Inc.</span> <span>|</span> <span class=\"label\">Published:</span> <span>January 15, 2023</span></p></div>\n"
            "   - <div><p class=\"source-attribution\"><span class=\"label\">Source:</span> <span>World Health Organization, UNICEF, Doctors Without Borders</span> <span>|</span> <span class=\"label\">Published:</span> <span>February 2025</span></p></div>\n"
            "11. Examples of INCORRECT attribution (NEVER use these formats):\n"
            "   - Source: The New York Times | Published: April 26, 2024 (✗ - news portal)\n"
            "   - Source: Government Review | Published: February 28, 2024 (✗ - non-specific government)\n"
            "   - Source: James Lester Photography | Published: 2024 (✗ - photography source)\n\n"
        )
        
        
       
        # Add keywords section
        prompt += (
            "KEYWORDS SECTION:\n"
            "1. After the source attribution, create a visually distinct keywords container using a CSS class 'keywords-container'.\n"
            "2. Add a heading with: '<p class=\"keywords-heading\"><strong>Keywords:</strong></p>'\n"
            "3. Create a flexible tag-like display for keywords with a container using class 'keywords-tags'.\n"
            "4. Format each keyword as a subtle pill-shaped tag using class 'keyword-pill'.\n"
            "5. Arrange keywords in order of relevance, with most important keywords first.\n"
            "6. Include 5-10 most frequently appearing significant words or phrases from the article that are DIRECTLY RELATED to the main topic.\n"
            "7. Close the container appropriately.\n"
            "8. End this section with a subtle visual separator using an element with class 'separator'.\n"
        )
        
        # Add entity overview section with entity containers
        prompt += (
            "ENTITY OVERVIEW SECTION:\n"
            "0. Identify and classify all key entities from the text into these categories, STRICTLY focusing on entities relevant to the CORE topic:\n"
            "   - NAMED INDIVIDUALS: Specific people mentioned by name who are central to the main story.\n"
            "   - ROLES & CATEGORIES: Occupations, types of people, or classifications that play a significant role in the core narrative.\n"
            "   - ORGANIZATIONS & PRODUCTS: Companies, brands, product types, and services that are directly involved in the main topic.\n"
            "   - LOCATIONS: Countries, cities, regions, or specific geographical places where key events in the main story occur.\n"
            "   - TIME PERIODS & EVENTS: Specific dates, time periods, seasons, or notable events that frame the central narrative.\n"
            "   - ARTISTIC CONCEPTS & DESIGN ELEMENTS: Aesthetic principles, design philosophies, or artistic movements central to the main topic.\n"
            "   - INDUSTRY TERMINOLOGY: Specialized terms and jargon specific to the industry being discussed that are essential to understanding the core topic.\n"
            "   - FINANCIAL & BUSINESS TERMS: Important business metrics, financial concepts, or market terminology directly relevant to the main narrative.\n"
            "   - KEY ACTIONS & RELATIONSHIPS: Verbs that show important actions or relationships between key entities in the core story.\n"
            "1. CRITICAL: Only include entities that are genuinely relevant to the core topic. Exclude entities that appear in tangential discussions, background information, or unrelated sections.\n"
            "2. Track the frequency and prominence of each entity throughout the text.\n"
            "3. Rank entities within each category based on importance (using factors such as frequency, prominence in headlines, or early mentions).\n"
        )
        
        # Add entity linking instructions based on setting
        if enable_entity_links:
            prompt += (
                "4. For each entity, create appropriate hyperlinks to external reference sources using the following formats:\n"
                "   - For NAMED INDIVIDUALS: <strong class=\"named-individual\"><u><a href=\"https://en.wikipedia.org/wiki/[Entity_Name_Formatted]\" target=\"_blank\">[Entity Name]</a></u></strong>\n"
                "   - For ORGANIZATIONS & PRODUCTS: <strong class=\"orgs-products\"><a href=\"https://en.wikipedia.org/wiki/[Entity_Name_Formatted]\" target=\"_blank\">[Entity Name]</a></strong>\n"
                "   - For LOCATIONS: <strong class=\"location\"><a href=\"https://en.wikipedia.org/wiki/[Entity_Name_Formatted]\" target=\"_blank\">[Entity Name]</a></strong>\n"
                "   - For other entity types, use the standard styling without hyperlinks\n"
                "   - When formatting Wikipedia URLs, replace spaces with underscores and handle special characters appropriately\n"
                "   - For entities unlikely to have dedicated Wikipedia pages, use appropriate alternative references or omit hyperlinks\n"
            )
        else:
            prompt += (
                "Examples:\n"
                "   - For NAMED INDIVIDUALS, list: <strong class=\"named-individual\"><u>John Doe</u></strong>, <strong class=\"named-individual\"><u>Jane Smith</u></strong>.\n"
                "   - For ROLES & CATEGORIES, list: <strong class=\"roles-categories\">Founder</strong>, <strong class=\"roles-categories\">Accountant</strong>.\n"
                "   - For ORGANIZATIONS & PRODUCTS, list: <strong class=\"orgs-products\">TechCorp</strong>, <strong class=\"orgs-products\">GadgetPro</strong>.\n"
                "   - For LOCATIONS, list: <strong class=\"location\">New York</strong>, <strong class=\"location\">Tokyo</strong>.\n"
                "   - For TIME PERIODS & EVENTS, list: <strong class=\"time-event\">2023</strong>, <strong class=\"time-event\">Fashion Week</strong>.\n"
                "   - For ARTISTIC CONCEPTS & DESIGN ELEMENTS, list: <strong class=\"artistic\">minimalism</strong>, <strong class=\"artistic\">avant-garde</strong>.\n"
                "   - For INDUSTRY TERMINOLOGY, list: <strong class=\"industry\">haute couture</strong>, <strong class=\"industry\">ready-to-wear</strong>.\n"
                "   - For FINANCIAL & BUSINESS TERMS, list: <strong class=\"financial\">acquisition</strong>, <strong class=\"financial\">market share</strong>.\n"
                "   - For KEY ACTIONS & RELATIONSHIPS, list: <strong class=\"key-actions\">acquired</strong>, <strong class=\"key-actions\">merged</strong>.\n\n"
            )
        
        # Add entity overview formatting instructions
        prompt += (
            "1. Create a section with the heading '<strong class=\"entity-overview-heading\">Entity Overview:</strong>' (styled as specified).\n"
            "2. Display entities in a visually structured format using a flexible grid-like approach with a container class 'entity-grid':\n"
            "   - For each category, use a container with class 'entity-category'.\n"
            "   - Include a title for each category with class 'entity-category-title'.\n"
            "   - List entities in a paragraph with class 'entity-list'.\n"
            "3. Apply consistent entity styling across all categories as previously defined, but with improved micro-typography.\n"
            "4. If a particular category has no relevant entities for the core topic, indicate this with '<em class=\"no-entity\">None identified</em>' after the colon.\n"
            "5. End this section with a visual divider using an element with class 'divider'.\n\n"
            
            "SUMMARY CREATION:\n"
            "1. Create a section with the heading '<strong class=\"summary-heading\">Summary:</strong>' (the heading must be bold).\n"
            "2. Write a focused, engaging summary that addresses ONLY the central topic identified earlier.\n"
            "3. Structure your summary with enhanced visual hierarchy using the following classes:\n"
            "   - FIRST PARAGRAPH: Use class 'summary-intro' with a larger font.\n"
            "   - KEY SENTENCES: Use class 'key-sentence' to emphasize important sentences.\n"
            "   - SUPPORTING PARAGRAPHS: Use classes 'supporting-point' for important supporting points and 'secondary-detail' for secondary details.\n"
            "   - CRUCIAL FACTS: Use class 'crucial-fact' for highlighting numerical data or statistics.\n"
            "4. Include important details such as names, numbers, dates, organizations, and relationships related to the main topic.\n"
        )
        
        # Add different formatting based on entity links
        if enable_entity_links:
            prompt += (
                "5. Format all entities with appropriate styling and hyperlinks as defined in the Entity Overview section using the designated CSS classes.\n"
            )
        else:
            prompt += (
                "5. Format all named individuals as bold AND underlined in their designated color using class 'named-individual' with EXACTLY this format: '<strong class=\"named-individual\"><u>Name</u></strong>'.\n"
                "6. Format all other entities according to their respective categories with appropriate CSS classes as defined in the Entity Overview section.\n"
            )
        
        prompt += (
            "7. Use simple and easy to understand phrases and language and avoid overly complex or long sentences.\n"
            "8. Create visual breathing room around key entities by adding a slight letter spacing using a span with class 'entity-spacing'.\n"
            "9. For transitional sentences between major ideas, use a paragraph with class 'transition-text'.\n"
            "10. CRITICAL: NEVER reference the source material. Do not use phrases like \"The article examines...\" \"The text discusses...\" \"The author argues...\" or any similar phrases that refer to the source content as an article, text, content, or document.\n"
            "11. Instead, write directly about the subject matter as if presenting original information. For example, instead of \"The article discusses Tesla's new battery technology\" write \"Tesla's new battery technology represents a significant breakthrough...\"\n"
            "12. IMPORTANT: Only reference entities that are directly relevant to the core topic. Do not mention entities that appeared in passing or in tangential discussions.\n"
            "13. End this section with a horizontal line using a gradient effect, represented by a divider with class 'gradient-divider'.\n"
            "14. Every entity mentioned in the 'ENTITY OVERVIEW SECTION' should also be present and properly formatted in the summary.\n\n"
        )
        
        
        # Add interesting facts section
        prompt += (
            "INTERESTING FACTS SECTION:\n"
            "1. Create a section with the heading '<strong class=\"facts-heading\">Interesting Facts:</strong>' (styled as specified).\n"
            "2. List 5-10 additional interesting facts using a visually engaging format with a container class 'facts-container':\n"
            "   - Use an unordered list with class 'facts-list'.\n"
            "   - For each fact, use list items with varying styles using classes 'fact-primary', 'fact-secondary', and 'fact-conclusion' respectively.\n"
            "3. Apply the same entity formatting as in the summary section for any entities mentioned in the facts.\n"
            "4. Use micro-typography to improve readability, with spans using classes 'date-numeric' and 'number-numeric' for dates and numbers respectively.\n"
            "5. CRITICAL: NEVER reference the source material. Do not use phrases like \"According to the article...\" \"The text mentions...\" or any similar phrases.\n"
            "6. Present each fact as a direct statement about the subject matter, not as information derived from a source.\n"
            "7. IMPORTANT: Only include facts that are directly relevant to the core topic. Exclude tangential or passing mentions.\n"
            "8. End this section with a visually distinct horizontal line using a divider with class 'facts-divider'.\n"
            "Example:\n"
            "   <div class=\"facts-container\">\n"
            "   <ul class=\"facts-list\">\n"
            "       <li class=\"fact-primary\"><span class=\"fact-bullet\">●</span><strong class=\"named-individual\"><u>John Doe</u></strong> was the youngest <strong class=\"roles-categories\">CEO</strong> in his industry in <span class=\"date-numeric\"><strong class=\"time-event\">2018</strong></span>.</li>\n"
            "       <li class=\"fact-secondary\"><span class=\"fact-bullet-secondary\">○</span><strong class=\"orgs-products\">Company XYZ</strong> set a record for quarterly <strong class=\"financial\">profits</strong> in <strong class=\"location\">Silicon Valley</strong>.</li>\n"
            "   </ul>\n"
            "   </div>\n"
            "   <div class=\"facts-divider\"></div>\n\n"
        )
        # Add legend section
        prompt += (
            "LEGEND SECTION:\n"
            "1. Create a visually distinctive legend section using a container with class 'legend-container':\n"
            "   - Add a heading with class 'legend-heading'.\n"
            "   - Create a responsive grid for entity types with class 'legend-grid'.\n"
            "   - For each entity type, create a styled container with class 'legend-item'.\n"
            "   - Include each entity type styled in its designated color.\n"
            "2. Close all containers appropriately.\n\n"
            
            "ARTICLE TEXT:\n" 
            + content + "\n"
        )
        
        # Return the complete prompt
        return prompt
        
    except Exception as e:
        logger.error(f"Error creating prompt: {e}", exc_info=True)
        return None

# For testing
if __name__ == "__main__":
    test_content = "This is a sample article content for testing."
    test_prompt = create_prompt(test_content, len(test_content))
    if test_prompt:
        print("Successfully created prompt.")
        print(f"Prompt length: {len(test_prompt)} characters")
        print("Prompt preview:")
        print(test_prompt[:500] + "...")
    else:
        print("Failed to create prompt.")
