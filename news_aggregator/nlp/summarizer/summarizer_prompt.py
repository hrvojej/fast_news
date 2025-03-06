"""
Module for generating prompts for the article summarization system.
This handles creation of prompts with appropriate formatting instructions.
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
                "6. Never use 'The article discusses the' or simillar phrases to start your response. Just give summary without relating to source. \n"
                "Example: <div><h1>Example Title</h1><p>Content here...</p></div>\n\n"
            )
        
        # Add title formatting instructions
        prompt += (
            "ENGAGING TITLE:\n"
            "1. Create a visually distinctive title using: '<h1 style=\"font-size:1.5em; line-height:1.3; margin-bottom:0.7em; letter-spacing:0.02em; position:relative; padding-bottom:0.5em; border-bottom:1px solid #f0f0f0;\">[Title text]</h1>'\n"
            "2. The title should directly relate to the central issue or conflict in the article.\n"
            "3. Make it compelling and descriptive; it can be longer if needed and does not have to be in question format.\n"
            "4. Consider adding subtle emphasis to key words in the title: '<span style=\"border-bottom:2px solid #f0f0f0;\">[key word]</span>'\n"
            "Example: <h1 style=\"font-size:1.5em; line-height:1.3; margin-bottom:0.7em; letter-spacing:0.02em; position:relative; padding-bottom:0.5em; border-bottom:1px solid #f0f0f0;\">The <span style=\"border-bottom:2px solid #f0f0f0;\">Rise</span> and <span style=\"border-bottom:2px solid #f0f0f0;\">Fall</span> of a Tech Giant: A Story of Innovation and Intrigue</h1>\n\n"
        )
        
        # Add source attribution section
        prompt += (
            "SOURCE ATTRIBUTION SECTION:\n"
            "1. Immediately after the title, create a visually distinct source attribution block: '<div style=\"margin:0.2em 0 1em 0; padding-bottom:0.8em;\">\n"
            "2. Use a styled format with subtle typography: '<p style=\"color:#555555; font-style:italic; font-size:0.9em; margin:0; display:flex; flex-wrap:wrap; gap:0.6em;\">\n"
            "3. Add a subtle label with right spacing: '<span style=\"color:#777777; font-weight:500; letter-spacing:0.02em; margin-right:0.3em;\">Source:</span>'\n"
            "4. Format organization names with proper styling: '<span style=\"color:#555555; letter-spacing:0.01em;\">[ORIGINAL SOURCE]</span>'\n"
            "5. Add a subtle separator: '<span style=\"color:#cccccc; margin:0 0.3em;\">|</span>'\n"
            "6. Add a date label with right spacing: '<span style=\"color:#777777; font-weight:500; letter-spacing:0.02em; margin-right:0.3em;\">Published:</span>'\n"
            "7. Format the date with proper styling: '<span style=\"color:#555555; letter-spacing:0.01em;\">[DATE]</span></p></div>'\n"
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
            "   - <div style=\"margin:0.2em 0 1em 0; padding-bottom:0.8em;\">\n"
            "     <p style=\"color:#555555; font-style:italic; font-size:0.9em; margin:0; display:flex; flex-wrap:wrap; gap:0.5em; align-items:center;\">\n"
            "     <span style=\"color:#777777; font-weight:500; letter-spacing:0.02em; margin-right:0.3em;\">Source:</span>\n"
            "     <span style=\"color:#555555; letter-spacing:0.01em;\">Tesla, Inc.</span>\n"
            "     <span style=\"color:#cccccc; margin:0 0.3em;\">|</span>\n"
            "     <span style=\"color:#777777; font-weight:500; letter-spacing:0.02em; margin-right:0.3em;\">Published:</span>\n"
            "     <span style=\"color:#555555; letter-spacing:0.01em;\">January 15, 2023</span></p></div>\n"
            "   - <div style=\"margin:0.2em 0 1em 0; padding-bottom:0.8em;\">\n"
            "     <p style=\"color:#555555; font-style:italic; font-size:0.9em; margin:0; display:flex; flex-wrap:wrap; gap:0.5em; align-items:center;\">\n"
            "     <span style=\"color:#777777; font-weight:500; letter-spacing:0.02em; margin-right:0.3em;\">Source:</span>\n"
            "     <span style=\"color:#555555; letter-spacing:0.01em;\">World Health Organization, UNICEF, Doctors Without Borders</span>\n"
            "     <span style=\"color:#cccccc; margin:0 0.3em;\">|</span>\n"
            "     <span style=\"color:#777777; font-weight:500; letter-spacing:0.02em; margin-right:0.3em;\">Published:</span>\n"
            "     <span style=\"color:#555555; letter-spacing:0.01em;\">February 2025</span></p></div>\n"
            "11. Examples of INCORRECT attribution (NEVER use these formats):\n"
            "   - Source: The New York Times | Published: April 26, 2024 (✗ - news portal)\n"
            "   - Source: Government Review | Published: February 28, 2024 (✗ - non-specific government)\n"
            "   - Source: James Lester Photography | Published: 2024 (✗ - photography source)\n\n"
        )
        
        # Add featured image section if requested
        if include_images:
            prompt += (
            "FEATURED IMAGE SECTION:\n"
            "1. After source attribution, search for and retrieve a high-quality, relevant image based on the article title and main topic.\n"
            "2. The image must be freely usable (Creative Commons, public domain, or similar license).\n"
            "3. Instead of embedding the image in HTML, return only the direct URL of the image as plain text. (For reference, you might consider the following HTML format for placement: '<div style=\"text-align:center; margin:1.2em 0 1.8em 0;\"><img src=\"[IMAGE_URL]\" alt=\"[DESCRIPTIVE ALT TEXT]\" style=\"max-width:100%; border-radius:6px; box-shadow:0 2px 12px rgba(0,0,0,0.1);\"></div>', but your output should consist solely of the image URL.)\n"
            "4. Additionally, provide a detailed alt text description of the image content related to the article topic as a separate sentence after the URL, if possible.\n"
            "5. Follow these cognitive science principles for image selection:\n"
            "   - Choose images that directly relate to the central topic\n"
            "   - Select images with clear focal points that draw attention\n"
            "   - Prefer images with emotional resonance related to the content tone\n"
            "   - Select images with appropriate color psychology for the subject matter\n"
            "   - Avoid images with excessive visual complexity that could distract\n"
            "6. If no suitable image can be found, omit this section entirely rather than using an irrelevant image.\n"
            "7. The very first line of your entire output must be the featured image URL (or an empty line if none is found), and the second line (if applicable) should be the alt text description.\n"
            "8. Immediately after these, output a marker line that reads exactly '---END IMAGE URL---' before continuing with the rest of the summary.\n\n"
            "9. Return a URL that, when opened in a browser, displays a high-quality image. \n\n"
            )
        
        # Add keywords section
        prompt += (
            "KEYWORDS SECTION:\n"
            "1. After the source attribution, create a visually distinct keywords container: '<div style=\"background-color:#fafafa; border-radius:4px; padding:0.7em 1em; margin:0.8em 0 1.2em 0;\">\n"
            "2. Add a heading with: '<p style=\"margin:0 0 0.4em 0;\"><strong style=\"letter-spacing:0.03em;\">Keywords:</strong></p>'\n"
            "3. Create a flexible tag-like display for keywords: '<div style=\"display:flex; flex-wrap:wrap; gap:0.5em;\">\n"
            "4. Format each keyword as a subtle pill-shaped tag: '<span style=\"display:inline-block; background-color:white; border:1px solid #eaeaea; border-radius:50px; padding:0.2em 0.8em; font-size:0.9em;\">[keyword]</span>'\n"
            "5. Arrange keywords in order of relevance, with most important keywords first.\n"
            "6. Include 5-10 most frequently appearing significant words or phrases from the article that are DIRECTLY RELATED to the main topic.\n"
            "7. Close all div containers appropriately: '</div></div>'\n"
            "8. End this section with a subtle visual separator: '<div style=\"height:1px; background-color:#f0f0f0; margin:1.2em 0;\"></div>'\n"
        )
        
        # Add example for keywords section
        prompt += (
            "Example: \n"
            "<div style=\"background-color:#fafafa; border-radius:4px; padding:0.7em 1em; margin:0.8em 0 1.2em 0;\">\n"
            "<p style=\"margin:0 0 0.4em 0;\"><strong style=\"letter-spacing:0.03em;\">Keywords:</strong></p>\n"
            "<div style=\"display:flex; flex-wrap:wrap; gap:0.5em;\">\n"
            "<span style=\"display:inline-block; background-color:white; border:1px solid #eaeaea; border-radius:50px; padding:0.2em 0.8em; font-size:0.9em;\">innovation</span>\n"
            "<span style=\"display:inline-block; background-color:white; border:1px solid #eaeaea; border-radius:50px; padding:0.2em 0.8em; font-size:0.9em;\">turnaround</span>\n"
            "<span style=\"display:inline-block; background-color:white; border:1px solid #eaeaea; border-radius:50px; padding:0.2em 0.8em; font-size:0.9em;\">profit</span>\n"
            "<span style=\"display:inline-block; background-color:white; border:1px solid #eaeaea; border-radius:50px; padding:0.2em 0.8em; font-size:0.9em;\">market</span>\n"
            "<span style=\"display:inline-block; background-color:white; border:1px solid #eaeaea; border-radius:50px; padding:0.2em 0.8em; font-size:0.9em;\">growth</span>\n"
            "</div>\n"
            "</div>\n"
            "<div style=\"height:1px; background-color:#f0f0f0; margin:1.2em 0;\"></div>\n\n"
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
                "   - For NAMED INDIVIDUALS: <strong style=\"color:#D55E00\"><u><a href=\"https://en.wikipedia.org/wiki/[Entity_Name_Formatted]\" target=\"_blank\" style=\"color:#D55E00; text-decoration:underline;\">[Entity Name]</a></u></strong>\n"
                "   - For ORGANIZATIONS & PRODUCTS: <strong style=\"color:#009E73\"><a href=\"https://en.wikipedia.org/wiki/[Entity_Name_Formatted]\" target=\"_blank\" style=\"color:#009E73;\">[Entity Name]</a></strong>\n"
                "   - For LOCATIONS: <strong style=\"color:#56B4E9\"><a href=\"https://en.wikipedia.org/wiki/[Entity_Name_Formatted]\" target=\"_blank\" style=\"color:#56B4E9;\">[Entity Name]</a></strong>\n"
                "   - For other entity types, use the standard styling without hyperlinks\n"
                "   - When formatting Wikipedia URLs, replace spaces with underscores and handle special characters appropriately\n"
                "   - For entities unlikely to have dedicated Wikipedia pages, use appropriate alternative references or omit hyperlinks\n"
            )
        else:
            prompt += (
                "Examples:\n"
                "   - For NAMED INDIVIDUALS, list: <strong style=\"color:#D55E00\"><u>John Doe</u></strong>, <strong style=\"color:#D55E00\"><u>Jane Smith</u></strong>.\n"
                "   - For ROLES & CATEGORIES, list: <strong style=\"color:#0072B2\">Founder</strong>, <strong style=\"color:#0072B2\">Accountant</strong>.\n"
                "   - For ORGANIZATIONS & PRODUCTS, list: <strong style=\"color:#009E73\">TechCorp</strong>, <strong style=\"color:#009E73\">GadgetPro</strong>.\n"
                "   - For LOCATIONS, list: <strong style=\"color:#56B4E9\">New York</strong>, <strong style=\"color:#56B4E9\">Tokyo</strong>.\n"
                "   - For TIME PERIODS & EVENTS, list: <strong style=\"color:#E69F00\">2023</strong>, <strong style=\"color:#E69F00\">Fashion Week</strong>.\n"
                "   - For ARTISTIC CONCEPTS & DESIGN ELEMENTS, list: <strong style=\"color:#F0E442\">minimalism</strong>, <strong style=\"color:#F0E442\">avant-garde</strong>.\n"
                "   - For INDUSTRY TERMINOLOGY, list: <strong style=\"color:#8AE68A\">haute couture</strong>, <strong style=\"color:#8AE68A\">ready-to-wear</strong>.\n"
                "   - For FINANCIAL & BUSINESS TERMS, list: <strong style=\"color:#666666\">acquisition</strong>, <strong style=\"color:#666666\">market share</strong>.\n"
                "   - For KEY ACTIONS & RELATIONSHIPS, list: <strong style=\"color:#CC79A7\">acquired</strong>, <strong style=\"color:#CC79A7\">merged</strong>.\n\n"
            )
        
        # Add entity overview formatting instructions
        prompt += (
            "1. Create a section with the heading '<strong style=\"font-size:1.15em; letter-spacing:0.03em;\">Entity Overview:</strong>' (styled as specified).\n"
            "2. Display entities in a visually structured format using a flexible grid-like approach:\n"
            "   - Container: '<div style=\"display:flex; flex-wrap:wrap; gap:0.8em; margin:1em 0;\">\n"
            "   - For each category: '<div style=\"flex:1; min-width:275px; margin-bottom:0.5em;\">\n"
            "   - Category title: '<p style=\"margin:0 0 0.3em 0; padding-bottom:0.2em; border-bottom:1px solid #eaeaea;\"><strong style=\"color:[CATEGORY_COLOR];\">[Category Name]:</strong></p>'\n"
            "   - Entity list: '<p style=\"margin:0; line-height:1.5;\">[entities with appropriate formatting, comma-separated]</p></div>'\n"
            "3. Apply consistent entity styling across all categories as previously defined, but with improved micro-typography:\n"
            "   - Add subtle letter-spacing to category titles: letter-spacing:0.02em;\n"
            "   - Use a slightly larger font (1.05em) for the most important entity in each category\n"
            "   - Apply a subtle background highlight to the most important entity in each category: background-color:rgba(230,230,230,0.2);\n"
            "4. If a particular category has no relevant entities for the core topic, indicate this with '<em style=\"color:#999; font-size:0.9em;\">None identified</em>' after the colon.\n"
            "5. End this section with a visual divider: '<hr style=\"height:1px; border:none; background-color:#eaeaea; margin:1.2em 0;\">'.\n\n"
            
            "SUMMARY CREATION:\n"
            "1. Create a section with the heading '<strong>Summary:</strong>' (the heading must be bold).\n"
            "2. Write a focused, engaging summary that addresses ONLY the central topic identified earlier.\n"
            "3. Structure your summary with enhanced visual hierarchy:\n"
            "   - FIRST PARAGRAPH: Present the core meaning or main point in a larger font using this format: '<p style=\"font-size:1.2em; line-height:1.5; margin-bottom:1.2em;\">[First paragraph content]</p>'\n"
            "   - KEY SENTENCES: For particularly important sentences within paragraphs, use: '<span style=\"letter-spacing:0.03em; font-weight:500;\">[Key sentence]</span>'\n"
            "   - SUBSEQUENT PARAGRAPHS: For supporting paragraphs, use varying visual weights:\n"
            "     * Important supporting points: '<p style=\"margin-bottom:1em; padding-left:0.8em; border-left:3px solid #eeeeee;\">[Content]</p>'\n"
            "     * Secondary details: '<p style=\"font-size:0.95em; line-height:1.4; margin-bottom:0.8em;\">[Content]</p>'\n"
            "   - CRUCIAL FACTS: Highlight crucial numerical data or statistics with: '<span style=\"font-variant-numeric:tabular-nums; background-color:#f8f8f8; padding:0px 3px;\">[numerical data]</span>'\n"
            "4. Include important details such as names, numbers, dates, organizations, and relationships related to the main topic.\n"
        )
        
        # Add different formatting based on entity links
        if enable_entity_links:
            prompt += (
                "5. Format all entities with appropriate styling and hyperlinks as defined in the Entity Overview section.\n"
            )
        else:
            prompt += (
                "5. Format all named individuals as bold AND underlined in their designated color (#D55E00) using EXACTLY this format: '<strong style=\"color:#D55E00\"><u>Name</u></strong>'.\n"
                "6. Format all other entities according to their respective categories with appropriate colors as defined in the Entity Overview section.\n"
            )
        
        prompt += (
            "7. Use simple language and avoid overly complex or long sentences.\n"
            "8. Create visual breathing room around key entities by adding a slight letter spacing: '<span style=\"letter-spacing:0.05em;\">[entity]</span>'\n"
            "9. For transitional sentences between major ideas, use: '<p style=\"font-size:0.9em; font-style:italic; margin:1em 0;\">[Transition text]</p>'\n"
            "10. CRITICAL: NEVER reference the source material. Do not use phrases like \"The article examines...\" \"The text discusses...\" \"The author argues...\" or any similar phrases that refer to the source content as an article, text, content, or document.\n"
            "11. Instead, write directly about the subject matter as if presenting original information. For example, instead of \"The article discusses Tesla's new battery technology\" write \"Tesla's new battery technology represents a significant breakthrough...\"\n"
            "12. IMPORTANT: Only reference entities that are directly relevant to the core topic. Do not mention entities that appeared in passing or in tangential discussions.\n"
            "13. End this section with a horizontal line using a gradient effect: '<hr style=\"height:3px; border:none; background: linear-gradient(to right, #f5f5f5, #dddddd, #f5f5f5);\">'.\n"
            "14. Every entity mentioned in 'ENTITY OVERVIEW SECTION' should also be present and properly formatted in the summary.\n\n"
        )
        
        # Add supporting images section if requested
        if include_images:
            prompt += (
                "SUPPORTING IMAGES SECTION:\n"
                "1. Identify 1-2 additional relevant images that illustrate key aspects or details from the summary.\n"
                "2. Place these images strategically within or after the summary section using:\n"
                "   - For left alignment: '<div style=\"float:left; margin:0.5em 1.5em 1em 0; max-width:40%;\"><img src=\"[IMAGE_URL]\" alt=\"[ALT TEXT]\" style=\"width:100%; border-radius:4px; box-shadow:0 2px 6px rgba(0,0,0,0.08);\"><p style=\"font-size:0.8em; margin-top:0.3em; color:#666; text-align:center;\">[CAPTION]</p></div>'\n"
                "   - For right alignment: '<div style=\"float:right; margin:0.5em 0 1em 1.5em; max-width:40%;\"><img src=\"[IMAGE_URL]\" alt=\"[ALT TEXT]\" style=\"width:100%; border-radius:4px; box-shadow:0 2px 6px rgba(0,0,0,0.08);\"><p style=\"font-size:0.8em; margin-top:0.3em; color:#666; text-align:center;\">[CAPTION]</p></div>'\n"
                "3. Follow these placement principles:\n"
                "   - Position images adjacent to related text content\n"
                "   - Alternate alignment (left/right) if using multiple images\n"
                "   - Ensure adequate spacing between images and text\n"
                "   - Use appropriate image sizes that complement without overwhelming text\n"
                "4. Provide informative captions that add context beyond what's visible in the image\n"
                "5. Include descriptive alt text for accessibility\n"
                "6. Only include images that enhance understanding of the content; omit if no relevant images are available\n\n"
            )
        
        # Add interesting facts section
        prompt += (
            "INTERESTING FACTS SECTION:\n"
            "1. Create a section with the heading '<strong style=\"font-size:1.1em; letter-spacing:0.05em;\">Interesting Facts:</strong>' (styled as specified).\n"
            "2. List 5-10 additional interesting facts using a visually engaging format:\n"
            "   - Container: '<div style=\"background:linear-gradient(to right, #fafafa, white); padding:1em; border-radius:5px; margin:1em 0;\">\n"
            "   - Use a custom-styled unordered list: '<ul style=\"list-style:none; padding-left:0;\">\n"
            "   - For each fact, create visual interest with varying styles:\n"
            "     * First and important facts: '<li style=\"margin-bottom:1em; padding-left:1.5em; position:relative;\"><span style=\"position:absolute; left:0; color:#888;\">●</span>[Fact content]</li>'\n"
            "     * Secondary facts: '<li style=\"margin-bottom:0.8em; padding-left:1.5em; position:relative; font-size:0.95em;\"><span style=\"position:absolute; left:0; color:#aaa;\">○</span>[Fact content]</li>'\n"
            "     * Final fact (conclusion): '<li style=\"margin-bottom:0; padding-left:1.5em; position:relative; font-weight:500;\"><span style=\"position:absolute; left:0; color:#888;\">●</span>[Fact content]</li>'\n"
            "3. Apply the same entity formatting as in the summary section for any entities mentioned in the facts.\n"
            "4. Use micro-typography to improve readability:\n"
            "   - For dates: '<span style=\"font-variant-numeric:tabular-nums;\">[date]</span>'\n"
            "   - For percentages/numbers: '<span style=\"font-variant-numeric:tabular-nums; letter-spacing:0.03em;\">[number]</span>'\n"
            "5. CRITICAL: NEVER reference the source material. Do not use phrases like \"According to the article...\" \"The text mentions...\" or any similar phrases that refer to the source content.\n"
            "6. Present each fact as a direct statement about the subject matter, not as information derived from a source.\n"
            "7. IMPORTANT: Only include facts that are directly relevant to the core topic. Exclude tangential or passing mentions.\n"
            "8. End this section with a visually distinct horizontal line: '<hr style=\"height:2px; border:none; background: linear-gradient(to right, #ffffff, #e0e0e0, #ffffff); margin:1.5em 0;\">'.\n"
            "Example:\n"
            "   <div style=\"background:linear-gradient(to right, #fafafa, white); padding:1em; border-radius:5px; margin:1em 0;\">\n"
            "   <ul style=\"list-style:none; padding-left:0;\">\n"
            "       <li style=\"margin-bottom:1em; padding-left:1.5em; position:relative;\"><span style=\"position:absolute; left:0; color:#888;\">●</span><strong style=\"color:#D55E00\"><u>John Doe</u></strong> was the youngest <strong style=\"color:#0072B2\">CEO</strong> in his industry in <span style=\"font-variant-numeric:tabular-nums;\"><strong style=\"color:#E69F00\">2018</strong></span>.</li>\n"
            "<li style=\"margin-bottom:0.8em; padding-left:1.5em; position:relative; font-size:0.95em;\"><span style=\"position:absolute; left:0; color:#aaa;\">"
            "○</span><strong style=\"color:#009E73\">Company XYZ</strong> set a record for quarterly <strong style=\"color:#666666\">profits</strong> in <strong style=\"color:#56B4E9\">Silicon Valley</strong>.</li> </ul> </div> <hr style=\"height:2px; border:none; background: linear-gradient(to right, #ffffff, #e0e0e0, #ffffff); margin:1.5em 0;\">\n\n"
        )
        # Add legend section
        prompt += (
            "LEGEND SECTION:\n"
            "1. Create a visually distinctive legend section using: '<div style=\"background-color:#f9f9f9; border-radius:4px; padding:0.8em; margin:1.2em 0;\">\n"
            "2. Add a heading with: '<p style=\"margin:0 0 0.5em 0;\"><strong style=\"font-size:1.05em; letter-spacing:0.02em;\">Legend:</strong></p>'\n"
            "3. Create a flexible, responsive grid for entity types: '<div style=\"display:flex; flex-wrap:wrap; gap:0.6em;\">\n"
            "4. For each entity type, create a styled container: '<div style=\"flex:1; min-width:175px; background-color:white; padding:0.5em; border-radius:3px; box-shadow:0 1px 2px rgba(0,0,0,0.05);\">\n"
            "5. Include each entity type styled in its designated color with enhanced spacing:\n"
            "   - '<div style=\"text-align:center;\"><strong style=\"color:#D55E00; letter-spacing:0.02em;\">Named Individuals</strong></div>'\n"
            "   - '<div style=\"text-align:center;\"><strong style=\"color:#0072B2; letter-spacing:0.02em;\">Roles & Categories</strong></div>'\n"
            "   - '<div style=\"text-align:center;\"><strong style=\"color:#009E73; letter-spacing:0.02em;\">Organizations & Products</strong></div>'\n"
            "   - '<div style=\"text-align:center;\"><strong style=\"color:#56B4E9; letter-spacing:0.02em;\">Locations</strong></div>'\n"
            "   - '<div style=\"text-align:center;\"><strong style=\"color:#E69F00; letter-spacing:0.02em;\">Time Periods & Events</strong></div>'\n"
            "   - '<div style=\"text-align:center;\"><strong style=\"color:#F0E442; letter-spacing:0.02em;\">Artistic Concepts & Design Elements</strong></div>'\n"
            "   - '<div style=\"text-align:center;\"><strong style=\"color:#8AE68A; letter-spacing:0.02em;\">Industry Terminology</strong></div>'\n"
            "   - '<div style=\"text-align:center;\"><strong style=\"color:#666666; letter-spacing:0.02em;\">Financial & Business Terms</strong></div>'\n"
            "   - '<div style=\"text-align:center;\"><strong style=\"color:#CC79A7; letter-spacing:0.02em;\">Key Actions & Relationships</strong></div>'\n"
            "6. Close all div containers appropriately: '</div></div></div>'\n\n"
            
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