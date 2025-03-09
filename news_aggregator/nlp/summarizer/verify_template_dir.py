import os

# Compute the BASE_DIR: two levels up from this script's directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Define the template directory relative to BASE_DIR
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'web', 'templates')

# Expected absolute path (adjust as needed for your system)
expected_path = r"C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\templates"

print("Computed TEMPLATE_DIR:", TEMPLATE_DIR)
print("Expected TEMPLATE_DIR:", expected_path)

if os.path.normcase(TEMPLATE_DIR) == os.path.normcase(expected_path):
    print("SUCCESS: TEMPLATE_DIR matches the expected path.")
else:
    print("ERROR: TEMPLATE_DIR does not match the expected path.")
