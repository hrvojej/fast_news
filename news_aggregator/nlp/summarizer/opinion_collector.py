# opinion_collector.py
"""
Data collection layer for public opinion analysis.

Collects top-voted comments from YouTube (via YouTube Data API v3) and Reddit
(via the public JSON API, no auth required), fetches portal article text for
bias analysis, and orchestrates all sources into a raw opinions dict.
"""

import re
import time
import logging
import urllib.parse
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_REDDIT_HEADERS = {
    "User-Agent": "FastNews/1.0 (opinion research bot; contact@fastnews.example.com)"
}

# Top news portals always included in portal analysis regardless of DuckDuckGo results
_ALWAYS_INCLUDE_DOMAINS = [
    "aljazeera.com",
    "bbc.com",
    "bbc.co.uk",
    "foxnews.com",
    "theguardian.com",
    "nytimes.com",
    "reuters.com",
    "cnn.com",
    "apnews.com",
    "bloomberg.com",
    "wsj.com",
    "washingtonpost.com",
    "thehill.com",
    "politico.com",
    "axios.com",
]


# ---------------------------------------------------------------------------
# YouTube
# ---------------------------------------------------------------------------

def search_youtube_comments(
    query: str,
    api_key: str,
    max_videos: int = 5,
    max_comments_per_video: int = 20,
    region_code: Optional[str] = None,
    min_likes: int = 5,
    min_words: int = 15,
) -> list[dict]:
    """
    Search YouTube for videos matching `query` and collect top comments.

    Returns a list of comment dicts:
        {text, likes, replies_count, platform, video_id, video_title,
         author, published_at, region_code}
    """
    if not api_key:
        logger.debug("No YouTube API key provided — skipping YouTube collection")
        return []

    base = "https://www.googleapis.com/youtube/v3"
    results = []

    # 1. Search for relevant videos
    search_params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "relevance",
        "maxResults": max_videos,
        "relevanceLanguage": "en",
        "key": api_key,
    }
    if region_code:
        search_params["regionCode"] = region_code

    try:
        resp = requests.get(f"{base}/search", params=search_params, timeout=15)
        resp.raise_for_status()
        search_data = resp.json()
    except Exception as exc:
        logger.warning(f"YouTube search failed: {exc}")
        return []

    video_items = search_data.get("items", [])
    if not video_items:
        return []

    for item in video_items:
        video_id = item.get("id", {}).get("videoId")
        if not video_id:
            continue
        video_title = item.get("snippet", {}).get("title", "")

        # 2. Fetch top comments for this video
        comment_params = {
            "part": "snippet",
            "videoId": video_id,
            "order": "relevance",
            "maxResults": max_comments_per_video,
            "key": api_key,
        }
        try:
            c_resp = requests.get(f"{base}/commentThreads", params=comment_params, timeout=15)
            c_resp.raise_for_status()
            comment_data = c_resp.json()
        except Exception as exc:
            logger.warning(f"YouTube commentThreads failed for {video_id}: {exc}")
            continue

        for thread in comment_data.get("items", []):
            top = thread.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            text = (top.get("textDisplay") or "").strip()
            likes = int(top.get("likeCount") or 0)
            replies = int(thread.get("snippet", {}).get("totalReplyCount") or 0)
            author = top.get("authorDisplayName", "")
            published_at = top.get("publishedAt", "")

            word_count = len(text.split())
            if likes < min_likes or word_count < min_words:
                continue

            results.append({
                "platform": "youtube",
                "text": text,
                "likes": likes,
                "replies_count": replies,
                "video_id": video_id,
                "video_title": video_title,
                "author": author,
                "published_at": published_at,
                "region_code": region_code,
                "author_country_inferred": None,
                "authenticity_score": None,
            })

    logger.info(f"YouTube: collected {len(results)} comments for query '{query[:60]}'")
    return results


# ---------------------------------------------------------------------------
# Reddit
# ---------------------------------------------------------------------------

def _reddit_get(url: str) -> Optional[dict]:
    """GET a Reddit JSON endpoint with retry logic."""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=_REDDIT_HEADERS, timeout=15)
            if resp.status_code == 429:
                wait = 2 ** attempt
                logger.debug(f"Reddit rate-limited; sleeping {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.debug(f"Reddit request failed ({attempt + 1}/3): {exc}")
            time.sleep(1)
    return None


def search_reddit_comments(
    query: str,
    subreddits: Optional[list[str]] = None,
    max_posts: int = 5,
    max_comments_per_post: int = 15,
    min_score: int = 10,
    min_words: int = 15,
) -> list[dict]:
    """
    Search Reddit for posts matching `query` and collect top comments.

    If `subreddits` is provided, restrict the search to those subreddits.
    Returns a list of comment dicts:
        {text, score, platform, subreddit, post_title, post_url, author,
         created_utc, author_country_inferred, authenticity_score}
    """
    results = []

    if subreddits:
        # Search within specific subreddits
        for sub in subreddits:
            sub_clean = sub.lstrip("r/")
            url = (
                f"https://www.reddit.com/r/{sub_clean}/search.json"
                f"?q={urllib.parse.quote(query)}&sort=relevance&limit={max_posts}&restrict_sr=1"
            )
            data = _reddit_get(url)
            if not data:
                continue
            posts = data.get("data", {}).get("children", [])
            for post in posts[:max_posts]:
                pd = post.get("data", {})
                post_id = pd.get("id")
                post_title = pd.get("title", "")
                post_url = f"https://www.reddit.com{pd.get('permalink', '')}"
                _collect_post_comments(
                    post_id, sub_clean, post_title, post_url,
                    max_comments_per_post, min_score, min_words, results
                )
                time.sleep(0.5)
    else:
        # Global search
        url = (
            f"https://www.reddit.com/search.json"
            f"?q={urllib.parse.quote(query)}&sort=relevance&type=link&limit={max_posts}"
        )
        data = _reddit_get(url)
        if data:
            posts = data.get("data", {}).get("children", [])
            for post in posts[:max_posts]:
                pd = post.get("data", {})
                post_id = pd.get("id")
                sub_name = pd.get("subreddit", "")
                post_title = pd.get("title", "")
                post_url = f"https://www.reddit.com{pd.get('permalink', '')}"
                _collect_post_comments(
                    post_id, sub_name, post_title, post_url,
                    max_comments_per_post, min_score, min_words, results
                )
                time.sleep(0.5)

    logger.info(f"Reddit: collected {len(results)} comments for query '{query[:60]}'")
    return results


def _collect_post_comments(
    post_id: str,
    subreddit: str,
    post_title: str,
    post_url: str,
    max_comments: int,
    min_score: int,
    min_words: int,
    results: list,
):
    """Fetch top comments for a single Reddit post and append to results."""
    if not post_id:
        return
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json?sort=top&limit={max_comments}"
    data = _reddit_get(url)
    if not data or not isinstance(data, list) or len(data) < 2:
        return

    comments_listing = data[1].get("data", {}).get("children", [])
    for comment in comments_listing:
        if comment.get("kind") != "t1":
            continue
        cd = comment.get("data", {})
        text = (cd.get("body") or "").strip()
        score = int(cd.get("score") or 0)
        author = cd.get("author", "")
        created_utc = cd.get("created_utc", 0)

        if score < min_score or len(text.split()) < min_words:
            continue
        if text in ("[deleted]", "[removed]", ""):
            continue

        results.append({
            "platform": "reddit",
            "text": text,
            "likes": score,
            "score": score,
            "subreddit": subreddit,
            "post_title": post_title,
            "post_url": post_url,
            "author": author,
            "created_utc": created_utc,
            "video_title": None,
            "video_id": None,
            "region_code": None,
            "author_country_inferred": None,
            "authenticity_score": None,
        })


def search_country_subreddits(
    query: str,
    country_entry: dict,
    max_comments: int = 20,
    min_score: int = 10,
    min_words: int = 15,
) -> list[dict]:
    """
    Collect Reddit comments specifically from country-specific subreddits.

    `country_entry` is an entry from `COUNTRY_SOURCES`.
    """
    subreddits = country_entry.get("subreddits", [])
    if not subreddits:
        return []
    comments = search_reddit_comments(
        query,
        subreddits=subreddits,
        max_posts=3,
        max_comments_per_post=max(1, max_comments // max(len(subreddits), 1)),
        min_score=min_score,
        min_words=min_words,
    )
    # Tag each comment with the inferred country
    for c in comments:
        c["author_country_inferred"] = country_entry["name"]
    return comments


# ---------------------------------------------------------------------------
# Portal discovery & text extraction
# ---------------------------------------------------------------------------

def find_portals_covering_topic(query: str, max_results: int = 10) -> list[dict]:
    """
    Discover news portals covering the topic via DuckDuckGo News search.

    Returns a list of {url, title, site} dicts.
    Always includes the known project portals in the result list.
    Falls back gracefully if duckduckgo-search is not installed.
    """
    discovered = []

    # Try DuckDuckGo news search
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            news_results = list(ddgs.news(query, max_results=20))
        for item in news_results:
            url = item.get("url", "")
            domain = _extract_domain(url)
            if domain and not any(d["site"] == domain for d in discovered):
                discovered.append({
                    "url": url,
                    "title": item.get("title", ""),
                    "site": domain,
                    "source": "ddg",
                })
    except ImportError:
        logger.debug("duckduckgo-search not installed; skipping DDG portal discovery")
    except Exception as exc:
        logger.warning(f"DuckDuckGo portal search failed: {exc}")

    # Merge with always-included portals (deduplicate by domain)
    existing_domains = {d["site"] for d in discovered}
    for domain in _ALWAYS_INCLUDE_DOMAINS:
        if domain not in existing_domains:
            discovered.append({
                "url": f"https://www.{domain}/",
                "title": domain,
                "site": domain,
                "source": "curated",
            })
            existing_domains.add(domain)

    # Limit to max_results
    return discovered[:max_results]


def fetch_portal_article_text(url: str) -> Optional[dict]:
    """
    Fetch and extract article text from a URL using requests + BeautifulSoup.

    Returns {url, title, snippet, full_text} or None on failure.
    Limits full_text to 1500 characters to stay within LLM context budgets.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Title
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            og_title = soup.find("meta", property="og:title")
            title = og_title["content"] if og_title and og_title.get("content") else url

        # Snippet / description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        snippet = meta_desc["content"].strip() if meta_desc and meta_desc.get("content") else ""

        # Body text — collect <p> tags
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 40]
        full_text = " ".join(paragraphs)[:1500]

        if not (title or snippet or full_text):
            return None

        return {
            "url": url,
            "site": _extract_domain(url),
            "title": title,
            "snippet": snippet,
            "full_text": full_text,
        }
    except Exception as exc:
        logger.debug(f"Failed to fetch portal article from {url}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def collect_all_opinions(
    query: str,
    entities: dict,
    youtube_api_key: str = "",
    skip_youtube: bool = False,
    max_youtube_videos: int = 5,
    max_youtube_comments: int = 20,
    max_reddit_posts: int = 5,
    max_reddit_comments: int = 15,
    min_likes: int = 5,
    min_score: int = 10,
    min_words: int = 15,
) -> dict:
    """
    Orchestrate all opinion sources for a given article query.

    `entities` is a dict with optional keys: 'persons', 'localities', 'institutions'
    — each a list of name strings.

    Returns:
    {
        "global_comments": [...],       # merged YouTube + global Reddit comments
        "by_locality": {                # country → comments from that country's subreddits
            "Israel": [...],
            ...
        },
        "portal_articles": [            # list of fetched portal article texts
            {url, site, title, snippet, full_text},
            ...
        ],
    }
    """
    from country_sources import resolve_country

    localities = [str(loc) for loc in entities.get("localities", []) if loc]

    global_comments = []

    # --- YouTube (global) ---
    if not skip_youtube and youtube_api_key:
        try:
            yt_comments = search_youtube_comments(
                query,
                api_key=youtube_api_key,
                max_videos=max_youtube_videos,
                max_comments_per_video=max_youtube_comments,
                min_likes=min_likes,
                min_words=min_words,
            )
            global_comments.extend(yt_comments)
        except Exception as exc:
            logger.warning(f"YouTube collection error: {exc}")

    # --- Reddit (global, top subreddits) ---
    try:
        reddit_global = search_reddit_comments(
            query,
            subreddits=["r/worldnews", "r/news", "r/geopolitics", "r/politics"],
            max_posts=max_reddit_posts,
            max_comments_per_post=max_reddit_comments,
            min_score=min_score,
            min_words=min_words,
        )
        global_comments.extend(reddit_global)
    except Exception as exc:
        logger.warning(f"Reddit global collection error: {exc}")

    # --- Country-specific Reddit ---
    by_locality = {}
    for country_name in localities:
        entry = resolve_country(country_name)
        if not entry:
            continue
        try:
            country_comments = search_country_subreddits(
                query,
                entry,
                max_comments=max_reddit_comments,
                min_score=min_score,
                min_words=min_words,
            )
            if country_comments:
                by_locality[entry["name"]] = country_comments
        except Exception as exc:
            logger.warning(f"Country Reddit collection failed for {country_name}: {exc}")

    # --- Portal discovery + text fetch ---
    portal_articles = []
    try:
        portal_refs = find_portals_covering_topic(query, max_results=10)
        for ref in portal_refs[:10]:
            text_data = fetch_portal_article_text(ref["url"])
            if text_data:
                portal_articles.append(text_data)
            time.sleep(0.3)
    except Exception as exc:
        logger.warning(f"Portal collection error: {exc}")

    logger.info(
        f"collect_all_opinions: {len(global_comments)} global comments, "
        f"{sum(len(v) for v in by_locality.values())} country comments, "
        f"{len(portal_articles)} portal articles"
    )

    return {
        "global_comments": global_comments,
        "by_locality": by_locality,
        "portal_articles": portal_articles,
    }


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _extract_domain(url: str) -> str:
    """Return the bare domain from a URL (e.g. 'bbc.com')."""
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        domain = re.sub(r"^www\.", "", domain)
        return domain
    except Exception:
        return ""
