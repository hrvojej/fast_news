# opinion_prompt.py
"""
Prompt builders for the public opinion analysis pipeline.

All prompts request JSON responses and are designed to be called via
`call_llm_api(..., response_format="json")`.
"""

import json
from typing import Optional


def create_comment_filter_prompt(comments: list[dict]) -> str:
    """
    Build a prompt that asks the LLM to score each comment for authenticity.

    Expected JSON response: list of {index, authenticity_score, keep, reason}
    - authenticity_score: 0.0 (bot/AI/generic) to 1.0 (authentic opinion)
    - keep: true/false
    - reason: short string

    Filtering criteria applied by the LLM prompt:
    - Penalise AI pattern phrases: "It's important to", "Moreover", "In conclusion",
      "It is crucial that", "I believe it is important", "As an AI"
    - Reward: first-person expressions, country/city references, personal experience markers
    - Penalise: pure profanity, spam, off-topic rants
    """
    comments_payload = []
    for i, c in enumerate(comments):
        comments_payload.append({
            "index": i,
            "platform": c.get("platform", ""),
            "text": c.get("text", "")[:500],   # cap to save tokens
            "likes": c.get("likes") or c.get("score") or 0,
        })

    comments_json = json.dumps(comments_payload, ensure_ascii=False)

    return f"""You are an expert at detecting authentic human opinions versus AI-generated, 
generic, or spam content in social media comments.

Below is a JSON array of comments collected from YouTube and Reddit. For each comment:
1. Assess the *authenticity* — does it express a genuine, personal human perspective?
2. Penalise: AI-sounding phrases ("It is important to", "Moreover", "In conclusion",
   "I believe it is essential"), copy-paste boilerplate, pure insults without substance,
   off-topic content, short shallow reactions ("lol", "exactly", "so true"), or spam.
3. Reward: specific details, personal experience markers, references to events, countries,
   named people, emotional nuance, or local knowledge.

Return a JSON array (one object per input comment, same order):
[
  {{"index": 0, "authenticity_score": 0.9, "keep": true, "reason": "Specific personal account with local knowledge"}},
  {{"index": 1, "authenticity_score": 0.2, "keep": false, "reason": "Generic AI-sounding phrase structure"}}
]

Comments to evaluate:
{comments_json}

Return ONLY the JSON array. No markdown, no explanation."""


def create_opinion_synthesis_prompt(
    comments: list[dict],
    entity_name: str,
    entity_type: str,
    locality: Optional[str] = None,
) -> str:
    """
    Build a prompt that synthesises a set of comments into a structured opinion summary
    about a named entity (person, locality, or institution).

    Expected JSON response:
    {
        "summary": "2-3 sentence synthesis paragraph",
        "sentiment_label": "positive|negative|mixed|neutral",
        "key_themes": ["theme1", "theme2"],
        "notable_quotes": ["direct quote fragment 1", "direct quote fragment 2"]
    }
    """
    assert entity_type in ("locality", "person", "institution"), f"Invalid entity_type: {entity_type}"

    comments_payload = []
    for c in comments[:40]:   # cap comment list to control token use
        comments_payload.append({
            "platform": c.get("platform", ""),
            "text": c.get("text", "")[:400],
            "likes": c.get("likes") or c.get("score") or 0,
            "country": c.get("author_country_inferred") or c.get("region_code") or "",
        })

    comments_json = json.dumps(comments_payload, ensure_ascii=False)

    locality_clause = f" Focus specifically on opinions FROM people in {locality}." if locality else ""

    entity_label = {
        "locality": "the country/region",
        "person": "the person",
        "institution": "the institution or organisation",
    }[entity_type]

    return f"""You are an expert analyst synthesising public opinion from social media comments.

Analyse the following comments and produce a structured opinion summary about {entity_label} \
named "{entity_name}".{locality_clause}

Synthesise the main sentiment, recurring themes, and most quotable remarks.
Be concise — the summary should be 2-4 sentences. Extract 2-4 key themes.
Select up to 3 notable short quote fragments (max 25 words each).

Return a JSON object:
{{
  "summary": "2-4 sentence synthesis",
  "sentiment_label": "positive|negative|mixed|neutral",
  "key_themes": ["theme1", "theme2"],
  "notable_quotes": ["short quote fragment"]
}}

Comments:
{comments_json}

Return ONLY the JSON object. No markdown, no explanation."""


def create_global_narrative_prompt(comments: list[dict], article_title: str) -> str:
    """
    Build a prompt to create a single global narrative paragraph from all comments.

    Expected JSON response:
    {
        "global_narrative": "paragraph",
        "dominant_sentiment": "positive|negative|mixed|neutral",
        "top_themes": ["theme1", ...]
    }
    """
    comments_payload = [
        {
            "platform": c.get("platform", ""),
            "text": c.get("text", "")[:350],
            "country": c.get("author_country_inferred") or "",
            "likes": c.get("likes") or c.get("score") or 0,
        }
        for c in comments[:50]
    ]
    comments_json = json.dumps(comments_payload, ensure_ascii=False)

    return f"""You are summarising the global public reaction to a news story.

Article headline: "{article_title}"

Below are authentic public comments collected from YouTube and Reddit worldwide.
Write a neutral, analytical paragraph (4-6 sentences) describing the dominant global 
public reaction, key debates, and emotional tone.

Return JSON:
{{
  "global_narrative": "4-6 sentence paragraph",
  "dominant_sentiment": "positive|negative|mixed|neutral",
  "top_themes": ["theme1", "theme2", "theme3"]
}}

Comments:
{comments_json}

Return ONLY the JSON object. No markdown, no explanation."""


def create_portal_bias_prompt(portal_snippets: list[dict], entity_list: list[str]) -> str:
    """
    Build a prompt that analyses framing and entity sentiment across multiple portals.

    `portal_snippets` is a list of {url, site, title, snippet, full_text}
    `entity_list` is a list of entity name strings (persons, localities, institutions)

    Expected JSON response:
    {
        "portal_name.com": {
            "framing": "left-leaning|right-leaning|centrist|nationalistic|...",
            "coverage_angle": "short phrase",
            "entity_sentiment": {
                "EntityName": -0.6
            },
            "evidence": "one-sentence rationale"
        }
    }
    """
    portals_payload = []
    for p in portal_snippets[:12]:
        portals_payload.append({
            "site": p.get("site", _extract_domain(p.get("url", ""))),
            "title": p.get("title", "")[:120],
            "text": (p.get("full_text") or p.get("snippet") or "")[:600],
        })

    portals_json = json.dumps(portals_payload, ensure_ascii=False)
    entities_json = json.dumps(entity_list[:10], ensure_ascii=False)

    return f"""You are a media bias analyst. Analyse how the following news portals cover 
the same news story and identify editorial framing and entity sentiment.

Entities to track: {entities_json}

For each portal, assess:
- "framing": editorial lean (e.g. "pro-government", "left-leaning", "nationalist", "centrist", "pro-western")
- "coverage_angle": a short phrase describing the portal's narrative angle
- "entity_sentiment": for each named entity, a float from -1.0 (hostile) to +1.0 (sympathetic)
  — include only entities that actually appear in the text
- "evidence": one sentence citing the key word choice or omission that supports your assessment

Return a JSON object where each key is the portal site domain:
{{
  "bbc.com": {{
    "framing": "centrist-western",
    "coverage_angle": "Focuses on diplomatic consequences",
    "entity_sentiment": {{"Trump": -0.3, "Iran": 0.1}},
    "evidence": "Uses 'alleged' and emphasises international law"
  }}
}}

Portals to analyse:
{portals_json}

Return ONLY the JSON object. No markdown, no explanation."""


# ---------------------------------------------------------------------------
# Utilities (used internally)
# ---------------------------------------------------------------------------

import re
import urllib.parse


def _extract_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        domain = re.sub(r"^www\.", "", domain)
        return domain
    except Exception:
        return ""
