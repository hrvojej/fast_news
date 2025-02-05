# path: /home/opc/news_dagster-etl/news_aggregator/db_scripts/models/__init__.py
"""
Database models package
"""

from .models import (
    Base,
    NewsPortal,
    create_portal_category_model,
    create_portal_article_model
)

__all__ = [
    'Base',
    'NewsPortal',
    'create_portal_category_model',
    'create_portal_article_model'
]