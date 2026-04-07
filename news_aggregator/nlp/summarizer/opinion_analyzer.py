# opinion_analyzer.py
"""
LLM-based orchestration layer for the public opinion analysis pipeline.

Orchestrates comment collection → authenticity filtering → opinion synthesis
→ portal bias analysis → final JSONB payload assembly.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_BATCH_SIZE = 30  # comments per LLM filter call


# ---------------------------------------------------------------------------
# Step 1: Filter comments by authenticity
# ---------------------------------------------------------------------------

def filter_authentic_comments(
    raw_comments: list[dict],
    article_id: str,
    authenticity_threshold: float = 0.6,
    max_display: int = 50,
) -> list[dict]:
    """
    Use the LLM to score each comment for authenticity and filter out AI/generic ones.

    Processes comments in batches of `_BATCH_SIZE` to respect token limits.
    Returns up to `max_display` authentic comments sorted by combined score.
    """
    from summarizer_api import call_llm_api
    from opinion_prompt import create_comment_filter_prompt

    if not raw_comments:
        return []

    scored: list[dict] = []  # copies of raw_comments with authenticity_score set

    for batch_start in range(0, len(raw_comments), _BATCH_SIZE):
        batch = raw_comments[batch_start: batch_start + _BATCH_SIZE]
        prompt = create_comment_filter_prompt(batch)
        try:
            resp_text = call_llm_api(prompt, article_id, len(prompt), response_format="json")
            results = _parse_json_response(resp_text, expected_type=list)
        except Exception as exc:
            logger.warning(f"LLM comment filter failed for batch at {batch_start}: {exc}")
            # Fall back: treat all comments in batch as "keep" with neutral score
            results = [{"index": i, "authenticity_score": 0.7, "keep": True} for i in range(len(batch))]

        for item in results:
            idx = item.get("index")
            if idx is None or idx >= len(batch):
                continue
            score = float(item.get("authenticity_score") or 0.0)
            keep = bool(item.get("keep", score >= authenticity_threshold))
            if keep and score >= authenticity_threshold:
                comment = dict(batch[idx])
                comment["authenticity_score"] = score
                scored.append(comment)

    # Sort by authenticity_score × engagement (likes/score)
    def _sort_key(c):
        eng = c.get("likes") or c.get("score") or 0
        return float(c.get("authenticity_score") or 0) * (1 + min(eng, 500) / 500)

    scored.sort(key=_sort_key, reverse=True)
    return scored[:max_display]


# ---------------------------------------------------------------------------
# Step 2: Infer comment country
# ---------------------------------------------------------------------------

def infer_comment_country(comment: dict) -> Optional[str]:
    """
    Rule-based country inference for a comment.

    Checks: already-set `author_country_inferred`, then subreddit, then region_code.
    Returns a country name string or None.
    """
    from country_sources import infer_country_from_subreddit, resolve_country

    if comment.get("author_country_inferred"):
        return comment["author_country_inferred"]

    subreddit = comment.get("subreddit")
    if subreddit:
        country = infer_country_from_subreddit(subreddit)
        if country:
            return country

    region_code = comment.get("region_code")
    if region_code:
        entry = resolve_country(region_code)
        if entry:
            return entry["name"]

    return None


def tag_comments_with_countries(comments: list[dict]) -> list[dict]:
    """Return a copy of comments with `author_country_inferred` populated where possible."""
    tagged = []
    for c in comments:
        c2 = dict(c)
        c2["author_country_inferred"] = infer_comment_country(c2)
        tagged.append(c2)
    return tagged


# ---------------------------------------------------------------------------
# Step 3: Synthesize opinions per entity
# ---------------------------------------------------------------------------

def synthesize_opinions(
    filtered_comments: list[dict],
    entities: dict,
    article_id: str,
    by_locality_raw: dict,
) -> tuple[str, dict, dict, dict]:
    """
    Synthesise opinions per entity type (locality, person, institution).

    Returns:
        global_narrative (str),
        by_locality (dict),
        by_person (dict),
        by_institution (dict)
    """
    from summarizer_api import call_llm_api
    from opinion_prompt import create_opinion_synthesis_prompt, create_global_narrative_prompt

    persons = [str(p) for p in entities.get("persons", []) if p]
    localities = [str(loc) for loc in entities.get("localities", []) if loc]
    institutions = [str(inst) for inst in entities.get("institutions", []) if inst]

    article_title = article_id  # used in global narrative prompt; caller may pass actual title

    # --- Global narrative ---
    global_narrative = ""
    if filtered_comments:
        try:
            gn_prompt = create_global_narrative_prompt(filtered_comments, article_title)
            gn_resp = call_llm_api(gn_prompt, article_id, len(gn_prompt), response_format="json")
            gn_data = _parse_json_response(gn_resp, expected_type=dict)
            global_narrative = gn_data.get("global_narrative", "")
        except Exception as exc:
            logger.warning(f"Global narrative synthesis failed: {exc}")

    # --- By locality ---
    by_locality = {}
    for country in localities:
        country_comments = (
            by_locality_raw.get(country, []) +
            [c for c in filtered_comments if c.get("author_country_inferred") == country]
        )
        if not country_comments:
            continue
        try:
            prompt = create_opinion_synthesis_prompt(country_comments, country, "locality", locality=country)
            resp = call_llm_api(prompt, article_id, len(prompt), response_format="json")
            data = _parse_json_response(resp, expected_type=dict)
            data["top_comments"] = country_comments[:5]
            by_locality[country] = data
        except Exception as exc:
            logger.warning(f"Locality synthesis failed for {country}: {exc}")

    # --- By person ---
    by_person = {}
    for person in persons:
        # Pick comments that mention the person
        relevant = [c for c in filtered_comments if person.lower() in (c.get("text") or "").lower()]
        if not relevant:
            relevant = filtered_comments[:15]  # fall back to global pool
        try:
            prompt = create_opinion_synthesis_prompt(relevant, person, "person")
            resp = call_llm_api(prompt, article_id, len(prompt), response_format="json")
            data = _parse_json_response(resp, expected_type=dict)
            # Per-country breakdown for this person
            by_country = {}
            for country in localities:
                c_comments = [
                    c for c in relevant
                    if c.get("author_country_inferred") == country
                ]
                if not c_comments:
                    continue
                try:
                    c_prompt = create_opinion_synthesis_prompt(c_comments, person, "person", locality=country)
                    c_resp = call_llm_api(c_prompt, article_id, len(c_prompt), response_format="json")
                    c_data = _parse_json_response(c_resp, expected_type=dict)
                    by_country[country] = c_data.get("summary", "")
                except Exception as exc:
                    logger.debug(f"Person-country synthesis failed {person}/{country}: {exc}")
            data["by_country"] = by_country
            by_person[person] = data
        except Exception as exc:
            logger.warning(f"Person synthesis failed for {person}: {exc}")

    # --- By institution ---
    by_institution = {}
    for inst in institutions:
        relevant = [c for c in filtered_comments if inst.lower() in (c.get("text") or "").lower()]
        if not relevant:
            relevant = filtered_comments[:10]
        try:
            prompt = create_opinion_synthesis_prompt(relevant, inst, "institution")
            resp = call_llm_api(prompt, article_id, len(prompt), response_format="json")
            data = _parse_json_response(resp, expected_type=dict)
            data["by_country"] = {}
            by_institution[inst] = data
        except Exception as exc:
            logger.warning(f"Institution synthesis failed for {inst}: {exc}")

    return global_narrative, by_locality, by_person, by_institution


# ---------------------------------------------------------------------------
# Step 4: Portal bias analysis
# ---------------------------------------------------------------------------

def analyze_portal_bias(
    portal_articles: list[dict],
    entities: dict,
    article_id: str,
) -> dict:
    """
    Analyse framing and entity sentiment across collected portal articles.

    Returns a dict keyed by portal domain with framing and entity_sentiment data.
    """
    from summarizer_api import call_llm_api
    from opinion_prompt import create_portal_bias_prompt

    if not portal_articles:
        return {}

    entity_list = (
        list(entities.get("persons", []))
        + list(entities.get("localities", []))
        + list(entities.get("institutions", []))
    )
    entity_list = [str(e) for e in entity_list if e][:12]

    if not entity_list:
        return {}

    try:
        prompt = create_portal_bias_prompt(portal_articles, entity_list)
        resp = call_llm_api(prompt, article_id, len(prompt), response_format="json")
        return _parse_json_response(resp, expected_type=dict)
    except Exception as exc:
        logger.warning(f"Portal bias analysis failed: {exc}")
        return {}


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def build_opinion_analysis(
    article_id: str,
    article_title: str,
    entities: dict,
    youtube_api_key: str = "",
    collect_config: Optional[dict] = None,
) -> dict:
    """
    Full orchestration: collect → filter → synthesise → portal bias → payload.

    `entities` example:
    {
        "persons": ["Donald Trump", "Benjamin Netanyahu"],
        "localities": ["United States", "Israel", "Iran"],
        "institutions": ["White House", "UN Security Council"]
    }

    `collect_config` can override any key from env_config opinion_collection section.

    Returns the final `opinion_analysis_json` dict ready for DB storage.
    Partial failures are logged but do not abort the pipeline.
    """
    from opinion_collector import collect_all_opinions

    cfg = collect_config or {}
    skip_youtube = bool(cfg.get("skip_youtube", False)) or not youtube_api_key
    max_yt_videos = int(cfg.get("max_youtube_videos", 5))
    max_yt_comments = int(cfg.get("max_youtube_comments_per_video", 20))
    max_reddit_posts = int(cfg.get("max_reddit_posts", 5))
    max_reddit_comments = int(cfg.get("max_reddit_comments_per_post", 15))
    min_likes = int(cfg.get("min_comment_likes", 5))
    min_score = int(cfg.get("min_comment_score", 10))
    min_words = int(cfg.get("min_comment_words", 15))
    auth_threshold = float(cfg.get("authenticity_threshold", 0.6))
    max_display = int(cfg.get("max_display_comments", 12))

    logger.info(f"[opinion] Starting opinion analysis for article {article_id}: '{article_title[:60]}'")

    # Build query from title (trim to ~100 chars)
    query = article_title[:100]

    # --- Collect raw data ---
    collected = {}
    try:
        collected = collect_all_opinions(
            query=query,
            entities=entities,
            youtube_api_key=youtube_api_key,
            skip_youtube=skip_youtube,
            max_youtube_videos=max_yt_videos,
            max_youtube_comments=max_yt_comments,
            max_reddit_posts=max_reddit_posts,
            max_reddit_comments=max_reddit_comments,
            min_likes=min_likes,
            min_score=min_score,
            min_words=min_words,
        )
    except Exception as exc:
        logger.error(f"[opinion] Collection step failed entirely: {exc}", exc_info=True)
        return _empty_payload()

    global_raw = collected.get("global_comments", [])
    by_locality_raw = collected.get("by_locality", {})
    portal_articles = collected.get("portal_articles", [])

    if not global_raw and not any(by_locality_raw.values()):
        logger.info(f"[opinion] No comments collected for {article_id}; skipping analysis")
        return _empty_payload()

    # --- Tag with countries ---
    all_raw = global_raw + [c for cs in by_locality_raw.values() for c in cs]
    all_raw = tag_comments_with_countries(all_raw)
    global_raw = all_raw[:len(global_raw)]   # restore partition

    # --- Authenticity filtering ---
    filtered = []
    try:
        filtered = filter_authentic_comments(
            all_raw, article_id,
            authenticity_threshold=auth_threshold,
            max_display=max_display * 4,   # keep extra for per-entity pools
        )
    except Exception as exc:
        logger.warning(f"[opinion] Filtering step failed: {exc}")
        # Fall back to all raw comments
        filtered = all_raw[:max_display * 2]

    top_comments = filtered[:max_display]

    # --- Synthesis ---
    global_narrative = ""
    by_locality_synth = {}
    by_person_synth = {}
    by_institution_synth = {}
    try:
        # Pass article title to synthesize_opinions so the global narrative prompt is meaningful
        import types
        _dummy = types.SimpleNamespace()
        global_narrative, by_locality_synth, by_person_synth, by_institution_synth = synthesize_opinions(
            filtered, entities, article_id, by_locality_raw
        )
    except Exception as exc:
        logger.warning(f"[opinion] Synthesis step failed: {exc}", exc_info=True)

    # --- Portal bias ---
    portal_bias = {}
    try:
        portal_bias = analyze_portal_bias(portal_articles, entities, article_id)
    except Exception as exc:
        logger.warning(f"[opinion] Portal bias step failed: {exc}")

    # --- Build final payload ---
    payload = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "top_comments": [_serialize_comment(c) for c in top_comments],
        "global_narrative": global_narrative,
        "by_locality": by_locality_synth,
        "by_person": by_person_synth,
        "by_institution": by_institution_synth,
        "portal_bias": portal_bias,
    }

    logger.info(
        f"[opinion] Analysis complete for {article_id}: "
        f"{len(top_comments)} top comments, "
        f"{len(by_person_synth)} persons, "
        f"{len(by_locality_synth)} localities, "
        f"{len(portal_bias)} portals analysed"
    )

    return payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_response(text: str, expected_type=dict):
    """Parse JSON from LLM response, tolerating markdown code fences."""
    if not text:
        return expected_type()
    # Strip ```json ... ``` fences if present
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        # Remove first and last fence lines
        inner_lines = []
        for i, line in enumerate(lines):
            if i == 0 and line.startswith("```"):
                continue
            if i == len(lines) - 1 and line.strip() == "```":
                continue
            inner_lines.append(line)
        stripped = "\n".join(inner_lines)
    try:
        result = json.loads(stripped)
        if isinstance(result, expected_type):
            return result
        return expected_type()
    except json.JSONDecodeError as exc:
        logger.debug(f"Failed to parse LLM JSON response: {exc}; raw: {text[:200]}")
        return expected_type()


def _serialize_comment(c: dict) -> dict:
    """Return a safe, serializable subset of a comment dict for DB storage."""
    return {
        "platform": c.get("platform", ""),
        "text": (c.get("text") or "")[:600],
        "likes": c.get("likes") or c.get("score") or 0,
        "video_title": c.get("video_title"),
        "subreddit": c.get("subreddit"),
        "author": c.get("author", ""),
        "published_at": c.get("published_at") or str(c.get("created_utc") or ""),
        "author_country_inferred": c.get("author_country_inferred"),
        "authenticity_score": round(float(c.get("authenticity_score") or 0), 3),
    }


def _empty_payload() -> dict:
    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "top_comments": [],
        "global_narrative": "",
        "by_locality": {},
        "by_person": {},
        "by_institution": {},
        "portal_bias": {},
    }
