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
        
            # Add global HTML class requirements
        prompt += (
                "HTML CLASS REQUIREMENTS:\n"
                "1. Use ONLY the following specific CSS classes for each element - no variations or inline styles allowed:\n"
                "   - For titles: 'article-title'\n"
                "   - For source attribution: 'source-attribution' and 'label'\n"
                "   - For keywords: 'keywords-container', 'keywords-heading', 'keywords-tags', 'keyword-pill'\n"
                "   - For entity types: 'named-individual', 'roles-categories', 'orgs-products', 'location', 'time-event', 'artistic', 'industry', 'financial', 'key-actions'\n"
                "   - For summary elements: 'summary-intro', 'key-sentence', 'supporting-point', 'secondary-detail', 'crucial-fact'\n"
                "   - For interesting facts: 'facts-container', 'facts-list', 'fact-primary', 'fact-secondary', 'fact-conclusion'\n"
                "   - For separators: 'separator', 'divider', 'gradient-divider', 'facts-divider'\n"
                "   - For entity structure: 'entity-overview-heading', 'entity-grid', 'entity-category', 'entity-category-title', 'entity-list', 'no-entity'\n"
                "   - For miscellaneous elements: 'entity-spacing', 'transition-text', 'date-numeric', 'number-numeric', 'fact-bullet', 'fact-bullet-secondary'\n"
                "2. NEVER include any inline styles (style attribute) or custom classes not listed above.\n"
                "3. Always wrap your entire response in a single <div> element.\n"
                "4. Use EXACTLY these class names with no variations, additions, or modifications.\n\n"
            )
        
        # Add format restrictions for longer articles
        if article_length > 5000:
            prompt += (
                "CRITICAL FOR LONGER ARTICLES - FORMAT RESTRICTIONS:\n"
                "1. Return ONLY valid, complete HTML content with no markdown formatting whatsoever.\n"
                "2. DO NOT start your response with titles or headings outside of HTML tags.\n"
                "3. Ensure ALL formatting is done using HTML elements with ONLY the specific CSS classes defined in these instructions.\n"
                "4. Wrap your entire response in a single <div> element.\n"
                "5. Do not include ```html code blocks or any markdown syntax.\n"
                "6. Never use 'The article discusses the' or similar phrases to start your response. Just give summary without relating to source.\n" 
                "7. NEVER use inline styles (style attributes) in any element - use ONLY the specified CSS classes.\n"
                "Example: <div><h1 class=\"article-title\">Example Title</h1><p>Content here...</p></div>\n\n"
            )

        # Add title formatting instructions
        prompt += (
            "ENGAGING TITLE:\n"
            "1. Create a visually distinctive title using: '<h1 class=\"article-title\">[Title text]</h1>'\n"
            "2. The title should directly relate to the central issue or conflict in the article.\n"
            "3. Make it compelling and descriptive; it can be longer if needed and does not have to be in question format.\n"
            "4. For emphasis on key words in the title, use: '<span class=\"emphasis-keyword\">[key word]</span>'\n"
            "5. ALWAYS use the exact class name \"article-title\" for the h1 element and \"emphasis-keyword\" for emphasis spans - no variations.\n"
            "Example: <h1 class=\"article-title\">The <span class=\"emphasis-keyword\">Rise</span> and <span class=\"emphasis-keyword\">Fall</span> of a Tech Giant: A Story of Innovation and Intrigue</h1>\n\n"
        )
        
        # Add source attribution section
        prompt += (
            "SOURCE ATTRIBUTION SECTION:\n"
            "1. Immediately after the title, create a source attribution block using a <div> element (no class needed for this container div).\n"
            "2. Inside the div, create EXACTLY ONE paragraph with class \"source-attribution\" to display the source info.\n"
            "3. Within this paragraph, use <span class=\"label\"> elements ONLY for the labels \"Source:\" and \"Published:\".\n"
            "4. Use plain <span> elements (without classes) for the actual source name and publication date.\n"
            "5. The structure must be EXACTLY: <div><p class=\"source-attribution\"><span class=\"label\">Source:</span> <span>[SOURCE]</span> <span>|</span> <span class=\"label\">Published:</span> <span>[DATE]</span></p></div>\n"
            "6. Do not add any additional classes, elements, or styling to this section.\n"
            "Example: <div><p class=\"source-attribution\"><span class=\"label\">Source:</span> <span>Tesla, Inc.</span> <span>|</span> <span class=\"label\">Published:</span> <span>January 15, 2023</span></p></div>\n"
        )

        # Add source attribution guidelines
        prompt += (
            "7. For the original source, apply these STRICT guidelines:\n"
            "   - NEVER attribute to any news portals, websites, news organizations, or media outlets (such as The New York Times, BBC, PBS, etc.)\n"
            "   - NEVER attribute to photography sources, photographers, or image credits\n"
            "   - When source is known, attribute to the specific originating organization\n"
            "   - When source is unknown, attribute to ALL organizations mentioned in the title (separated by commas)\n"
            "   - If no organizations appear in the title, attribute to up to THREE most important organizations from the article body\n"
            "   - For government sources, ALWAYS specify which government (e.g., 'U.S. Department of Treasury' not just 'Government')\n"
            "   - Valid sources include: specific companies, named government agencies, industry associations, research institutions, regulatory bodies\n"
            "8. For the date:\n"
            "   - Use the format 'Month DD, YYYY' if the exact date is available\n"
            "   - If only the month and year are known, use 'Month YYYY'\n"
            "   - If date is completely unknown, use the current month and year (e.g., 'March 2025')\n"
            "9. Examples of CORRECT attribution:\n"
            "   - <div><p class=\"source-attribution\"><span class=\"label\">Source:</span> <span>Tesla, Inc.</span> <span>|</span> <span class=\"label\">Published:</span> <span>January 15, 2023</span></p></div>\n"
            "   - <div><p class=\"source-attribution\"><span class=\"label\">Source:</span> <span>World Health Organization, UNICEF, Doctors Without Borders</span> <span>|</span> <span class=\"label\">Published:</span> <span>February 2025</span></p></div>\n"
            "10. Examples of INCORRECT attribution (NEVER use these formats):\n"
            "   - Source: The New York Times | Published: April 26, 2024 (✗ - news portal)\n"
            "   - Source: Government Review | Published: February 28, 2024 (✗ - non-specific government)\n"
            "   - Source: James Lester Photography | Published: 2024 (✗ - photography source)\n\n"
        )
        
        
       
        # Add keywords section
        prompt += (
            "KEYWORDS SECTION:\n"
            "1. After the source attribution, create a keywords container using EXACTLY this structure: <div class=\"keywords-container\">...</div>\n"
            "2. Add a heading with EXACTLY: '<p class=\"keywords-heading\"><strong>Keywords:</strong></p>'\n"
            "3. Create a container for keyword tags using EXACTLY: <div class=\"keywords-tags\">...</div>\n"
            "4. Format each keyword as: '<span class=\"keyword-pill\">keyword</span>'\n"
            "5. Include 5-10 most frequently appearing significant words or phrases that are DIRECTLY RELATED to the main topic.\n"
            "6. Arrange keywords in order of relevance, with most important keywords first.\n"
            "7. Complete HTML structure must be:\n"
            "   <div class=\"keywords-container\">\n"
            "     <p class=\"keywords-heading\"><strong>Keywords:</strong></p>\n"
            "     <div class=\"keywords-tags\">\n"
            "       <span class=\"keyword-pill\">keyword1</span>\n"
            "       <span class=\"keyword-pill\">keyword2</span>\n"
            "       ...\n"
            "     </div>\n"
            "   </div>\n"
            "8. After the keywords container, add a visual separator with: <div class=\"separator\"></div>\n"
        )

        # Add entity overview section with entity containers
        prompt += (
            "ENTITY OVERVIEW SECTION:\n"
            "1. First identify and classify all key entities from the text into these categories, STRICTLY focusing on entities relevant to the CORE topic:\n"
            "   - NAMED INDIVIDUALS: Specific people mentioned by name who are central to the main story.\n"
            "   - ROLES & CATEGORIES: Occupations, types of people, or classifications that play a significant role in the core narrative.\n"
            "   - ORGANIZATIONS & PRODUCTS: Companies, brands, product types, and services that are directly involved in the main topic.\n"
            "   - LOCATIONS: Countries, cities, regions, or specific geographical places where key events in the main story occur.\n"
            "   - TIME PERIODS & EVENTS: Specific dates, time periods, seasons, or notable events that frame the central narrative.\n"
            "   - ARTISTIC CONCEPTS & DESIGN ELEMENTS: Aesthetic principles, design philosophies, or artistic movements central to the main topic.\n"
            "   - INDUSTRY TERMINOLOGY: Specialized terms and jargon specific to the industry being discussed that are essential to understanding the core topic.\n"
            "   - FINANCIAL & BUSINESS TERMS: Important business metrics, financial concepts, or market terminology directly relevant to the main narrative.\n"
            "   - KEY ACTIONS & RELATIONSHIPS: Verbs that show important actions or relationships between key entities in the core story.\n"
            "2. CRITICAL: Only include entities that are genuinely relevant to the core topic. Exclude entities that appear in tangential discussions, background information, or unrelated sections.\n"
            "3. Track the frequency and prominence of each entity throughout the text.\n"
            "4. Rank entities within each category based on importance (using factors such as frequency, prominence in headlines, or early mentions).\n"
        )
        
       # Add entity linking instructions based on setting
        if enable_entity_links:
            prompt += (
                "5. For each entity, create hyperlinks to external reference sources using EXACTLY these formats:\n"
                "   - For NAMED INDIVIDUALS: <strong class=\"named-individual\"><u><a href=\"https://en.wikipedia.org/wiki/[Entity_Name_Formatted]\" target=\"_blank\">[Entity Name]</a></u></strong>\n"
                "   - For ORGANIZATIONS & PRODUCTS: <strong class=\"orgs-products\"><a href=\"https://en.wikipedia.org/wiki/[Entity_Name_Formatted]\" target=\"_blank\">[Entity Name]</a></strong>\n"
                "   - For LOCATIONS: <strong class=\"location\"><a href=\"https://en.wikipedia.org/wiki/[Entity_Name_Formatted]\" target=\"_blank\">[Entity Name]</a></strong>\n"
                "   - When formatting Wikipedia URLs, replace spaces with underscores and handle special characters appropriately\n"
                "   - For entities unlikely to have dedicated Wikipedia pages, use appropriate alternative references or omit hyperlinks\n"
                "   - All other entity types must use the standard styling formats listed below WITHOUT hyperlinks\n"
            )
        else:
            prompt += (
                "5. Format EACH entity type using ONLY these EXACT HTML structures:\n"
                "   - NAMED INDIVIDUALS: <strong class=\"named-individual\"><u>[Name]</u></strong>\n"
                "   - ROLES & CATEGORIES: <strong class=\"roles-categories\">[Role]</strong>\n"
                "   - ORGANIZATIONS & PRODUCTS: <strong class=\"orgs-products\">[Organization]</strong>\n"
                "   - LOCATIONS: <strong class=\"location\">[Location]</strong>\n"
                "   - TIME PERIODS & EVENTS: <strong class=\"time-event\">[Time/Event]</strong>\n"
                "   - ARTISTIC CONCEPTS & DESIGN ELEMENTS: <strong class=\"artistic\">[Concept]</strong>\n"
                "   - INDUSTRY TERMINOLOGY: <strong class=\"industry\">[Term]</strong>\n"
                "   - FINANCIAL & BUSINESS TERMS: <strong class=\"financial\">[Term]</strong>\n"
                "   - KEY ACTIONS & RELATIONSHIPS: <strong class=\"key-actions\">[Action]</strong>\n"
                "   - Do NOT modify these class names or HTML structures in any way\n"
                "   - Do NOT add any additional classes, styles, or HTML elements\n\n"
            )
        # Add entity overview formatting instructions
        prompt += (
            "ENTITY OVERVIEW SECTION STRUCTURE:\n"
            "1. Create a section with EXACTLY this heading: '<strong class=\"entity-overview-heading\">Entity Overview:</strong>'\n"
            "2. Structure the entity display using this EXACT HTML pattern:\n"
            "   <div class=\"entity-grid\">\n"
            "     <div class=\"entity-category\">\n"
            "       <h3 class=\"entity-category-title\">CATEGORY NAME:</h3>\n"
            "       <p class=\"entity-list\">entity1, entity2, entity3</p>\n"
            "     </div>\n"
            "     <!-- Repeat for each category -->\n"
            "   </div>\n"
            "3. Use a separate <div class=\"entity-category\"> for EACH of the entity categories identified earlier.\n"
            "4. If a particular category has no relevant entities, use EXACTLY: '<em class=\"no-entity\">None identified</em>'\n"
            "5. Apply the entity styling formats defined earlier consistently for ALL mentions of entities.\n"
            "6. End this section with EXACTLY: <div class=\"divider\"></div>\n\n"
            
            "SUMMARY CREATION:\n"
            "1. Create a section with EXACTLY this heading: '<strong class=\"summary-heading\">Summary:</strong>'\n"
            "2. Write a comprehensive, detailed, and extended summary that thoroughly covers the central topic. Expand on key points with multiple paragraphs, elaborate supporting details, and extensive analysis..\n"
            "3. Structure your summary with these EXACT classes:\n"
            "   - First paragraph must use: <p class=\"summary-intro\">First paragraph content...</p>\n"
            "   - For key sentences: <span class=\"key-sentence\">Important sentence</span>\n"
            "   - For supporting points: <p class=\"supporting-point\">Supporting content...</p>\n"
            "   - For secondary details: <p class=\"secondary-detail\">Secondary information...</p>\n"
            "   - For numerical data: <span class=\"crucial-fact\">statistic or number</span>\n"
            "4. Include important details such as names, numbers, dates, organizations, and relationships related to the main topic.\n"
        )

        # Add different formatting based on entity links
        if enable_entity_links:
            prompt += (
                "5. Format all entities with appropriate styling and hyperlinks as defined in the Entity Overview section using the EXACT same HTML patterns and CSS classes.\n"
            )
        else:
            prompt += (
                "5. Format all named individuals EXACTLY as: '<strong class=\"named-individual\"><u>Name</u></strong>'\n"
                "6. Format all other entities using the EXACT HTML patterns for their respective categories as defined earlier.\n"
            )

        prompt += (
            "7. Use simple language and avoid overly complex or long sentences.\n"
            "8. For key entities that need emphasis, wrap them in EXACTLY: <span class=\"entity-spacing\">entity name</span>\n"
            "9. For transitions between major points, use EXACTLY: <p class=\"transition-text\">Transitional sentence...</p>\n"
            "10. CRITICAL: NEVER reference the source material. Do not use phrases like \"The article examines...\" \"The text discusses...\" \"The author argues...\" or any similar phrases that refer to the source content.\n"
            "11. Write directly about the subject matter as if presenting original information.\n"
            "12. IMPORTANT: Only reference entities that are directly relevant to the core topic.\n"
            "13. End the summary section with EXACTLY: <div class=\"gradient-divider\"></div>\n"
            "14. Every entity mentioned in the Entity Overview section must also appear and be properly formatted in the summary.\n\n"
        )
        
        
        # Add interesting facts section
        prompt += (
            "INTERESTING FACTS SECTION:\n"
            "1. Create a section with EXACTLY this heading: '<strong class=\"facts-heading\">Interesting Facts:</strong>'\n"
            "2. Structure the facts section using this EXACT HTML pattern:\n"
            "   <div class=\"facts-container\">\n"
            "     <ul class=\"facts-list\">\n"
            "       <li class=\"fact-primary\"><span class=\"fact-bullet\">●</span>First fact content...</li>\n"
            "       <li class=\"fact-secondary\"><span class=\"fact-bullet-secondary\">○</span>Second fact content...</li>\n"
            "       <li class=\"fact-conclusion\"><span class=\"fact-bullet\">●</span>Final important fact...</li>\n"
            "     </ul>\n"
            "   </div>\n"
            "3. Include 5-10 additional interesting facts about the subject matter.\n"
            "4. For each fact, alternate between the classes 'fact-primary' and 'fact-secondary', with the last fact using 'fact-conclusion'.\n"
            "5. Format all entity mentions using the EXACT same HTML patterns and class names as in the summary section.\n"
            "6. For dates, use: <span class=\"date-numeric\">date</span>\n"
            "7. For numbers and statistics, use: <span class=\"number-numeric\">number</span>\n"
            "8. CRITICAL: NEVER reference the source material. Present each fact as a direct statement about the subject matter.\n"
            "9. IMPORTANT: Only include facts that are directly relevant to the core topic.\n"
            "10. End this section with EXACTLY: <div class=\"facts-divider\"></div>\n"
        )

        prompt += "\nARTICLE TEXT:\n" + content + "\n"

        
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
        print(test_prompt[:50] + "...")
    else:
        print("Failed to create prompt.")
