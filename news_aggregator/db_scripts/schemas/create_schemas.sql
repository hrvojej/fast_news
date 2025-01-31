-- Chunk 1: Inicijalne postavke i tablica news_portals
-- 1. Omogućivanje potrebnih ekstenzija
CREATE EXTENSION IF NOT EXISTS ltree;

-- 2. Osnovna tablica s portalima
CREATE TABLE public.news_portals (
    portal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portal_prefix VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    base_url TEXT NOT NULL,
    rss_url TEXT,
    scraping_enabled BOOLEAN DEFAULT true,
    portal_language VARCHAR(50),
    timezone VARCHAR(50) DEFAULT 'UTC',
    active_status BOOLEAN DEFAULT true,
    scraping_frequency_minutes INTEGER DEFAULT 60,
    last_scraped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. Osnovni indeksi
CREATE INDEX idx_portal_status ON public.news_portals(active_status);
CREATE INDEX idx_portal_prefix ON public.news_portals(portal_prefix);

-- 4. Funkcija za ažuriranje stupca updated_at
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5. Primjena trigera na tablicu news_portals
CREATE TRIGGER update_news_portals_updated_at
    BEFORE UPDATE ON public.news_portals
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();


--Chunk 2: Dinamičko stvaranje shema i tablica za svaki portal
-- 6. Dinamičko stvaranje shema i tablica (categories, articles) za svaki portal
DO $$
DECLARE
    portal RECORD;
BEGIN
    FOR portal IN SELECT portal_prefix FROM public.news_portals
    LOOP
        -- Kreira se shema za dotični portal
        EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', portal.portal_prefix);

        -- Kreiranje tablice categories
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.categories (
                category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                slug VARCHAR(255) NOT NULL,
                portal_id UUID NOT NULL DEFAULT gen_random_uuid() REFERENCES public.news_portals(portal_id) ON DELETE CASCADE,
                path LTREE NOT NULL,
                level INT NOT NULL,
                description TEXT,
                link TEXT,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(slug, portal_id)
            )', portal.portal_prefix);

        -- Kreiranje tablice articles
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.articles (
                article_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                guid TEXT UNIQUE,
                description TEXT,
                content TEXT,
                author TEXT[],
                pub_date TIMESTAMPTZ,
                category_id UUID NOT NULL REFERENCES %I.categories(category_id) ON DELETE CASCADE,
                keywords TEXT[],
                reading_time_minutes INTEGER,
                language_code VARCHAR(10),
                image_url TEXT,
                sentiment_score FLOAT CHECK (sentiment_score BETWEEN -1 AND 1),
                share_count INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                comment_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )', portal.portal_prefix, portal.portal_prefix);

        -- Korišteni indeksi za categories i articles
        EXECUTE format('
            CREATE INDEX IF NOT EXISTS idx_category_path ON %I.categories USING GIST (path);
            CREATE INDEX IF NOT EXISTS idx_category_portal ON %I.categories(portal_id);
            CREATE INDEX IF NOT EXISTS idx_articles_pub_date ON %I.articles(pub_date);
            CREATE INDEX IF NOT EXISTS idx_articles_category ON %I.articles(category_id);
            CREATE INDEX IF NOT EXISTS idx_articles_search ON %I.articles
                USING gin(to_tsvector(''english'', title || '' '' || COALESCE(description,'''') || '' '' || COALESCE(content,''''))
            );
        ',
        portal.portal_prefix, portal.portal_prefix, portal.portal_prefix,
        portal.portal_prefix, portal.portal_prefix);

        -- Trigeri za ažuriranje updated_at
        EXECUTE format('
            CREATE TRIGGER update_categories_updated_at
                BEFORE UPDATE ON %I.categories
                FOR EACH ROW
                EXECUTE FUNCTION public.update_updated_at_column();

            CREATE TRIGGER update_articles_updated_at
                BEFORE UPDATE ON %I.articles
                FOR EACH ROW
                EXECUTE FUNCTION public.update_updated_at_column();
        ', portal.portal_prefix, portal.portal_prefix);
    END LOOP;
END $$;

-- Chunk 3: Shema events i tablice events, event_articles, timeline_entries (s IDENTITY)
-- 7. Kreiranje sheme events
CREATE SCHEMA IF NOT EXISTS events;

-- 7.1 Tablica events
CREATE TABLE events.events (
   event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   title TEXT NOT NULL,
   description TEXT,
   start_time TIMESTAMPTZ NOT NULL,
   end_time TIMESTAMPTZ,
   event_type VARCHAR(50) NOT NULL,
   importance_level INT CHECK (importance_level BETWEEN 1 AND 5),
   geographic_scope VARCHAR(50),
   tags TEXT[],
   sentiment_score FLOAT CHECK (sentiment_score BETWEEN -1 AND 1),
   status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived', 'merged')),
   parent_event_id UUID REFERENCES events.events(event_id) ON DELETE CASCADE,
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 7.2 Tablica event_articles
CREATE TABLE events.event_articles (
   event_id UUID REFERENCES events.events(event_id) ON DELETE CASCADE,
article_id UUID NOT NULL DEFAULT gen_random_uuid(),
   portal_id UUID REFERENCES public.news_portals(portal_id) ON DELETE CASCADE,
   similarity_score FLOAT CHECK (similarity_score BETWEEN 0 AND 1),
   context_summary TEXT,
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   PRIMARY KEY (event_id, article_id, portal_id)
);

-- 7.3 Particionirana tablica timeline_entries (IDENTITY + kompozitni PK)
CREATE TABLE events.timeline_entries (
   entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   event_id UUID REFERENCES events.events(event_id) ON DELETE CASCADE,
   article_id UUID NOT NULL,
   portal_id UUID REFERENCES public.news_portals(portal_id) ON DELETE CASCADE,
   entry_timestamp TIMESTAMPTZ NOT NULL,
   entry_type VARCHAR(50) NOT NULL CHECK (entry_type IN ('initial', 'update', 'development', 'conclusion')),
   summary TEXT NOT NULL,
   impact_level INT CHECK (impact_level BETWEEN 1 AND 5),
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   CONSTRAINT unique_article_timeline UNIQUE(event_id, article_id, portal_id),
   PRIMARY KEY (entry_id, entry_timestamp)
) PARTITION BY RANGE (entry_timestamp);

-- 7.4 Indeksi
CREATE INDEX idx_events_temporal ON events.events(start_time, end_time);
CREATE INDEX idx_events_status ON events.events(status);
CREATE INDEX idx_events_type ON events.events(event_type);
CREATE INDEX idx_event_articles_portal ON events.event_articles(portal_id);
CREATE INDEX idx_event_articles_similarity ON events.event_articles(similarity_score DESC);
CREATE INDEX idx_timeline_event ON events.timeline_entries(event_id);

-- 7.5 Triger za update updated_at na events
CREATE TRIGGER update_events_updated_at
   BEFORE UPDATE ON events.events
   FOR EACH ROW
   EXECUTE FUNCTION public.update_updated_at_column();

-- 7.6 Triger za update updated_at na timeline_entries
CREATE TRIGGER update_timeline_updated_at
   BEFORE UPDATE ON events.timeline_entries
   FOR EACH ROW
   EXECUTE FUNCTION public.update_updated_at_column();

-- 7.7 Funkcija i triger za provjeru article_id u event_articles
CREATE OR REPLACE FUNCTION events.validate_article_reference()
RETURNS trigger AS $$
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_event_article_reference
    BEFORE INSERT OR UPDATE ON events.event_articles
    FOR EACH ROW
    EXECUTE FUNCTION events.validate_article_reference();

-- 7.8 Funkcija i triger za dinamičko stvaranje particija timeline_entries
CREATE OR REPLACE FUNCTION events.create_timeline_partitions(
    start_date DATE,
    end_date DATE,
    interval_months INT DEFAULT 3
)
RETURNS void AS $$
DECLARE
    current_date DATE := start_date;
BEGIN
    WHILE current_date < end_date LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS events.timeline_entries_%s 
             PARTITION OF events.timeline_entries 
             FOR VALUES FROM (%L) TO (%L)',
            to_char(current_date, 'YYYY_MM'),
            current_date,
            current_date + interval '3 months'
        );
        current_date := current_date + interval '3 months';
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Chunk 4: Shema comments (particionirana) + validacija referenci na članke
-- 8. Shema comments
CREATE SCHEMA IF NOT EXISTS comments;

-- 8.1 Tablica comments particionirana po posted_at
CREATE TABLE comments.comments (
    comment_id TEXT,
    article_id UUID NOT NULL,
    portal_id UUID REFERENCES public.news_portals(portal_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    content_html TEXT,
    author_id TEXT,
    author_name TEXT,
    parent_comment_id TEXT REFERENCES comments.comments(comment_id) ON DELETE CASCADE,
    root_comment_id TEXT,
    reply_level INT DEFAULT 0,
    thread_path LTREE,
    likes_count INT DEFAULT 0,
    replies_count INT DEFAULT 0,
    sentiment_score FLOAT CHECK (sentiment_score BETWEEN -1 AND 1),
    is_spam BOOLEAN DEFAULT false,
    posted_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (posted_at);

-- 8.2 Tablica article_comment_stats
CREATE TABLE comments.article_comment_stats (
    article_id UUID NOT NULL,
    portal_id UUID REFERENCES public.news_portals(portal_id) ON DELETE CASCADE,
    total_comments_count INT DEFAULT 0,
    top_level_comments_count INT DEFAULT 0,
    reply_comments_count INT DEFAULT 0,
    total_likes_count INT DEFAULT 0,
    overall_sentiment_score FLOAT CHECK (overall_sentiment_score BETWEEN -1 AND 1),
    last_comment_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (article_id, portal_id)
);

-- 8.3 Indeksi
CREATE INDEX idx_comments_article ON comments.comments(article_id, portal_id);
CREATE INDEX idx_comments_hierarchy ON comments.comments(parent_comment_id, root_comment_id);
CREATE INDEX idx_comments_path ON comments.comments USING GIST (thread_path);
CREATE INDEX idx_comments_temporal ON comments.comments(posted_at);
CREATE INDEX idx_comments_author ON comments.comments(author_id);
CREATE INDEX idx_comment_stats_temporal ON comments.article_comment_stats(last_comment_at);

-- 8.4 Trigeri updated_at
CREATE TRIGGER update_comment_updated_at
    BEFORE UPDATE ON comments.comments
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_comment_stats_updated_at
    BEFORE UPDATE ON comments.article_comment_stats
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- 8.5 Validacija portala i parent komentara
CREATE OR REPLACE FUNCTION comments.validate_comment_references()
RETURNS TRIGGER AS $$
BEGIN
    -- Provjera valjanosti portal_id
    IF NOT EXISTS (
        SELECT 1 FROM public.news_portals p 
        WHERE p.portal_id = NEW.portal_id
    ) THEN
        RAISE EXCEPTION 'Invalid portal_id';
    END IF;

    -- Provjera parent_comment_id (ako postoji)
    IF NEW.parent_comment_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM comments.comments 
        WHERE comment_id = NEW.parent_comment_id
    ) THEN
        RAISE EXCEPTION 'Invalid parent_comment_id';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_comment_references
    BEFORE INSERT OR UPDATE ON comments.comments
    FOR EACH ROW
    EXECUTE FUNCTION comments.validate_comment_references();

-- 8.6 **NOVO**: Validacija članka (article_id) unutar comments
-- Removed duplicate function and trigger definition

-- 8.7 Funkcija i triger za kreiranje particija comments
CREATE OR REPLACE FUNCTION comments.create_comment_partitions(
    start_date DATE,
    end_date DATE,
    interval_months INT DEFAULT 3
)
RETURNS void AS $$
DECLARE
    current_date DATE := start_date;
BEGIN
    WHILE current_date < end_date LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS comments.comments_%s 
             PARTITION OF comments.comments 
             FOR VALUES FROM (%L) TO (%L)',
            to_char(current_date, 'YYYY_MM'),
            current_date,
            current_date + interval '3 months'
        );
        current_date := current_date + interval '3 months';
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Chunk 5: Shema topics i povezane tablice, s cikličkim provjerama
-- 9. Shema topics
CREATE SCHEMA IF NOT EXISTS topics;

-- 9.1 Tablica topic_categories
CREATE TABLE topics.topic_categories (
   category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   name VARCHAR(255) NOT NULL,
   slug VARCHAR(255) NOT NULL UNIQUE,
   description TEXT,
   display_order INT,
   status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'archived')),
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 9.2 Tablica topics
CREATE TABLE topics.topics (
   topic_id SERIAL PRIMARY KEY,
   category_id UUID DEFAULT gen_random_uuid() REFERENCES topics.topic_categories(category_id) ON DELETE CASCADE,
   name VARCHAR(255) NOT NULL,
   slug VARCHAR(255) NOT NULL,
   description TEXT,
   parent_topic_id INT REFERENCES topics.topics(topic_id),
   path LTREE NOT NULL,
   level INT NOT NULL,
   keywords TEXT[],
   importance_score FLOAT CHECK (importance_score BETWEEN 0 AND 1),
   article_count INT DEFAULT 0,
   status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'merged', 'archived')),
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   UNIQUE(slug, path),
   CONSTRAINT valid_hierarchy CHECK (
       (parent_topic_id IS NULL AND level = 1) OR 
       (parent_topic_id IS NOT NULL AND level > 1)
   )
);

-- 9.3 Tablica topic_content
CREATE TABLE topics.topic_content (
   topic_id INT REFERENCES topics.topics(topic_id) ON DELETE CASCADE,
   content_type VARCHAR(50) NOT NULL CHECK (
       content_type IN ('article', 'event', 'comment')
   ),
   content_id TEXT NOT NULL, -- TEXT, može sadržavati i comment_id
   portal_id UUID REFERENCES public.news_portals(portal_id) ON DELETE CASCADE,
   relevance_score FLOAT CHECK (relevance_score BETWEEN 0 AND 1),
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   PRIMARY KEY (topic_id, content_type, content_id)
);

-- 9.4 Indeksi
CREATE INDEX idx_topic_categories_status ON topics.topic_categories(status);
CREATE INDEX idx_topics_hierarchy ON topics.topics USING GIST (path);
CREATE INDEX idx_topics_parent ON topics.topics(parent_topic_id);
CREATE INDEX idx_topics_status ON topics.topics(status);
CREATE INDEX idx_topic_content_type ON topics.topic_content(content_type);
CREATE INDEX idx_topic_content_relevance ON topics.topic_content(relevance_score);

-- 9.5 Trigeri za update_updated_at
CREATE TRIGGER update_topic_categories_updated_at
    BEFORE UPDATE ON topics.topic_categories
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_topics_updated_at
    BEFORE UPDATE ON topics.topics
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- 9.6 Funkcija i triger za automatsko ažuriranje path i level
CREATE OR REPLACE FUNCTION topics.update_topic_path()
RETURNS TRIGGER AS $$
BEGIN
    -- Root topic
    IF NEW.parent_topic_id IS NULL THEN
        NEW.path = text2ltree(NEW.topic_id::text);
        NEW.level = 1;
    ELSE
        -- Child topic + sprječavanje ciklusa
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_topic_path
    BEFORE INSERT OR UPDATE OF parent_topic_id
    ON topics.topics
    FOR EACH ROW
    EXECUTE FUNCTION topics.update_topic_path();

-- 9.7 Dodatni triger za sprječavanje ciklusa (robusniji primjer)
CREATE OR REPLACE FUNCTION topics.check_topic_cycle()
RETURNS trigger AS $$
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_topic_cycles
    BEFORE INSERT OR UPDATE ON topics.topics
    FOR EACH ROW
    EXECUTE FUNCTION topics.check_topic_cycle();

-- 9.8 Validacija content_id u topic_content
CREATE OR REPLACE FUNCTION topics.validate_content_reference()
RETURNS trigger AS $$
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_topic_content_reference
    BEFORE INSERT OR UPDATE ON topics.topic_content
    FOR EACH ROW
    EXECUTE FUNCTION topics.validate_content_reference();


-- Chunk 6: Shema analysis (sentiment_lexicon, content_analysis, content_statistics)
-- 10. Shema analysis
CREATE SCHEMA IF NOT EXISTS analysis;

-- 10.1 Tablica sentiment_lexicon
CREATE TABLE analysis.sentiment_lexicon (
    word_id SERIAL PRIMARY KEY,
    word VARCHAR(255) NOT NULL UNIQUE,
    language_code VARCHAR(10) NOT NULL DEFAULT 'en',
    base_score FLOAT NOT NULL CHECK (base_score BETWEEN -1 AND 1),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 10.2 Tablica content_analysis
CREATE TABLE analysis.content_analysis (
    content_id SERIAL PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL CHECK (
        source_type IN ('article', 'comment', 'title', 'summary')
    ),
    source_id TEXT NOT NULL,
    portal_id UUID REFERENCES public.news_portals(portal_id) ON DELETE CASCADE,
    content_length INT,
    language_code VARCHAR(10),
    readability_score FLOAT,
    overall_sentiment_score FLOAT CHECK (overall_sentiment_score BETWEEN -1 AND 1),
    extracted_keywords TEXT[],
    main_topics TEXT[],
    named_entities JSONB,
    analyzed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_type, source_id)
);

-- 10.3 Tablica content_statistics
CREATE TABLE analysis.content_statistics (
    stat_id SERIAL PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL,
    source_id TEXT NOT NULL,
    time_bucket TIMESTAMPTZ NOT NULL,
    word_count INT,
    view_count INT,
    completion_rate FLOAT,
    keyword_density JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_type, source_id, time_bucket)
);

-- 10.4 Indeksi
CREATE INDEX idx_lexicon_word ON analysis.sentiment_lexicon(word);
CREATE INDEX idx_lexicon_language ON analysis.sentiment_lexicon(language_code);
CREATE INDEX idx_lexicon_score ON analysis.sentiment_lexicon(base_score);

CREATE INDEX idx_content_source ON analysis.content_analysis(source_type, source_id);
CREATE INDEX idx_content_sentiment ON analysis.content_analysis(overall_sentiment_score);
CREATE INDEX idx_content_temporal ON analysis.content_analysis(analyzed_at);

CREATE INDEX idx_stats_temporal ON analysis.content_statistics(time_bucket);
CREATE INDEX idx_stats_source ON analysis.content_statistics(source_type, source_id);

-- 10.5 Validacija referenci
CREATE OR REPLACE FUNCTION analysis.validate_content_reference()
RETURNS TRIGGER AS $$
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
                portal_prefix
            ) USING NEW.source_id::INT;
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_content_reference
    BEFORE INSERT OR UPDATE ON analysis.content_analysis
    FOR EACH ROW
    EXECUTE FUNCTION analysis.validate_content_reference();

-- 10.6 Triger update updated_at
CREATE TRIGGER update_content_analysis_updated_at
    BEFORE UPDATE ON analysis.content_analysis
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- 10.7 Materijalizirani pogled i funkcija za osvježavanje
CREATE MATERIALIZED VIEW analysis.content_statistics_mv AS
SELECT 
    source_type,
    date_trunc('day', time_bucket) as day,
    avg(word_count) as avg_word_count,
    avg(view_count) as avg_view_count,
    avg(completion_rate) as avg_completion_rate
FROM analysis.content_statistics
GROUP BY source_type, date_trunc('day', time_bucket)
WITH DATA;

CREATE UNIQUE INDEX ON analysis.content_statistics_mv (source_type, day);

CREATE OR REPLACE FUNCTION public.refresh_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analysis.content_statistics_mv;
END;
$$ LANGUAGE plpgsql;

-- Chunk 7: Shema social (platforms, posts, metrics) + proširena validacija postova
-- 11. Shema social
CREATE SCHEMA IF NOT EXISTS social;

-- 11.1 Tablica platforms
CREATE TABLE social.platforms (
    platform_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT true,
    api_version VARCHAR(50),
    rate_limits JSONB,
    auth_config JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 11.2 Tablica posts
CREATE TABLE social.posts (
    post_id TEXT PRIMARY KEY,
    platform_id INT REFERENCES social.platforms(platform_id) ON DELETE CASCADE,
    article_id UUID NOT NULL,
    portal_id UUID REFERENCES public.news_portals(portal_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    content_type VARCHAR(50) CHECK (
        content_type IN ('text', 'image', 'video', 'link', 'mixed')
    ),
    language_code VARCHAR(10),
    urls TEXT[],
    author_platform_id TEXT,
    author_username TEXT,
    likes_count INT DEFAULT 0,
    shares_count INT DEFAULT 0,
    replies_count INT DEFAULT 0,
    sentiment_score FLOAT CHECK (sentiment_score BETWEEN -1 AND 1),
    posted_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 11.3 Tablica article_social_metrics
CREATE TABLE social.article_social_metrics (
    article_id UUID NOT NULL,
    portal_id UUID REFERENCES public.news_portals(portal_id) ON DELETE CASCADE,
    platform_id INT REFERENCES social.platforms(platform_id) ON DELETE CASCADE,
    total_posts_count INT DEFAULT 0,
    total_likes_count INT DEFAULT 0,
    total_shares_count INT DEFAULT 0,
    total_replies_count INT DEFAULT 0,
    overall_sentiment_score FLOAT CHECK (overall_sentiment_score BETWEEN -1 AND 1),
    first_posted_at TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (article_id, portal_id, platform_id)
);

-- 11.4 Indeksi
CREATE INDEX idx_posts_article ON social.posts(article_id, portal_id);
CREATE INDEX idx_posts_platform ON social.posts(platform_id, posted_at);
CREATE INDEX idx_posts_temporal ON social.posts(posted_at);
CREATE INDEX idx_posts_author ON social.posts(author_platform_id);
CREATE INDEX idx_metrics_temporal ON social.article_social_metrics(last_activity_at);

-- 11.5 Trigeri updated_at
CREATE TRIGGER update_platform_updated_at
    BEFORE UPDATE ON social.platforms
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_post_updated_at
    BEFORE UPDATE ON social.posts
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_metrics_updated_at
    BEFORE UPDATE ON social.article_social_metrics
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- 11.6 Proširena validacija postova (uključuje provjeru članka)
CREATE OR REPLACE FUNCTION social.validate_post_references()
RETURNS TRIGGER AS $$
DECLARE
    portal_prefix TEXT;
    article_exists BOOLEAN;
BEGIN
    -- Validacija platforme
    IF NOT EXISTS (
        SELECT 1 FROM social.platforms 
        WHERE platform_id = NEW.platform_id AND enabled = true
    ) THEN
        RAISE EXCEPTION 'Invalid or disabled platform_id';
    END IF;

    -- Validacija portala
    IF NOT EXISTS (
        SELECT 1 FROM public.news_portals 
        WHERE portal_id = NEW.portal_id
    ) THEN
        RAISE EXCEPTION 'Invalid portal_id';
    END IF;

    -- Validacija članka (article_id) u odgovarajućoj shemi portala
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_post_references
    BEFORE INSERT OR UPDATE ON social.posts
    FOR EACH ROW
    EXECUTE FUNCTION social.validate_post_references();

-- Chunk 8: Shema entities i dodatni trigeri za cikluse i validacije
-- 12. Shema entities
CREATE SCHEMA IF NOT EXISTS entities;

-- 12.1 Tablica entities
CREATE TABLE entities.entities (
    entity_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL CHECK (
        entity_type IN ('person', 'organization', 'location', 'product', 'event', 'concept')
    ),
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'merged', 'archived')),
    description TEXT,
    aliases TEXT[],
    importance_score FLOAT CHECK (importance_score BETWEEN 0 AND 1),
    sentiment_score FLOAT CHECK (sentiment_score BETWEEN -1 AND 1),
    mention_count INT DEFAULT 0,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(normalized_name, entity_type)
);

-- 12.2 Tablica entity_relationships
CREATE TABLE entities.entity_relationships (
    source_entity_id INT REFERENCES entities.entities(entity_id) ON DELETE CASCADE,
    target_entity_id INT REFERENCES entities.entities(entity_id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL CHECK (
        relationship_type IN ('parent_of', 'child_of', 'related_to', 'member_of', 'located_in')
    ),
    strength FLOAT CHECK (strength BETWEEN 0 AND 1),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_entity_id, target_entity_id, relationship_type),
    CHECK (source_entity_id != target_entity_id)
);

-- 12.3 Tablica entity_mentions
CREATE TABLE entities.entity_mentions (
    mention_id SERIAL PRIMARY KEY,
    entity_id INT REFERENCES entities.entities(entity_id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL CHECK (
        content_type IN ('article', 'comment')
    ),
    content_id TEXT NOT NULL,
    portal_id UUID REFERENCES public.news_portals(portal_id) ON DELETE CASCADE,
    context_snippet TEXT,
    sentiment_score FLOAT CHECK (sentiment_score BETWEEN -1 AND 1),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_id, content_type, content_id)
);

-- 12.4 Indeksi
CREATE INDEX idx_entities_type ON entities.entities(entity_type);
CREATE INDEX idx_entities_status ON entities.entities(status);
CREATE INDEX idx_entities_normalized_name ON entities.entities(normalized_name);
CREATE INDEX idx_entities_temporal ON entities.entities(last_seen_at);

CREATE INDEX idx_entity_relationships_type ON entities.entity_relationships(relationship_type);
CREATE INDEX idx_entity_mentions_content ON entities.entity_mentions(content_type, content_id);
CREATE INDEX idx_entity_mentions_temporal ON entities.entity_mentions(created_at);

-- 12.5 Full Text Search indeks za entities
CREATE INDEX idx_entities_text_search ON entities.entities 
    USING GIN (to_tsvector('english', 
        coalesce(name, '') || ' ' || 
        coalesce(description, '') || ' ' || 
        coalesce(array_to_string(aliases, ' '), '')
    ));

-- 12.6 Trigeri za updated_at
CREATE TRIGGER update_entity_updated_at
    BEFORE UPDATE ON entities.entities
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_entity_relationships_updated_at
    BEFORE UPDATE ON entities.entity_relationships
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- 12.7 Validacija referenci (entity_mentions -> članak ili komentar)
CREATE OR REPLACE FUNCTION entities.validate_entity_mention()
RETURNS TRIGGER AS $$
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
                portal_prefix
            ) USING NEW.content_id::INT;
        WHEN 'comment' THEN
            PERFORM 1 FROM comments.comments 
            WHERE comment_id = NEW.content_id;
    END CASE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION '% ID % not found', NEW.content_type, NEW.content_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_entity_mention
    BEFORE INSERT OR UPDATE ON entities.entity_mentions
    FOR EACH ROW
    EXECUTE FUNCTION entities.validate_entity_mention();

-- 12.8 Sprječavanje ciklusa u entity_relationships
CREATE OR REPLACE FUNCTION entities.check_relationship_cycle()
RETURNS trigger AS $$
DECLARE
    path_exists boolean;
BEGIN
    -- Provjera za recipročne odnose
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

    -- Provjera ciklusa za hijerarhijske odnose (npr. parent_of/child_of)
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_relationship_cycles
    BEFORE INSERT OR UPDATE ON entities.entity_relationships
    FOR EACH ROW
    EXECUTE FUNCTION entities.check_relationship_cycle();

-- Chunk 9: Automatski cron rasporedi za particionirane tablice
-- 13. Planirani cron poslovi za stvaranje particija (potrebna ekstenzija pg_cron)

-- Stvaranje particija za timeline_entries (events)
SELECT cron.schedule(
    '0 0 1 * *',
    $$
    SELECT events.create_timeline_partitions(
        CURRENT_DATE,
        CURRENT_DATE + INTERVAL '6 months'
    );
    $$
);

-- Stvaranje particija za comments
SELECT cron.schedule(
    '0 0 1 * *',
    $$
    SELECT comments.create_comment_partitions(
        CURRENT_DATE,
        CURRENT_DATE + INTERVAL '6 months'
    );
    $$
);

/*
NAPOMENA:
- Za gore navedene rasporede potrebno je imati instaliranu ekstenziju pg_cron i odgovarajuće dozvole.
- Ako se koristi okruženje koje ne podržava pg_cron (npr. neke managed usluge bez pg_cron),
  treba izostaviti ili zamijeniti raspoređivanje drugim mehanizmom (npr. eksternim job schedulerom).
*/

