"""
Helpers for structured summary generation and rendering.

This module converts model JSON output into normalized Python structures that can
be stored in the database and rendered by Jinja templates without requiring the
model to emit presentation-layer HTML.
"""

import html
import json
import re

from summarizer_logging import get_logger


logger = get_logger(__name__)


PORTAL_SOURCE_NAMES = {
    "pt_reuters": "Reuters",
    "pt_bbc": "BBC",
    "pt_guardian": "The Guardian",
    "pt_nyt": "The New York Times",
    "pt_fox": "Fox News",
    "pt_aljazeera": "Al Jazeera",
    "pt_abc": "ABC News",
    "py_cnn": "CNN",
}


def extract_json_payload(raw_text):
    """Extract a JSON object from a model response."""
    if not raw_text or not isinstance(raw_text, str):
        raise ValueError("Model response is empty or not a string")

    cleaned = raw_text.strip().replace("\ufeff", "")
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    candidates = [cleaned]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(cleaned[start:end + 1])

    last_error = None
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc

    raise ValueError(f"Unable to parse JSON payload: {last_error}")


def _clean_text(value):
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_string_list(value, max_items=None):
    items = []

    if isinstance(value, list):
        iterable = value
    elif isinstance(value, str):
        iterable = re.split(r"\n+|;|\|", value)
    else:
        iterable = []

    for item in iterable:
        cleaned = _clean_text(item)
        if not cleaned:
            continue
        if cleaned not in items:
            items.append(cleaned)
        if max_items and len(items) >= max_items:
            break

    return items


def _clean_int(value, default=0, minimum=0, maximum=100):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def normalize_plan_data(raw_plan, fallback_title):
    raw_plan = raw_plan or {}
    if not isinstance(raw_plan, dict):
        raw_plan = {}

    section_plan = []
    for item in raw_plan.get("section_plan", []):
        if isinstance(item, dict):
            section_name = _clean_text(item.get("section") or item.get("key") or item.get("name"))
            purpose = _clean_text(item.get("purpose") or item.get("goal") or item.get("description"))
            if section_name:
                section_plan.append({"section": section_name, "purpose": purpose})
        else:
            section_name = _clean_text(item)
            if section_name:
                section_plan.append({"section": section_name, "purpose": ""})

    return {
        "title": _clean_text(raw_plan.get("title")) or fallback_title,
        "angle": _clean_text(raw_plan.get("angle") or raw_plan.get("focus") or raw_plan.get("summary_goal")),
        "summary_goal": _clean_text(raw_plan.get("summary_goal") or raw_plan.get("angle")),
        "audience": _clean_text(raw_plan.get("audience") or raw_plan.get("reader_focus")),
        "keywords": _clean_string_list(raw_plan.get("keywords"), max_items=10),
        "search_queries": _clean_string_list(raw_plan.get("search_queries"), max_items=8),
        "section_plan": section_plan,
    }


def normalize_entity_overview(raw_entities):
    entities = []
    if not isinstance(raw_entities, list):
        return entities

    for item in raw_entities:
        if not isinstance(item, dict):
            continue
        category = _clean_text(item.get("category") or item.get("title") or item.get("name"))
        raw_items = item.get("items") or item.get("entities") or item.get("values") or []
        values = _clean_string_list(raw_items, max_items=10)
        if category and values:
            entities.append({"category": category, "items": values})

    return entities


def normalize_related_resources(raw_resources):
    resources = []
    if not isinstance(raw_resources, list):
        return resources

    for item in raw_resources:
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title") or item.get("label"))
        url = _clean_text(item.get("url") or item.get("href"))
        description = _clean_text(item.get("description") or item.get("snippet"))
        if title and url:
            resources.append({
                "title": title,
                "url": url,
                "description": description,
            })

    return resources[:8]


def normalize_sentiment_analysis(raw_sentiment):
    sentiment_rows = []
    if not isinstance(raw_sentiment, list):
        return sentiment_rows

    for item in raw_sentiment:
        if not isinstance(item, dict):
            continue
        entity = _clean_text(item.get("entity") or item.get("name"))
        if not entity:
            continue
        sentiment_rows.append({
            "entity": entity,
            "positive": _clean_text(item.get("positive") or item.get("positive_count")),
            "negative": _clean_text(item.get("negative") or item.get("negative_count")),
            "summary": _clean_text(item.get("summary")),
            "keywords": _clean_string_list(item.get("keywords"), max_items=8),
        })

    return sentiment_rows


def normalize_popularity(raw_popularity):
    if not isinstance(raw_popularity, dict):
        raw_popularity = {}

    return {
        "number": _clean_int(raw_popularity.get("number") or raw_popularity.get("score"), default=0),
        "description": _clean_text(raw_popularity.get("description")),
    }


def normalize_sections_data(raw_sections):
    raw_sections = raw_sections or {}
    if not isinstance(raw_sections, dict):
        raw_sections = {}

    return {
        "title": _clean_text(raw_sections.get("title")),
        "keywords": _clean_string_list(raw_sections.get("keywords"), max_items=10),
        "entity_overview": normalize_entity_overview(raw_sections.get("entity_overview")),
        "summary_intro": _clean_text(raw_sections.get("summary_intro") or raw_sections.get("lead") or raw_sections.get("intro")),
        "supporting_points": _clean_string_list(raw_sections.get("supporting_points") or raw_sections.get("key_points"), max_items=6),
        "transition_text": _clean_text(raw_sections.get("transition_text") or raw_sections.get("transition") or raw_sections.get("bridge")),
        "secondary_details": _clean_string_list(raw_sections.get("secondary_details") or raw_sections.get("details"), max_items=6),
        "interesting_facts": _clean_string_list(raw_sections.get("interesting_facts") or raw_sections.get("facts"), max_items=6),
        "related_resources": normalize_related_resources(raw_sections.get("related_resources") or raw_sections.get("resources")),
        "sentiment_analysis": normalize_sentiment_analysis(raw_sections.get("sentiment_analysis")),
        "topic_popularity": normalize_popularity(raw_sections.get("topic_popularity") or raw_sections.get("popularity")),
    }


def merge_plan_and_sections(plan_data, sections_data, fallback_title):
    plan = normalize_plan_data(plan_data, fallback_title)
    sections = normalize_sections_data(sections_data)

    title = sections.get("title") or plan.get("title") or fallback_title
    keywords = sections.get("keywords") or plan.get("keywords") or []
    entity_overview = sections.get("entity_overview") or []

    return {
        "title": title,
        "plan": plan,
        "keywords": keywords,
        "entity_overview": entity_overview,
        "sections": {
            "summary_intro": sections.get("summary_intro", ""),
            "supporting_points": sections.get("supporting_points", []),
            "transition_text": sections.get("transition_text", ""),
            "secondary_details": sections.get("secondary_details", []),
        },
        "interesting_facts": sections.get("interesting_facts", []),
        "related_resources": sections.get("related_resources", []),
        "sentiment_analysis": sections.get("sentiment_analysis", []),
        "topic_popularity": sections.get("topic_popularity", {"number": 0, "description": ""}),
    }


def build_summary_paragraphs(structured_summary):
    sections = structured_summary.get("sections", {})
    paragraphs = []

    intro = _clean_text(sections.get("summary_intro"))
    if intro:
        paragraphs.append({"class": "summary-intro", "text": intro})

    supporting_points = sections.get("supporting_points", []) or []
    transition_text = _clean_text(sections.get("transition_text"))
    secondary_details = sections.get("secondary_details", []) or []

    midpoint = max(1, len(supporting_points) // 2) if supporting_points else 0
    for index, point in enumerate(supporting_points):
        cleaned = _clean_text(point)
        if cleaned:
            paragraphs.append({"class": "supporting-point", "text": cleaned})
        if transition_text and index + 1 == midpoint:
            paragraphs.append({"class": "transition-text", "text": transition_text})

    if transition_text and not supporting_points:
        paragraphs.append({"class": "transition-text", "text": transition_text})

    for detail in secondary_details:
        cleaned = _clean_text(detail)
        if cleaned:
            paragraphs.append({"class": "secondary-detail", "text": cleaned})

    return paragraphs


def build_interesting_facts(structured_summary):
    facts = []
    raw_facts = structured_summary.get("interesting_facts", []) or []
    total = len(raw_facts)
    for index, fact in enumerate(raw_facts):
        cleaned = _clean_text(fact)
        if not cleaned:
            continue
        if total == 1 or index == total - 1:
            class_name = "fact-conclusion"
        elif index % 2 == 0:
            class_name = "fact-primary"
        else:
            class_name = "fact-secondary"
        facts.append({"class": [class_name], "class_name": class_name, "text": cleaned})
    return facts


def build_template_fields(structured_summary):
    return {
        "article_title": structured_summary.get("title", ""),
        "keywords": structured_summary.get("keywords", []),
        "entity_overview": structured_summary.get("entity_overview", []),
        "summary_paragraphs": build_summary_paragraphs(structured_summary),
        "interesting_facts": build_interesting_facts(structured_summary),
        "related_resources": structured_summary.get("related_resources", []),
        "sentiment_analysis": structured_summary.get("sentiment_analysis", []),
        "topic_popularity": structured_summary.get("topic_popularity", {"number": 0, "description": ""}),
    }


def render_summary_html_fragment(structured_summary):
    parts = []
    for paragraph in build_summary_paragraphs(structured_summary):
        class_name = paragraph.get("class", "summary-intro")
        text = html.escape(paragraph.get("text", ""))
        if text:
            parts.append(f'<p class="{class_name}">{text}</p>')
    return "\n".join(parts)


def build_source_attribution_html(metadata, schema):
    metadata = metadata or {}
    source_name = PORTAL_SOURCE_NAMES.get(schema, schema.replace("_", " ").title())
    author_value = metadata.get("author") or []

    if isinstance(author_value, str):
        author_text = _clean_text(author_value)
    else:
        author_text = ", ".join(_clean_string_list(author_value, max_items=5))

    spans = [
        '<span class="label">Source:</span>',
        f'<span>{html.escape(source_name)}</span>',
    ]

    if author_text:
        spans.extend([
            '<span class="label">Author:</span>',
            f'<span>{html.escape(author_text)}</span>',
        ])

    return f'<p class="source-attribution">{" ".join(spans)}</p>'


def build_structured_db_fields(structured_summary):
    if not structured_summary:
        return {}

    sections = structured_summary.get("sections", {})
    return {
        "summary_plan_json": structured_summary.get("plan"),
        "summary_keywords_json": structured_summary.get("keywords", []),
        "summary_entities_json": structured_summary.get("entity_overview", []),
        "summary_sections_json": sections,
        "summary_facts_json": structured_summary.get("interesting_facts", []),
        "summary_resources_json": structured_summary.get("related_resources", []),
        "summary_sentiment_json": structured_summary.get("sentiment_analysis", []),
        "summary_popularity_json": structured_summary.get("topic_popularity", {}),
    }