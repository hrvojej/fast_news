import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nlp', 'summarizer'))
from summarizer_html import get_subfolder_from_url

test_urls = [
    # Reuters
    ("https://www.reuters.com/sports/dusty-may-informs-michigan-officials-intention-stay-put-spurn-unc--flm-2026-04-06/", "sports"),
    ("https://www.reuters.com/business/us-stock-futures-edge-up-investors-assess-mideast-ceasefire-prospects-2026-04-06/", "business"),
    ("https://www.reuters.com/world/americas/canada-could-face-long-term-political-challenges-2025-02-07/", "world/americas"),
    ("https://www.reuters.com/sustainability/boards-policy-regulation/investors-press-amazon-2026-04-06/", "sustainability/boards-policy-regulation"),
    # NYT (date-leading, should still work)
    ("https://www.nytimes.com/2025/02/14/climate/fema-quietly-eases-rules.html", "climate"),
    ("https://www.nytimes.com/2025/02/14/us/politics/some-article.html", "us/politics"),
    # CNN (date-leading)
    ("https://edition.cnn.com/2025/02/04/politics/cia-workforce-buyouts/index.html", "politics/cia-workforce-buyouts"),
    # Al Jazeera (date in middle)
    ("https://www.aljazeera.com/sports/2025/2/6/torres-hattrick-leads-barcelona", "sports"),
    # BBC
    ("https://www.bbc.com/news/world-europe-12345678", "news"),  # news is in skip list, so empty
    ("https://www.bbc.com/sport/football/some-article-slug", "sport/football"),
]

all_pass = True
for url, expected in test_urls:
    result = get_subfolder_from_url(url)
    status = "OK" if result == expected else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  {status}: {url[:70]}...")
    if status == "FAIL":
        print(f"         Expected: '{expected}', Got: '{result}'")

print(f"\n{'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
