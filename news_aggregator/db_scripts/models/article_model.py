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
