#!/usr/bin/env python3
"""
verify_database.py

This script verifies the existence of schemas, tables, triggers, and indexes 
created by the setup_database.py and create_complete_schema.sql scripts. 
Comments are in English, as requested.
"""

import psycopg2
import sys

def verify_database(environment='dev'):
    """
    Verifies the database objects (schemas, tables, triggers, indexes)
    for the given environment ('dev' or 'prod').
    """
    # Connection config - adjust host/port/password if needed
    config_map = {
        'dev': {
            'dbname': 'news_aggregator_dev',
            'user': 'postgres'
            },
        'prod': {
            'dbname': 'news_aggregator_prod',
            'user': 'postgres'
        }
    }
    config = config_map[environment]

    # Connect to the target database
    conn = psycopg2.connect(**config)
    cur = conn.cursor()

    try:
        print(f"Verificira se '{environment}' baza...\n")

        # 1) Check if ltree extension exists
        # We can query pg_extension catalog
        cur.execute("""
            SELECT extname
            FROM pg_extension
            WHERE extname = 'ltree';
        """)
        row = cur.fetchone()
        if not row:
            raise Exception("Extension 'ltree' not found.")

        # 2) Check public.news_portals table existence
        # "to_regclass('public.news_portals')" returns the OID if table exists, else NULL
        cur.execute("SELECT to_regclass('public.news_portals');")
        if cur.fetchone()[0] is None:
            raise Exception("Table 'public.news_portals' does not exist.")

        # 3) Read all bucket_prefix values to check each portal schema
        cur.execute("SELECT bucket_prefix FROM public.news_portals;")
        portal_prefixes = [r[0] for r in cur.fetchall()]

        # 4) For each prefix, check if schema exists, then check categories and articles tables
        for prefix in portal_prefixes:
            # Check schema existence from pg_namespace
            cur.execute("""
                SELECT nspname
                FROM pg_namespace
                WHERE nspname = %s;
            """, (prefix,))
            row = cur.fetchone()
            if not row:
                raise Exception(f"Schema '{prefix}' not found (portal: {prefix}).")

            # Check categories table
            categories_table = f"{prefix}.categories"
            cur.execute("SELECT to_regclass(%s);", (categories_table,))
            if cur.fetchone()[0] is None:
                raise Exception(f"Table '{categories_table}' does not exist.")

            # Check articles table
            articles_table = f"{prefix}.articles"
            cur.execute("SELECT to_regclass(%s);", (articles_table,))
            if cur.fetchone()[0] is None:
                raise Exception(f"Table '{articles_table}' does not exist.")

            # Check triggers for categories table
            # For trigger presence, we can query pg_trigger. 
            # Note: triggers in pg_trigger have no direct "schema" field, 
            # but are associated with a table via tgrelid (which references the table).
            # We'll check triggers by name and table OID.
            # Example trigger name from create_complete_schema.sql:
            #   update_categories_updated_at
            #   update_articles_updated_at
            # We can parametrize them:
            for trigger_name, table_name in [
                ('update_categories_updated_at', 'categories'),
                ('update_articles_updated_at',  'articles')
            ]:
                cur.execute("""
                    SELECT t.tgname
                    FROM pg_trigger t
                    JOIN pg_class c ON t.tgrelid = c.oid
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    WHERE t.tgname = %s
                    AND n.nspname = %s
                    AND c.relname = %s
                """, (trigger_name, prefix, table_name))
                trow = cur.fetchone()
                if not trow:
                    raise Exception(f"Trigger '{trigger_name}' not found on {prefix}.{table_name}.")

        # 5) Check other schemas (events, topics, entities) and their tables
        #    (events.events, events.event_articles, etc.)
        # We'll define a helper to do table existence checks
        def check_schema_and_table(schema_name, table_name):
            cur.execute("SELECT nspname FROM pg_namespace WHERE nspname = %s;", (schema_name,))
            row = cur.fetchone()
            if not row:
                raise Exception(f"Schema '{schema_name}' not found.")
            fq_name = f"{schema_name}.{table_name}"
            cur.execute("SELECT to_regclass(%s);", (fq_name,))
            if cur.fetchone()[0] is None:
                raise Exception(f"Table '{fq_name}' does not exist.")

        # events schema
        check_schema_and_table('events', 'events')
        check_schema_and_table('events', 'event_articles')

        # topics schema
        check_schema_and_table('topics', 'topics')
        check_schema_and_table('topics', 'topic_events')

        # entities schema
        check_schema_and_table('entities', 'entities')
        check_schema_and_table('entities', 'entity_events')

        # Check triggers on events, topics, entities
        # update_events_updated_at, update_topics_updated_at, update_entities_updated_at
        for trig_name, schema_name, table_name in [
            ('update_events_updated_at',   'events',   'events'),
            ('update_topics_updated_at',   'topics',   'topics'),
            ('update_entities_updated_at', 'entities', 'entities')
        ]:
            cur.execute("""
                SELECT t.tgname
                FROM pg_trigger t
                JOIN pg_class c ON t.tgrelid = c.oid
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE t.tgname = %s
                AND n.nspname = %s
                AND c.relname = %s
            """, (trig_name, schema_name, table_name))
            trow = cur.fetchone()
            if not trow:
                raise Exception(f"Trigger '{trig_name}' not found on {schema_name}.{table_name}.")

        # 6) Check indexes (just a few key ones from create_complete_schema.sql):
        # example: 
        #   CREATE INDEX IF NOT EXISTS idx_events_status ON events.events(status);
        # we'll check presence in pg_class (for the index name)
        indexes = [
            ('events', 'idx_events_status'),
            ('events', 'idx_events_time'),
            ('topics', 'idx_topics_parent'),
            ('entities', 'idx_entities_type')
        ]
        for schema_name, idx_name in indexes:
            # The fully qualified name of an index might look like "events.idx_events_status"
            # We can query pg_class by the name, but also ensure the schema matches pg_namespace
            cur.execute("""
                SELECT c.relname
                FROM pg_class c
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE c.relname = %s
                  AND n.nspname = %s
                  AND c.relkind = 'i';  -- 'i' means index
            """, (idx_name, schema_name))
            if not cur.fetchone():
                raise Exception(f"Index '{schema_name}.{idx_name}' not found.")

        print("Sva predviđena struktura uspješno postoji u bazi:", environment)

    except Exception as e:
        print(f"Verifikacija nije uspjela: {str(e)}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['dev', 'prod']:
        verify_database(sys.argv[1])
    else:
        print("Molim navesti environment: dev ili prod")
        sys.exit(1)
