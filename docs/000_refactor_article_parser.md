Before I start refactoring, could you please clarify a few details?

Do you want the new fetch/update script to be structured as a class with a run method (similar to how ABCRSSArticlesParser is built), encapsulating the fetching, parsing, and updating logic? Yes, but I want as much as possible, to extract common functionalities in separate modules like in example given. 
Should we reuse some of the common patterns from the RSS parser (like dynamic model creation and shared logging) in the refactored updater? Yes.
Are there any specific changes you want for the error handling, retries, or random sleeping behavior, or should these remain mostly the same? They remain same. 
Would you like to factor out any duplicated code (for example, updating the status record on error) into helper methods or a base class? Yes, as much as possible. Use /modules directory for that and give preposition of name of the helper script and their content. 
Keep on mind that you can also upgrade existing scripts in modules if needed - like base_parser.py or any other. 