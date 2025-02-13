from db_scripts.db_context import DatabaseContext
from sqlalchemy import text

def fetch_portal_id_by_prefix(portal_prefix, env='dev'):
    """
    Fetches the portal_id from the news_portals table for a given portal prefix.
    """
    db_context = DatabaseContext.get_instance(env)
    with db_context.session() as session:
        result = session.execute(
            text("SELECT portal_id FROM public.news_portals WHERE portal_prefix = :prefix"),
            {'prefix': portal_prefix}
        ).fetchone()
        if result:
            return result[0]
        raise Exception(f"Portal with prefix '{portal_prefix}' not found.")

def get_active_categories(portal_prefix, env='dev'):
    """
    Returns active categories for the given portal.
    The query is encapsulated in this module so portal-specific parsers do not contain SQL.
    """
    db_context = DatabaseContext.get_instance(env)
    with db_context.session() as session:
        sql = f"""
            SELECT category_id, atom_link 
            FROM {portal_prefix}.categories 
            WHERE is_active = true AND atom_link IS NOT NULL
        """
        result = session.execute(text(sql)).fetchall()
    return result
