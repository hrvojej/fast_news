from dataclasses import dataclass
from typing import Optional

@dataclass
class Portal:
    portal_id: int
    portal_name: str
    portal_domain: str
    bucket_prefix: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
