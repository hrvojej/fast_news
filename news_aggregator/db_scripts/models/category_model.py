from dataclasses import dataclass
from typing import Optional

@dataclass
class Category:
    category_id: int
    portal_id: int
    category_name: str
    category_url: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
