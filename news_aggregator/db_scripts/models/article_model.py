from dataclasses import dataclass
from typing import Optional

@dataclass
class Article:
    article_id: int
    portal_id: int
    category_id: int
    article_url: str
    article_title: str
    article_content: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    url: Optional[str] = None
    guid: Optional[str] = None
    description: Optional[str] = None
    author: Optional[list[str]] = None
    pub_date: Optional[str] = None
    keywords: Optional[list[str]] = None
    image_url: Optional[str] = None
    image_width: Optional[int] = None
    image_credit: Optional[str] = None
