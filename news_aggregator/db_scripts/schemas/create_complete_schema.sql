-- Common schema for both dev and prod environments
CREATE EXTENSION IF NOT EXISTS ltree;

-- Schema for each news portal
DO $$ 
DECLARE
    portal RECORD;
BEGIN
    FOR portal IN SELECT bucket_prefix FROM public.news_portals
    LOOP
        -- 1) Kreiranje sheme
        EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', portal.bucket_prefix);

        -- 2) categories tablica
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.categories (
                category_id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                slug VARCHAR(255) NOT NULL,
                portal_id INT NOT NULL REFERENCES public.news_portals(portal_id) ON DELETE CASCADE,
                path LTREE NOT NULL,
                level INT NOT NULL,
                title TEXT,
                link TEXT,
                atom_link TEXT,
                description TEXT,
                language VARCHAR(50),
                copyright_text TEXT,
                last_build_date TIMESTAMPTZ,
                pub_date TIMESTAMPTZ,
                image_title TEXT,
                image_url TEXT,
                image_link TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(slug, portal_id)
            )', portal.bucket_prefix);

        -- 3) articles tablica
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.articles (
                article_id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                guid TEXT UNIQUE,
                description TEXT,
                author TEXT[],
                pub_date TIMESTAMPTZ,
                category_id INT NOT NULL REFERENCES %I.categories(category_id) ON DELETE CASCADE,
                keywords TEXT[],
                image_url TEXT,
                image_width INT,
                image_credit TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )', portal.bucket_prefix, portal.bucket_prefix);
    END LOOP;
END $$;

-- Events schema
CREATE SCHEMA IF NOT EXISTS events;

-- Events table
CREATE TABLE IF NOT EXISTS events.events (
    event_id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'active',
    confidence_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Event-Article mapping
CREATE TABLE IF NOT EXISTS events.event_articles (
    event_id INT REFERENCES events.events(event_id) ON DELETE CASCADE,
    article_id INT NOT NULL,
    portal_id INT NOT NULL REFERENCES public.news_portals(portal_id),
    similarity_score FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id, article_id, portal_id)
);

-- Topics schema
CREATE SCHEMA IF NOT EXISTS topics;

-- Topics table
CREATE TABLE IF NOT EXISTS topics.topics (
    topic_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_topic_id INT REFERENCES topics.topics(topic_id),
    confidence_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Topic-Event mapping
CREATE TABLE IF NOT EXISTS topics.topic_events (
    topic_id INT REFERENCES topics.topics(topic_id) ON DELETE CASCADE,
    event_id INT REFERENCES events.events(event_id) ON DELETE CASCADE,
    confidence_score FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (topic_id, event_id)
);

-- Entity schema
CREATE SCHEMA IF NOT EXISTS entities;

-- Entities table
CREATE TABLE IF NOT EXISTS entities.entities (
    entity_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Entity-Event mapping
CREATE TABLE IF NOT EXISTS entities.entity_events (
    entity_id INT REFERENCES entities.entities(entity_id) ON DELETE CASCADE,
    event_id INT REFERENCES events.events(event_id) ON DELETE CASCADE,
    role VARCHAR(50),
    confidence_score FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (entity_id, event_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_events_status ON events.events(status);
CREATE INDEX IF NOT EXISTS idx_events_time ON events.events(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_topics_parent ON topics.topics(parent_topic_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities.entities(entity_type);

-- Create or replace function for auto-updating 'updated_at'
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

--------------------------------------------------------------------------------
-- Apply updated_at triggers to all tables. Najprije DROP TRIGGER, zatim CREATE.
--------------------------------------------------------------------------------

DO $$
DECLARE
    portal RECORD;
BEGIN
    FOR portal IN SELECT bucket_prefix FROM public.news_portals
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_categories_updated_at ON %I.categories;
            CREATE TRIGGER update_categories_updated_at
                BEFORE UPDATE ON %I.categories
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        ', portal.bucket_prefix, portal.bucket_prefix);

        EXECUTE format('
            DROP TRIGGER IF EXISTS update_articles_updated_at ON %I.articles;
            CREATE TRIGGER update_articles_updated_at
                BEFORE UPDATE ON %I.articles
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        ', portal.bucket_prefix, portal.bucket_prefix);
    END LOOP;

    -- Events
    EXECUTE '
        DROP TRIGGER IF EXISTS update_events_updated_at ON events.events;
        CREATE TRIGGER update_events_updated_at
            BEFORE UPDATE ON events.events
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    ';

    -- Topics
    EXECUTE '
        DROP TRIGGER IF EXISTS update_topics_updated_at ON topics.topics;
        CREATE TRIGGER update_topics_updated_at
            BEFORE UPDATE ON topics.topics
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    ';

    -- Entities
    EXECUTE '
        DROP TRIGGER IF EXISTS update_entities_updated_at ON entities.entities;
        CREATE TRIGGER update_entities_updated_at
            BEFORE UPDATE ON entities.entities
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    ';
END $$;
