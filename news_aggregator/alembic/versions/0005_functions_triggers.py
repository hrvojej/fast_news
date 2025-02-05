# path: news_dagster-etl/news_aggregator/alembic/versions/0005_functions_triggers.py
"""Create functions and triggers

Revision ID: 0005
Revises: 0004
Create Date: 2025-02-03 10:25:00

"""
from alembic import op
from sqlalchemy import text

revision = '0005'
down_revision = '0004'

def upgrade():
    op.execute(text("""
        -- 1. Validation trigger for event_articles to check that the referenced article exists.
        CREATE EXTENSION IF NOT EXISTS ltree;

        CREATE OR REPLACE FUNCTION events.validate_article_reference()
        RETURNS trigger AS $func$
        DECLARE
            portal_prefix text;
            article_exists boolean;
        BEGIN
            SELECT portal_prefix INTO portal_prefix
              FROM public.news_portals
             WHERE portal_id = NEW.portal_id;
            IF portal_prefix IS NULL THEN
              RAISE EXCEPTION 'Invalid portal_id %', NEW.portal_id;
            END IF;
            EXECUTE format('
                SELECT EXISTS (
                    SELECT 1
                    FROM %I.articles
                    WHERE article_id = $1
                )', portal_prefix)
              INTO article_exists
              USING NEW.article_id;
            IF NOT article_exists THEN
              RAISE EXCEPTION 'Article % does not exist in portal %', NEW.article_id, portal_prefix;
            END IF;
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;

        CREATE TRIGGER validate_event_article_reference
          BEFORE INSERT OR UPDATE ON events.event_articles
          FOR EACH ROW
          EXECUTE FUNCTION events.validate_article_reference();


        -- 2. Validation trigger for comments: check that portal exists and, if present, parent_comment_id is valid.
        CREATE OR REPLACE FUNCTION comments.validate_comment_references()
        RETURNS trigger AS $func$
        BEGIN
          IF NOT EXISTS (
              SELECT 1 FROM public.news_portals p
              WHERE p.portal_id = NEW.portal_id
          ) THEN
              RAISE EXCEPTION 'Invalid portal_id';
          END IF;
          IF NEW.parent_comment_id IS NOT NULL AND NOT EXISTS (
              SELECT 1 FROM comments.comments
              WHERE comment_id = NEW.parent_comment_id
          ) THEN
              RAISE EXCEPTION 'Invalid parent_comment_id';
          END IF;
          RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;

        CREATE TRIGGER validate_comment_references
          BEFORE INSERT OR UPDATE ON comments.comments
          FOR EACH ROW
          EXECUTE FUNCTION comments.validate_comment_references();


        -- 3. Topics triggers: update topic path/level and prevent cycles.
        CREATE OR REPLACE FUNCTION topics.update_topic_path()
        RETURNS TRIGGER AS $func$
        BEGIN
            IF NEW.parent_topic_id IS NULL THEN
                NEW.path = text2ltree(NEW.topic_id::text);
                NEW.level = 1;
            ELSE
                WITH RECURSIVE topic_hierarchy AS (
                    SELECT topic_id, path, 1 as depth
                    FROM topics.topics
                    WHERE topic_id = NEW.parent_topic_id
                    UNION ALL
                    SELECT t.topic_id, t.path, h.depth + 1
                    FROM topics.topics t
                    JOIN topic_hierarchy h ON t.parent_topic_id = h.topic_id
                    WHERE h.depth < 100
                )
                SELECT path || text2ltree(NEW.topic_id::text), depth + 1
                INTO NEW.path, NEW.level
                FROM topic_hierarchy
                WHERE topic_id = NEW.parent_topic_id;
                IF NEW.topic_id IN (
                    SELECT topic_id FROM topic_hierarchy
                ) THEN
                    RAISE EXCEPTION 'Circular reference detected in topic hierarchy';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;

        CREATE TRIGGER set_topic_path
          BEFORE INSERT OR UPDATE OF parent_topic_id ON topics.topics
          FOR EACH ROW
          EXECUTE FUNCTION topics.update_topic_path();

        CREATE OR REPLACE FUNCTION topics.check_topic_cycle()
        RETURNS trigger AS $func$
        DECLARE
            path_count integer;
        BEGIN
            IF NEW.parent_topic_id IS NULL THEN
                RETURN NEW;
            END IF;
            WITH RECURSIVE topic_tree AS (
                SELECT topic_id, parent_topic_id, ARRAY[topic_id] as path
                FROM topics.topics
                WHERE topic_id = NEW.parent_topic_id
                UNION ALL
                SELECT t.topic_id, t.parent_topic_id, tt.path || t.topic_id
                FROM topics.topics t
                INNER JOIN topic_tree tt ON t.topic_id = tt.parent_topic_id
                WHERE NOT t.topic_id = ANY(tt.path)
            )
            SELECT count(*) INTO path_count
            FROM topic_tree
            WHERE topic_id = NEW.topic_id;
            IF path_count > 0 THEN
                RAISE EXCEPTION 'Cycle detected in topic hierarchy';
            END IF;
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;

        CREATE TRIGGER prevent_topic_cycles
          BEFORE INSERT OR UPDATE ON topics.topics
          FOR EACH ROW
          EXECUTE FUNCTION topics.check_topic_cycle();

        -- 4. Topic content validation trigger.
        CREATE OR REPLACE FUNCTION topics.validate_content_reference()
        RETURNS trigger AS $func$
        DECLARE
            portal_prefix text;
            content_exists boolean;
        BEGIN
            IF NEW.content_type = 'article' THEN
                IF NEW.portal_id IS NULL THEN
                    RAISE EXCEPTION 'portal_id is required for articles';
                END IF;
                SELECT portal_prefix INTO portal_prefix
                  FROM public.news_portals
                 WHERE portal_id = NEW.portal_id;
                IF portal_prefix IS NULL THEN
                    RAISE EXCEPTION 'Invalid portal_id %', NEW.portal_id;
                END IF;
                EXECUTE format('
                    SELECT EXISTS (
                        SELECT 1
                        FROM %I.articles
                        WHERE article_id = $1
                    )', portal_prefix)
                  INTO content_exists
                  USING NEW.content_id::integer;
            ELSIF NEW.content_type = 'event' THEN
                SELECT EXISTS (
                    SELECT 1
                    FROM events.events
                    WHERE event_id = NEW.content_id::integer
                ) INTO content_exists;
            ELSIF NEW.content_type = 'comment' THEN
                SELECT EXISTS (
                    SELECT 1
                    FROM comments.comments
                    WHERE comment_id = NEW.content_id
                ) INTO content_exists;
            ELSE
                RAISE EXCEPTION 'Invalid content_type: %', NEW.content_type;
            END IF;
            IF NOT content_exists THEN
                RAISE EXCEPTION '% with ID % does not exist', NEW.content_type, NEW.content_id;
            END IF;
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;

        CREATE TRIGGER validate_topic_content_reference
          BEFORE INSERT OR UPDATE ON topics.topic_content
          FOR EACH ROW
          EXECUTE FUNCTION topics.validate_content_reference();

        -- 5. Analysis validation function.
        CREATE OR REPLACE FUNCTION analysis.validate_content_reference()
        RETURNS TRIGGER AS $func$
        DECLARE
            portal_prefix TEXT;
        BEGIN
            IF NEW.portal_id IS NOT NULL THEN
                SELECT portal_prefix INTO portal_prefix 
                  FROM public.news_portals 
                 WHERE portal_id = NEW.portal_id;
            END IF;
            CASE NEW.source_type
                WHEN 'article' THEN
                    IF NEW.portal_id IS NULL THEN
                        RAISE EXCEPTION 'portal_id is required for articles';
                    END IF;
                    EXECUTE format('
                        SELECT 1 FROM %I.articles WHERE article_id = $1', 
                        portal_prefix)
                    USING NEW.source_id::INT;
                WHEN 'comment' THEN
                    PERFORM 1 FROM comments.comments 
                    WHERE comment_id = NEW.source_id;
                WHEN 'event' THEN
                    PERFORM 1 FROM events.events 
                    WHERE event_id = NEW.source_id::INT;
            END CASE;
            IF NOT FOUND THEN
                RAISE EXCEPTION '% ID % not found', NEW.source_type, NEW.source_id;
            END IF;
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;

        CREATE TRIGGER validate_content_reference
          BEFORE INSERT OR UPDATE ON analysis.content_analysis
          FOR EACH ROW
          EXECUTE FUNCTION analysis.validate_content_reference();


        ALTER TABLE comments.comments 
        ALTER COLUMN thread_path TYPE ltree USING thread_path::ltree;



        -- 6. Social posts validation trigger.
        CREATE OR REPLACE FUNCTION social.validate_post_references()
        RETURNS TRIGGER AS $func$
        DECLARE
            portal_prefix TEXT;
            article_exists BOOLEAN;
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM social.platforms 
                WHERE platform_id = NEW.platform_id AND enabled = true
            ) THEN
                RAISE EXCEPTION 'Invalid or disabled platform_id';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM public.news_portals 
                WHERE portal_id = NEW.portal_id
            ) THEN
                RAISE EXCEPTION 'Invalid portal_id';
            END IF;
            SELECT portal_prefix INTO portal_prefix
              FROM public.news_portals
             WHERE portal_id = NEW.portal_id;
            IF portal_prefix IS NULL THEN
                RAISE EXCEPTION 'Invalid portal_id %', NEW.portal_id;
            END IF;
            EXECUTE format('
                SELECT EXISTS (
                    SELECT 1
                    FROM %I.articles
                    WHERE article_id = $1
                )', portal_prefix)
              INTO article_exists
              USING NEW.article_id;
            IF NOT article_exists THEN
                RAISE EXCEPTION 'Article % does not exist in portal schema %', NEW.article_id, portal_prefix;
            END IF;
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;

        CREATE TRIGGER validate_post_references
          BEFORE INSERT OR UPDATE ON social.posts
          FOR EACH ROW
          EXECUTE FUNCTION social.validate_post_references();

        -- 7. Entity mention validation trigger.
        CREATE OR REPLACE FUNCTION entities.validate_entity_mention()
        RETURNS TRIGGER AS $func$
        DECLARE
            portal_prefix TEXT;
        BEGIN
            IF NEW.portal_id IS NOT NULL THEN
                SELECT portal_prefix INTO portal_prefix 
                  FROM public.news_portals 
                 WHERE portal_id = NEW.portal_id;
            END IF;
            CASE NEW.content_type
                WHEN 'article' THEN
                    IF NEW.portal_id IS NULL THEN
                        RAISE EXCEPTION 'portal_id is required for articles';
                    END IF;
                    EXECUTE format('
                        SELECT 1 FROM %I.articles WHERE article_id = $1', 
                        portal_prefix)
                    USING NEW.content_id::INT;
                WHEN 'comment' THEN
                    PERFORM 1 FROM comments.comments 
                    WHERE comment_id = NEW.content_id;
            END CASE;
            IF NOT FOUND THEN
                RAISE EXCEPTION '% ID % not found', NEW.content_type, NEW.content_id;
            END IF;
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;

        CREATE TRIGGER validate_entity_mention
          BEFORE INSERT OR UPDATE ON entities.entity_mentions
          FOR EACH ROW
          EXECUTE FUNCTION entities.validate_entity_mention();

        -- Create trigger function for search vector
        CREATE OR REPLACE FUNCTION entities.update_entity_search_vector()
        RETURNS trigger AS $func$
        BEGIN
          NEW.search_vector := to_tsvector('english', 
            COALESCE(NEW.name, '') || ' ' || 
            COALESCE(NEW.description, '') || ' ' || 
            COALESCE(array_to_string(NEW.aliases, ' '), '')
          );
          RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;

        -- Create trigger
        CREATE TRIGGER update_entity_search_vector
          BEFORE INSERT OR UPDATE ON entities.entities
          FOR EACH ROW
          EXECUTE FUNCTION entities.update_entity_search_vector();

        -- Create index on search_vector
        CREATE INDEX IF NOT EXISTS idx_entities_text_search ON entities.entities
        USING gin(search_vector);

        -- 8. Prevent cycles in entity relationships.
        CREATE OR REPLACE FUNCTION entities.check_relationship_cycle()
        RETURNS trigger AS $func$
        DECLARE
            path_exists boolean;
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM entities.entity_relationships
                WHERE source_entity_id = NEW.target_entity_id
                  AND target_entity_id = NEW.source_entity_id
                  AND relationship_type = CASE NEW.relationship_type
                      WHEN 'parent_of' THEN 'child_of'
                      WHEN 'child_of' THEN 'parent_of'
                      ELSE NEW.relationship_type
                  END
            ) THEN
                RAISE EXCEPTION 'Reciprocal relationship already exists';
            END IF;
            IF NEW.relationship_type IN ('parent_of', 'child_of') THEN
                WITH RECURSIVE relationship_chain AS (
                    SELECT source_entity_id, target_entity_id, ARRAY[source_entity_id] as path
                    FROM (SELECT NEW.source_entity_id, NEW.target_entity_id) as new_rel
                    UNION ALL
                    SELECT er.source_entity_id, er.target_entity_id, rc.path || er.source_entity_id
                    FROM entities.entity_relationships er
                    INNER JOIN relationship_chain rc ON er.source_entity_id = rc.target_entity_id
                    WHERE NOT er.source_entity_id = ANY(rc.path)
                      AND er.relationship_type = NEW.relationship_type
                )
                SELECT EXISTS (
                    SELECT 1 FROM relationship_chain 
                    WHERE target_entity_id = NEW.source_entity_id
                ) INTO path_exists;
                IF path_exists THEN
                    RAISE EXCEPTION 'Cycle detected in entity relationships';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;

        CREATE TRIGGER prevent_relationship_cycles
          BEFORE INSERT OR UPDATE ON entities.entity_relationships
          FOR EACH ROW
          EXECUTE FUNCTION entities.check_relationship_cycle();

        -- Note: Partition creation functions will be added in a separate migration
    """))

def downgrade():
    op.execute(text("""
        DROP TRIGGER IF EXISTS validate_event_article_reference ON events.event_articles;
        DROP FUNCTION IF EXISTS events.validate_article_reference();

        DROP TRIGGER IF EXISTS validate_comment_references ON comments.comments;
        DROP FUNCTION IF EXISTS comments.validate_comment_references();

        DROP TRIGGER IF EXISTS set_topic_path ON topics.topics;
        DROP TRIGGER IF EXISTS prevent_topic_cycles ON topics.topics;
        DROP FUNCTION IF EXISTS topics.update_topic_path();
        DROP FUNCTION IF EXISTS topics.check_topic_cycle();

        DROP TRIGGER IF EXISTS validate_topic_content_reference ON topics.topic_content;
        DROP FUNCTION IF EXISTS topics.validate_content_reference();

        DROP TRIGGER IF EXISTS validate_content_reference ON analysis.content_analysis;
        DROP FUNCTION IF EXISTS analysis.validate_content_reference();

        DROP TRIGGER IF EXISTS validate_post_references ON social.posts;
        DROP FUNCTION IF EXISTS social.validate_post_references();

        DROP TRIGGER IF EXISTS validate_entity_mention ON entities.entity_mentions;
        DROP TRIGGER IF EXISTS update_entity_search_vector ON entities.entities;
        DROP FUNCTION IF EXISTS entities.validate_entity_mention();
        DROP FUNCTION IF EXISTS entities.update_entity_search_vector();
        
        DROP INDEX IF EXISTS idx_entities_text_search;

        DROP TRIGGER IF EXISTS prevent_relationship_cycles ON entities.entity_relationships;
        DROP FUNCTION IF EXISTS entities.check_relationship_cycle();

        -- Note: Partition functions will be dropped in a separate migration
    """))