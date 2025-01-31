My python data engineering project for fetching and scrapping RSS and HTML pages of categories and articles of 20 most popular portals is in focus of this question. 

Task at hand:
check DDL of project:

-- Common schema for both dev and prod environments
CREATE EXTENSION IF NOT EXISTS ltree;

-- Schema for each news portal
DO $$ 
DECLARE
    portal RECORD;
BEGIN
    FOR portal IN SELECT portal_prefix FROM public.news_portals
    LOOP
        -- 1) Kreiranje sheme
        EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', portal.portal_prefix);

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
            )', portal.portal_prefix);

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
            )', portal.portal_prefix, portal.portal_prefix);
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
    FOR portal IN SELECT portal_prefix FROM public.news_portals
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_categories_updated_at ON %I.categories;
            CREATE TRIGGER update_categories_updated_at
                BEFORE UPDATE ON %I.categories
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        ', portal.portal_prefix, portal.portal_prefix);

        EXECUTE format('
            DROP TRIGGER IF EXISTS update_articles_updated_at ON %I.articles;
            CREATE TRIGGER update_articles_updated_at
                BEFORE UPDATE ON %I.articles
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        ', portal.portal_prefix, portal.portal_prefix);
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

I need to undrstand if script above is properly supporting all features of the project. 

Some info for understanding:
Events have to have connection to one or more articles. 
Idea is that each portal report on news but those news could be covering same event. 
I will implement latter on functionalitiy that will connect event with all articles that are talking about that event.
Also articles I think are missing comments fields where I would store aggregated list of most important comments in JSON format. JSON format should have structure to define each comment in JSON in proper way - date, likes, replies, comment content...propose what else could be added here. 

Full list of project features is here:

# News Portal Complete Feature List

## 1. Core News Features

### News Aggregation & Analysis
- Automated collection from top 20 global portals
- Topic-based categorization (politics, sports, tech, etc.)
- Cross-source fact verification
- Source credibility assessment
- Article metadata management (authors, dates, sources)
- Fast entity and content search capabilities

### TL;DR (Summary) System
- Twitter-style concise summaries
- Key information highlighting from multiple sources
- Multi-source comparison and fact verification
- Difference highlighting between sources
- Multidimensional analysis of coverage
- Important statistics and data point extraction

## 2. Visualization & Navigation

### Knowledge Graph Visualization
- Interactive relationship visualization
- Entity and event connections mapping
- Timeline progression views
- Hidden connection discovery
- Story development tracking
- Visual connection between related stories

### Search & Navigation
- Quick entity and topic search
- Advanced filtering options (source, category, time)
- Related content discovery
- Simple navigation between connected stories
- Category-based browsing
- Current events overview

## 3. External Content Integration

### Social Media Analysis
- Comment sentiment analysis
- Top comment ranking by engagement
- Public reaction tracking
- Trend analysis across platforms
- Engagement metrics monitoring
- Key discussion points identification

### Video Content Analysis
- Related video discovery and aggregation
- Video comment analysis
- Key moment identification
- Multimedia perspective integration
- Video sentiment tracking
- YouTube comment analysis

## 4. Advanced Analysis Features

### Content Understanding
- Bias detection in reporting
- Multi-source fact verification
- Context provision for stories
- Statistical data highlighting
- Key quote extraction
- Source credibility assessment

### Temporal Analysis
- Story evolution tracking
- Historical context provision
- Update monitoring
- Event progression tracking
- Timeline visualization
- Related event connection

## 5. Infrastructure & Performance

### System Capabilities
- Fast search and retrieval
- Real-time updates
- Cross-platform compatibility
- Mobile-friendly interface
- Advanced filtering system
- Responsive design

### Data Management
- Efficient content organization
- Multiple source handling
- Data verification systems
- Content categorization
- Relationship mapping
- Entity tracking



#### Question  ######
Check if given schema is sufficient for given project features. 

Output you answer in form of a table of contents and than we will cover each heading individually properly in details. 
Idea is to assemble full featured DDL schema that will be able to host all data for all features. 
This has to be done meticoulisily with hight level of care for all possible connections with table and with final features in mind. 
Keep on mind all connections between tables. 
Everything has to be technically correct after I connect all artefacts in final DDL. 
Keep on mind all indexes and other supporting production database elements that have to be implemented in this. 

Comments structur as follows:
########
{
  "comments": [{
    "id": "string",
    "content": "text",
    "author": "string",
    "date_posted": "timestamp",
    "likes": integer,
    "dislikes": integer,
    "replies_count": integer,
    "replies": [{
      "id": "string",
      "content": "text",
      "author": "string",
      "date_posted": "timestamp",
      "likes": integer,
      "parent_comment_id": "string"
    }],
    "sentiment_score": float,
    "is_verified": boolean,
    "engagement_score": float
  }]
}

Remove all features related to:
Source credibility tracking
and 
Fact verification system

Enhance articles not only with sentiment score but also with sentiment words - 5 key words reflecting article sentiment. 
We need to have same thing for comments - only I don't want to have sentiment for each comment and reply but for lets say top 10 comments and replys aggregated in single sentiment analysis per comment/replays and than calculated weights and created final top 10 sentiment words for comments. 
Equally comments and corresponding replys could be tailing to different topic in comments so I need topics to cover comments as well since users could be linking in conversation this event(topic) to something else. 
Think of less complicated schema to represent this. 

#### Todo ###

I'll analyze the schema requirements and propose a comprehensive table of contents for our detailed review. We'll then methodically examine each section to ensure the database structure fully supports all specified features.

# Table of Contents

1. Core Schema Analysis
   - News Portal Schema Assessment
   - Articles Table Enhancements
   - Categories Structure Evaluation

2. Event Management Structure
   - Event Schema Analysis
   - Event-Article Relationships
   - Event Timeline Requirements

3. Topic and Entity Framework
   - Topic Schema with relationships
   - Entity Structure with relationships

4. Comment System Architecture
   - Comment Storage Design
   - Sentiment Analysis Structure
   - Topic-Comment Relationships

5. Social Media Integration
   - Comment Aggregation Structure
   - Engagement Metrics Storage
   - Platform-Specific Requirements

6. Content Analysis Framework
   - Sentiment Analysis Storage
   - Key Words Management
   - Content Statistics Structure

7. Performance Optimization
   - Index Strategy
   - Partitioning Requirements
   - Query Optimization Structures

8. Schema Enhancement Requirements
   - Missing Table Structures
   - Additional Columns
   - Relationship Modifications

Let's begin with the first section to methodically review and enhance each component. Would you like me to start with the detailed analysis of the Core Schema Analysis section?

###
I'll analyze the schema requirements and propose a comprehensive table of contents for our detailed review. We'll then methodically examine each section to ensure the database structure fully supports all specified features.

# Table of Contents

1. Core Schema Analysis
   - News Portal Schema Assessment

CREATE TABLE IF NOT EXISTS public.news_portals (
    portal_id SERIAL PRIMARY KEY,
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

-- Index for frequent lookups
CREATE INDEX IF NOT EXISTS idx_portal_status ON public.news_portals(active_status);
CREATE INDEX IF NOT EXISTS idx_portal_prefix ON public.news_portals(portal_prefix);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_news_portals_updated_at ON public.news_portals;
CREATE TRIGGER update_news_portals_updated_at
    BEFORE UPDATE ON public.news_portals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

   - Articles Table Enhancements

CREATE TABLE IF NOT EXISTS %I.articles (
    article_id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    guid TEXT UNIQUE,
    description TEXT,
    content TEXT,
    author TEXT[],
    pub_date TIMESTAMPTZ,
    category_id INT NOT NULL REFERENCES %I.categories(category_id) ON DELETE CASCADE,
    keywords TEXT[],
    
    -- Enhanced metadata fields
    reading_time_minutes INTEGER,
    word_count INTEGER,
    language_code VARCHAR(10),
    
    -- Image metadata
    image_url TEXT,
    image_width INTEGER,
    image_height INTEGER,
    image_alt_text TEXT,
    image_credit TEXT,
    
    -- Content analysis fields
    sentiment_score FLOAT,
    sentiment_keywords TEXT[5],
    key_quotes TEXT[],
    
    -- Social engagement metrics
    share_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    
    -- Comment analysis
    comments_json JSONB,
    comment_count INTEGER DEFAULT 0,
    comment_sentiment_score FLOAT,
    comment_sentiment_keywords TEXT[10],
    
    -- Audit fields
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Video content
    video_urls TEXT[],
    video_transcripts TEXT[]
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_articles_pub_date ON %I.articles(pub_date);
CREATE INDEX IF NOT EXISTS idx_articles_sentiment ON %I.articles(sentiment_score);
CREATE INDEX IF NOT EXISTS idx_articles_engagement ON %I.articles(share_count, view_count);
CREATE INDEX IF NOT EXISTS idx_articles_search ON %I.articles USING gin(to_tsvector('english', title || ' ' || description || ' ' || content));
CREATE INDEX IF NOT EXISTS idx_articles_keywords ON %I.articles USING gin(keywords);
CREATE INDEX IF NOT EXISTS idx_articles_comments ON %I.articles USING gin(comments_json);

   - Categories Structure Evaluation

CREATE TABLE IF NOT EXISTS %I.categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    portal_id INT NOT NULL REFERENCES public.news_portals(portal_id) ON DELETE CASCADE,
    
    -- Hierarchical structure
    path LTREE NOT NULL,
    level INT NOT NULL,
    
    -- RSS/Feed metadata
    title TEXT,
    link TEXT,
    atom_link TEXT,
    description TEXT,
    language VARCHAR(50),
    copyright_text TEXT,
    last_build_date TIMESTAMPTZ,
    pub_date TIMESTAMPTZ,
    
    -- Image information
    image_title TEXT,
    image_url TEXT,
    image_link TEXT,
    
    -- Content analysis
    keywords TEXT[],
    is_active BOOLEAN DEFAULT true,
    
    -- Audit fields
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(slug, portal_id)
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_category_path ON %I.categories USING GIST (path);
CREATE INDEX IF NOT EXISTS idx_category_portal ON %I.categories(portal_id);
CREATE INDEX IF NOT EXISTS idx_category_active ON %I.categories(is_active);
CREATE INDEX IF NOT EXISTS idx_category_language ON %I.categories(language);

2. Event Management Structure
   - Event Schema Analysis - Events Table

CREATE SCHEMA IF NOT EXISTS events;

CREATE TABLE IF NOT EXISTS events.events (
    event_id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    
    -- Temporal tracking
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    is_ongoing BOOLEAN DEFAULT true,
    last_update_time TIMESTAMPTZ,
    
    -- Event classification
    event_type VARCHAR(50) NOT NULL,
    importance_level INT CHECK (importance_level BETWEEN 1 AND 5),
    geographic_scope VARCHAR(50),
    location_data JSONB,
    
    -- Content analysis
    key_entities TEXT[],
    tags TEXT[],
    sentiment_score FLOAT,
    sentiment_keywords TEXT[5],
    
    -- Engagement metrics
    view_count INTEGER DEFAULT 0,
    follower_count INTEGER DEFAULT 0,
    
    -- Event state
    status VARCHAR(50) DEFAULT 'active' 
        CHECK (status IN ('active', 'completed', 'archived', 'merged')),
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    
    -- For merged events
    parent_event_id INTEGER REFERENCES events.events(event_id),
    
    -- Audit fields
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_events_temporal ON events.events(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_events_status ON events.events(status);
CREATE INDEX IF NOT EXISTS idx_events_type ON events.events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_importance ON events.events(importance_level);
CREATE INDEX IF NOT EXISTS idx_events_location ON events.events USING GIN (location_data);
CREATE INDEX IF NOT EXISTS idx_events_entities ON events.events USING GIN (key_entities);
CREATE INDEX IF NOT EXISTS idx_events_sentiment ON events.events(sentiment_score);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_events_updated_at ON events.events;
CREATE TRIGGER update_events_updated_at
    BEFORE UPDATE ON events.events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

   - Event-Article Relationships
-- First, drop the existing event_articles table to recreate it properly
DROP TABLE IF EXISTS events.event_articles;

-- Recreate event_articles table with proper constraints
CREATE TABLE events.event_articles (
    event_id INT REFERENCES events.events(event_id) ON DELETE CASCADE,
    article_id INT NOT NULL,
    portal_id INT NOT NULL REFERENCES public.news_portals(portal_id),
    
    -- Relationship strength metrics
    similarity_score FLOAT NOT NULL CHECK (similarity_score BETWEEN 0 AND 1),
    relevance_weight FLOAT CHECK (relevance_weight BETWEEN 0 AND 1),
    
    -- Content relationship analysis
    shared_entities TEXT[] NOT NULL DEFAULT '{}',
    shared_keywords TEXT[] NOT NULL DEFAULT '{}',
    context_summary TEXT,
    
    -- Temporal tracking
    article_event_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sequence_order INT,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (event_id, article_id, portal_id)
);

-- Create function to validate article references
CREATE OR REPLACE FUNCTION events.validate_article_reference()
RETURNS TRIGGER AS $$
DECLARE
    portal_prefix TEXT;
BEGIN
    -- Get portal prefix
    SELECT portal_prefix INTO portal_prefix 
    FROM public.news_portals 
    WHERE portal_id = NEW.portal_id;
    
    -- Check if article exists in the portal's schema
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = portal_prefix
        AND table_name = 'articles'
    ) THEN
        RAISE EXCEPTION 'Portal schema %.articles does not exist', portal_prefix;
    END IF;
    
    -- Dynamic SQL to check article existence
    EXECUTE format('
        SELECT 1 
        FROM %I.articles 
        WHERE article_id = $1', 
        portal_prefix
    ) USING NEW.article_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article ID % does not exist in portal %', NEW.article_id, portal_prefix;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for article validation
CREATE TRIGGER validate_event_article
    BEFORE INSERT OR UPDATE ON events.event_articles
    FOR EACH ROW
    EXECUTE FUNCTION events.validate_article_reference();

-- Create indexes for performance
CREATE INDEX idx_event_articles_portal ON events.event_articles(portal_id);
CREATE INDEX idx_event_articles_similarity ON events.event_articles(similarity_score DESC);
CREATE INDEX idx_event_articles_temporal ON events.event_articles(article_event_timestamp);
CREATE INDEX idx_event_articles_entities ON events.event_articles USING GIN (shared_entities);
CREATE INDEX idx_event_articles_keywords ON events.event_articles USING GIN (shared_keywords);

-- Add foreign key validation trigger
COMMENT ON TABLE events.event_articles IS 'Maps articles from various portal schemas to events with dynamic foreign key validation';









   - Event Timeline Requirements
CREATE TABLE IF NOT EXISTS events.timeline_entries (
    entry_id SERIAL PRIMARY KEY,
    event_id INT REFERENCES events.events(event_id) ON DELETE CASCADE,
    article_id INT NOT NULL,
    portal_id INT NOT NULL REFERENCES public.news_portals(portal_id),
    
    -- Timeline metadata
    entry_timestamp TIMESTAMPTZ NOT NULL,
    entry_type VARCHAR(50) NOT NULL 
        CHECK (entry_type IN ('initial', 'update', 'development', 'conclusion')),
    
    -- Content analysis
    significance_score FLOAT CHECK (significance_score BETWEEN 0 AND 1),
    summary TEXT NOT NULL,
    key_changes TEXT[],
    key_entities TEXT[],
    
    -- Impact tracking
    impact_level INT CHECK (impact_level BETWEEN 1 AND 5),
    sentiment_shift FLOAT,
    
    -- Verification
    source_count INT DEFAULT 1,
    verification_status VARCHAR(50) DEFAULT 'unverified'
        CHECK (verification_status IN ('unverified', 'partially_verified', 'verified')),
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_article_timeline 
        UNIQUE(event_id, article_id, portal_id)
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_timeline_event 
    ON events.timeline_entries(event_id);
CREATE INDEX IF NOT EXISTS idx_timeline_timestamp 
    ON events.timeline_entries(entry_timestamp);
CREATE INDEX IF NOT EXISTS idx_timeline_significance 
    ON events.timeline_entries(significance_score);
CREATE INDEX IF NOT EXISTS idx_timeline_type 
    ON events.timeline_entries(entry_type);

-- Trigger for updated_at
CREATE TRIGGER update_timeline_updated_at
    BEFORE UPDATE ON events.timeline_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

3. Topic and Entity Framework
   - Topic Schema with relationships - 

-- Topic Categories (top-level organization)
CREATE TABLE topics.topic_categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    display_order INT,
    icon_class VARCHAR(50),
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'archived')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Main Topics Table
CREATE TABLE topics.topics (
    topic_id SERIAL PRIMARY KEY,
    category_id INT REFERENCES topics.topic_categories(category_id),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Hierarchy Management
    parent_topic_id INT REFERENCES topics.topics(topic_id),
    path LTREE NOT NULL,
    level INT NOT NULL,
    root_topic_id INT REFERENCES topics.topics(topic_id),
    
    -- Content Classification
    keywords TEXT[],
    key_entities TEXT[],
    related_concepts TEXT[],
    
    -- Analysis Data
    sentiment_score FLOAT,
    sentiment_keywords TEXT[5],
    importance_score FLOAT CHECK (importance_score BETWEEN 0 AND 1),
    trending_score FLOAT,
    
    -- Engagement Metrics
    event_count INT DEFAULT 0,
    article_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    view_count INT DEFAULT 0,
    follower_count INT DEFAULT 0,
    
    -- Status Management
    status VARCHAR(50) DEFAULT 'active' 
        CHECK (status IN ('active', 'merged', 'split', 'archived')),
    visibility VARCHAR(50) DEFAULT 'public' 
        CHECK (visibility IN ('public', 'private', 'archived')),
    
    -- Temporal Data
    first_appearance_date TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,
    peak_activity_date TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(slug, path),
    CONSTRAINT valid_hierarchy CHECK (
        (parent_topic_id IS NULL AND level = 1) OR 
        (parent_topic_id IS NOT NULL AND level > 1)
    )
);

-- Topic Relationships
CREATE TABLE topics.topic_relationships (
    source_topic_id INT REFERENCES topics.topics(topic_id),
    target_topic_id INT REFERENCES topics.topics(topic_id),
    relationship_type VARCHAR(50) NOT NULL CHECK (
        relationship_type IN (
            'parent_child',    -- Hierarchical relationship
            'related',         -- Topics are related
            'merged_into',     -- Topic was merged into another
            'split_from',      -- Topic was split from another
            'prerequisite',    -- Topic is prerequisite for understanding
            'successor',       -- Topic follows another chronologically
            'contains',        -- Topic fully contains another
            'overlaps'         -- Topics have overlapping content
        )
    ),
    strength FLOAT CHECK (strength BETWEEN 0 AND 1),
    bidirectional BOOLEAN DEFAULT false,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (source_topic_id, target_topic_id, relationship_type),
    CHECK (source_topic_id != target_topic_id)
);

-- Topic Timeline
CREATE TABLE topics.topic_timeline (
    timeline_id SERIAL PRIMARY KEY,
    topic_id INT REFERENCES topics.topics(topic_id),
    event_type VARCHAR(50) NOT NULL CHECK (
        event_type IN (
            'created',
            'updated',
            'merged',
            'split',
            'archived',
            'trending',
            'significant_update'
        )
    ),
    event_date TIMESTAMPTZ NOT NULL,
    event_description TEXT,
    importance_score FLOAT CHECK (importance_score BETWEEN 0 AND 1),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Topic Statistics
CREATE TABLE topics.topic_statistics (
    topic_id INT REFERENCES topics.topics(topic_id),
    date_bucket DATE NOT NULL,
    article_count INT DEFAULT 0,
    event_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    view_count INT DEFAULT 0,
    sentiment_score FLOAT,
    trending_score FLOAT,
    peak_hour_activity INT[], -- Array of 24 integers for hourly activity
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (topic_id, date_bucket)
);



-- Topic Content Mapping
CREATE TABLE topics.topic_content (
    topic_id INT REFERENCES topics.topics(topic_id),
    content_type VARCHAR(50) NOT NULL CHECK (
        content_type IN ('article', 'event', 'comment', 'social_post')
    ),
    content_id INT NOT NULL,
    portal_id INT REFERENCES public.news_portals(portal_id),
    relevance_score FLOAT CHECK (relevance_score BETWEEN 0 AND 1),
    sentiment_score FLOAT,
    assignment_type VARCHAR(50) DEFAULT 'automatic' CHECK (
        assignment_type IN ('automatic', 'manual', 'suggested')
    ),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (topic_id, content_type, content_id)
);

-- Topic Categories
CREATE INDEX idx_topic_categories_status ON topics.topic_categories(status);
CREATE INDEX idx_topic_categories_display ON topics.topic_categories(display_order);

-- Topics
CREATE INDEX idx_topics_hierarchy ON topics.topics USING GIST (path);
CREATE INDEX idx_topics_parent ON topics.topics(parent_topic_id);
CREATE INDEX idx_topics_root ON topics.topics(root_topic_id);
CREATE INDEX idx_topics_status ON topics.topics(status, visibility);
CREATE INDEX idx_topics_trending ON topics.topics(trending_score DESC);
CREATE INDEX idx_topics_engagement ON topics.topics(view_count, comment_count);
CREATE INDEX idx_topics_temporal ON topics.topics(last_activity_at);
CREATE INDEX idx_topics_search ON topics.topics USING GIN (
    to_tsvector('english', 
        coalesce(name, '') || ' ' || 
        coalesce(description, '') || ' ' || 
        coalesce(array_to_string(keywords, ' '), '')
    )
);

-- Topic Relationships
CREATE INDEX idx_topic_relationships_type 
    ON topics.topic_relationships(relationship_type);
CREATE INDEX idx_topic_relationships_temporal 
    ON topics.topic_relationships(start_date, end_date);

-- Topic Timeline
CREATE INDEX idx_topic_timeline_date ON topics.topic_timeline(event_date);
CREATE INDEX idx_topic_timeline_type ON topics.topic_timeline(event_type);

-- Topic Statistics
CREATE INDEX idx_topic_stats_date ON topics.topic_statistics(date_bucket);
CREATE INDEX idx_topic_stats_trending ON topics.topic_statistics(trending_score);

-- Topic Content
CREATE INDEX idx_topic_content_type ON topics.topic_content(content_type);
CREATE INDEX idx_topic_content_relevance ON topics.topic_content(relevance_score);


-- Update topic path automatically
CREATE OR REPLACE FUNCTION topics.update_topic_path()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.parent_topic_id IS NULL THEN
        NEW.path = text2ltree(NEW.topic_id::text);
        NEW.level = 1;
        NEW.root_topic_id = NEW.topic_id;
    ELSE
        WITH RECURSIVE topic_path AS (
            SELECT topic_id, path, 1 as depth
            FROM topics.topics
            WHERE topic_id = NEW.parent_topic_id
            UNION ALL
            SELECT t.topic_id, t.path, p.depth + 1
            FROM topics.topics t
            JOIN topic_path p ON t.parent_topic_id = p.topic_id
        )
        SELECT 
            path || text2ltree(NEW.topic_id::text),
            depth + 1,
            topic_id
        INTO 
            NEW.path,
            NEW.level,
            NEW.root_topic_id
        FROM topic_path
        WHERE topic_id = NEW.parent_topic_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION topics.validate_topic_content_reference()
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
            EXECUTE format('SELECT 1 FROM %I.articles WHERE article_id = $1', portal_prefix) 
            USING NEW.content_id;
        WHEN 'event' THEN
            PERFORM 1 FROM events.events WHERE event_id = NEW.content_id;
        WHEN 'comment' THEN
            PERFORM 1 FROM comments.comments WHERE comment_id = NEW.content_id::text;
        WHEN 'social_post' THEN
            PERFORM 1 FROM social.posts WHERE post_id = NEW.content_id::text;
    END CASE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION '% ID % not found', NEW.content_type, NEW.content_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_topic_content_reference
    BEFORE INSERT OR UPDATE ON topics.topic_content
    FOR EACH ROW
    EXECUTE FUNCTION topics.validate_topic_content_reference();

-- Trigger for path updates
CREATE TRIGGER set_topic_path
    BEFORE INSERT OR UPDATE OF parent_topic_id
    ON topics.topics
    FOR EACH ROW
    EXECUTE FUNCTION topics.update_topic_path();




# Entity Structure with relationships

-- Base Entity Schema
CREATE SCHEMA IF NOT EXISTS entities;

-- Core Entities Table
CREATE TABLE entities.entities (
    entity_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL CHECK (
        entity_type IN (
            'person',
            'organization',
            'location',
            'product',
            'event',
            'concept',
            'technology',
            'regulation',
            'document'
        )
    ),
    
    -- Entity Classification
    status VARCHAR(50) DEFAULT 'active' 
        CHECK (status IN ('active', 'inactive', 'merged', 'archived')),
    primary_category VARCHAR(100),
    subcategories TEXT[],
    
    -- Core Metadata
    description TEXT,
    short_description TEXT,
    aliases TEXT[],
    languages TEXT[],
    
    -- Rich Attributes
    properties JSONB,         -- Type-specific properties
    external_ids JSONB,       -- IDs in external systems
    links JSONB,             -- Related URLs and references
    
    -- Media
    image_url TEXT,
    media_urls JSONB,        -- Other media (videos, documents)
    
    -- Analysis Metrics
    importance_score FLOAT CHECK (importance_score BETWEEN 0 AND 1),
    trending_score FLOAT,
    sentiment_score FLOAT,
    sentiment_keywords TEXT[5],
    
    -- Engagement Metrics
    mention_count INT DEFAULT 0,
    citation_count INT DEFAULT 0,
    view_count INT DEFAULT 0,
    
    -- Temporal Tracking
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    peak_mention_date TIMESTAMPTZ,
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(normalized_name, entity_type)
);

-- Entity Relationships
CREATE TABLE entities.entity_relationships (
    source_entity_id INT REFERENCES entities.entities(entity_id),
    target_entity_id INT REFERENCES entities.entities(entity_id),
    relationship_type VARCHAR(50) NOT NULL CHECK (
        relationship_type IN (
            'parent_of',
            'child_of',
            'affiliate_of',
            'member_of',
            'competitor_of',
            'collaborator_with',
            'located_in',
            'manages',
            'created_by',
            'owns',
            'related_to'
        )
    ),
    
    -- Relationship Properties
    strength FLOAT CHECK (strength BETWEEN 0 AND 1),
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    bidirectional BOOLEAN DEFAULT false,
    
    -- Temporal Aspects
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    
    -- Rich Attributes
    properties JSONB,
    citation_urls TEXT[],
    
    -- Metrics
    mention_count INT DEFAULT 0,
    last_mentioned_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (source_entity_id, target_entity_id, relationship_type),
    CHECK (source_entity_id != target_entity_id)
);

-- Entity Mentions (Occurrences in Content)
CREATE TABLE entities.entity_mentions (
    mention_id SERIAL PRIMARY KEY,
    entity_id INT REFERENCES entities.entities(entity_id),
    content_type VARCHAR(50) NOT NULL CHECK (
        content_type IN ('article', 'comment', 'social_post', 'video', 'document')
    ),
    content_id INT NOT NULL,
    portal_id INT REFERENCES public.news_portals(portal_id),
    
    -- Mention Classification
    mention_type VARCHAR(50) NOT NULL CHECK (
        mention_type IN (
            'primary_subject',
            'secondary_subject',
            'referenced',
            'quoted',
            'background'
        )
    ),
    
    -- Context
    context_snippet TEXT,
    context_position JSONB,  -- Position in content {start: X, end: Y}
    
    -- Analysis
    sentiment_score FLOAT,
    importance_score FLOAT CHECK (importance_score BETWEEN 0 AND 1),
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    
    -- Associated Entities
    co_mentioned_entities INT[],  -- Array of entity_ids mentioned together
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(entity_id, content_type, content_id, context_position)
);

-- Entity Timeline (Historical Tracking)
CREATE TABLE entities.entity_timeline (
    timeline_id SERIAL PRIMARY KEY,
    entity_id INT REFERENCES entities.entities(entity_id),
    event_type VARCHAR(50) NOT NULL CHECK (
        event_type IN (
            'created',
            'updated',
            'merged',
            'split',
            'relationship_added',
            'relationship_removed',
            'trending',
            'significant_mention'
        )
    ),
    
    event_date TIMESTAMPTZ NOT NULL,
    event_description TEXT,
    importance_score FLOAT CHECK (importance_score BETWEEN 0 AND 1),
    metadata JSONB,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Entity Statistics (Time-based Metrics)
CREATE TABLE entities.entity_statistics (
    entity_id INT REFERENCES entities.entities(entity_id),
    date_bucket DATE NOT NULL,
    
    -- Mention Metrics
    mention_count INT DEFAULT 0,
    unique_sources_count INT DEFAULT 0,
    
    -- Engagement
    view_count INT DEFAULT 0,
    interaction_count INT DEFAULT 0,
    
    -- Analysis
    sentiment_score FLOAT,
    importance_score FLOAT,
    trending_score FLOAT,
    
    -- Related Entities
    top_co_occurrences JSONB,  -- {entity_id: count}
    
    -- Temporal
    peak_hour_mentions INT[],  -- Array of 24 integers for hourly activity
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (entity_id, date_bucket)
);

-- Entity Merging History
CREATE TABLE entities.entity_merges (
    merge_id SERIAL PRIMARY KEY,
    source_entity_id INT REFERENCES entities.entities(entity_id),
    target_entity_id INT REFERENCES entities.entities(entity_id),
    merge_reason TEXT,
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    metadata JSONB,
    merged_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX idx_entities_type ON entities.entities(entity_type);
CREATE INDEX idx_entities_status ON entities.entities(status);
CREATE INDEX idx_entities_normalized_name ON entities.entities(normalized_name);
CREATE INDEX idx_entities_importance ON entities.entities(importance_score DESC);
CREATE INDEX idx_entities_trending ON entities.entities(trending_score DESC);
CREATE INDEX idx_entities_temporal ON entities.entities(last_seen_at);
CREATE INDEX idx_entities_properties ON entities.entities USING GIN (properties);
CREATE INDEX idx_entities_external_ids ON entities.entities USING GIN (external_ids);

CREATE INDEX idx_entity_relationships_temporal 
    ON entities.entity_relationships(valid_from, valid_until);
CREATE INDEX idx_entity_relationships_strength 
    ON entities.entity_relationships(strength DESC);

CREATE INDEX idx_entity_mentions_content 
    ON entities.entity_mentions(content_type, content_id);
CREATE INDEX idx_entity_mentions_temporal 
    ON entities.entity_mentions(created_at);
CREATE INDEX idx_entity_mentions_importance 
    ON entities.entity_mentions(importance_score DESC);

CREATE INDEX idx_entity_timeline_date 
    ON entities.entity_timeline(event_date);
CREATE INDEX idx_entity_timeline_type 
    ON entities.entity_timeline(event_type);

CREATE INDEX idx_entity_statistics_date 
    ON entities.entity_statistics(date_bucket);
CREATE INDEX idx_entity_statistics_trending 
    ON entities.entity_statistics(trending_score DESC);

-- Full Text Search
CREATE INDEX idx_entities_text_search ON entities.entities 
    USING GIN (to_tsvector('english', 
        coalesce(name, '') || ' ' || 
        coalesce(description, '') || ' ' || 
        coalesce(array_to_string(aliases, ' '), '') || ' ' ||
        coalesce(short_description, '')
    ));

-- Automated Triggers
CREATE TRIGGER update_entity_updated_at
    BEFORE UPDATE ON entities.entities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_entity_relationships_updated_at
    BEFORE UPDATE ON entities.entity_relationships
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();



-
4. Comment System Architecture
   - Comment Storage Design
   - Sentiment Analysis Structure
   - Topic-Comment Relationships

-- Comment System Schema
CREATE SCHEMA IF NOT EXISTS comments;

-- Core Comments Table
CREATE TABLE comments.comments (
    comment_id TEXT PRIMARY KEY,           -- Using UUID or platform-specific ID
    article_id INT NOT NULL,
    portal_id INT REFERENCES public.news_portals(portal_id),
    
    -- Comment Content
    content TEXT NOT NULL,
    content_html TEXT,                     -- Formatted version if available
    language_code VARCHAR(10),
    
    -- Author Information
    author_id TEXT,                        -- Platform-specific user ID
    author_name TEXT,
    author_verified BOOLEAN DEFAULT false,
    author_metadata JSONB,                 -- Platform-specific author data
    
    -- Hierarchy
    parent_comment_id TEXT REFERENCES comments.comments(comment_id),
    root_comment_id TEXT,                  -- Top-level comment ID
    reply_level INT DEFAULT 0,             -- Nesting level
    thread_path LTREE,                     -- Hierarchical path
    
    -- Metrics
    likes_count INT DEFAULT 0,
    dislikes_count INT DEFAULT 0,
    replies_count INT DEFAULT 0,
    share_count INT DEFAULT 0,
    engagement_score FLOAT,                -- Calculated based on interactions
    
    -- Sentiment Analysis
    sentiment_score FLOAT,
    sentiment_keywords TEXT[5],            -- Top sentiment-indicating words
    sentiment_magnitude FLOAT,             -- Intensity of sentiment
    
    -- Topic Analysis
    topic_keywords TEXT[],
    named_entities JSONB,                  -- Extracted named entities
    topic_categories TEXT[],               -- Mapped topic categories
    
    -- Content Classification
    is_spam BOOLEAN DEFAULT false,
    toxicity_score FLOAT,
    quality_score FLOAT CHECK (quality_score BETWEEN 0 AND 1),
    
    -- Platform Data
    platform_specific_data JSONB,          -- Platform-specific metadata
    
    -- Temporal
    posted_at TIMESTAMPTZ NOT NULL,
    edited_at TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Comment Aggregation for Articles
CREATE TABLE comments.article_comment_stats (
    article_id INT NOT NULL,
    portal_id INT REFERENCES public.news_portals(portal_id),
    
    -- Comment Counts
    total_comments_count INT DEFAULT 0,
    top_level_comments_count INT DEFAULT 0,
    reply_comments_count INT DEFAULT 0,
    
    -- Engagement Metrics
    total_likes_count INT DEFAULT 0,
    total_dislikes_count INT DEFAULT 0,
    total_shares_count INT DEFAULT 0,
    engagement_rate FLOAT,
    
    -- Sentiment Analysis
    overall_sentiment_score FLOAT,
    sentiment_distribution JSONB,          -- Distribution of sentiment scores
    top_sentiment_keywords TEXT[10],       -- Most significant sentiment words
    
    -- Topic Analysis
    top_discussion_topics TEXT[],          -- Main topics from comments
    topic_distribution JSONB,              -- Topic frequency distribution
    key_entities JSONB,                    -- Important entities mentioned
    
    -- Quality Metrics
    avg_comment_quality FLOAT,
    spam_comment_ratio FLOAT,
    toxic_comment_ratio FLOAT,
    
    -- Temporal Analysis
    peak_activity_periods JSONB,           -- High activity timeframes
    last_comment_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (article_id, portal_id)
);

-- Comment-Topic Relationships
CREATE TABLE comments.comment_topics (
    comment_id TEXT REFERENCES comments.comments(comment_id),
    topic_id INT REFERENCES topics.topics(topic_id),
    
    -- Relationship Metrics
    relevance_score FLOAT CHECK (relevance_score BETWEEN 0 AND 1),
    sentiment_score FLOAT,
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    
    -- Context
    context_summary TEXT,
    key_phrases TEXT[],
    
    -- Classification
    relationship_type VARCHAR(50) CHECK (
        relationship_type IN (
            'direct_discussion',
            'reference',
            'tangential',
            'comparison'
        )
    ),
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (comment_id, topic_id)
);

-- Real-time Comment Trends
CREATE TABLE comments.comment_trends (
    trend_id SERIAL PRIMARY KEY,
    article_id INT NOT NULL,
    portal_id INT REFERENCES public.news_portals(portal_id),
    
    -- Time Window
    window_start TIMESTAMPTZ NOT NULL,
    window_duration INTERVAL NOT NULL,
    
    -- Trend Metrics
    comment_velocity FLOAT,                -- Comments per minute
    engagement_velocity FLOAT,             -- Engagements per minute
    sentiment_trend FLOAT,                 -- Change in sentiment
    
    -- Trending Content
    trending_keywords TEXT[],
    trending_topics TEXT[],
    hot_comments TEXT[],                   -- Highly engaging comments
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (article_id, portal_id, window_start)
);

-- Performance Indexes
CREATE INDEX idx_comments_article ON comments.comments(article_id, portal_id);
CREATE INDEX idx_comments_hierarchy ON comments.comments(parent_comment_id, root_comment_id);
CREATE INDEX idx_comments_path ON comments.comments USING GIST (thread_path);
CREATE INDEX idx_comments_temporal ON comments.comments(posted_at);
CREATE INDEX idx_comments_engagement ON comments.comments(engagement_score DESC);
CREATE INDEX idx_comments_sentiment ON comments.comments(sentiment_score);
CREATE INDEX idx_comments_quality ON comments.comments(quality_score DESC);
CREATE INDEX idx_comments_author ON comments.comments(author_id);

CREATE INDEX idx_comment_stats_temporal ON comments.article_comment_stats(last_comment_at);
CREATE INDEX idx_comment_stats_engagement ON comments.article_comment_stats(engagement_rate DESC);

CREATE INDEX idx_comment_topics_relevance ON comments.comment_topics(relevance_score DESC);
CREATE INDEX idx_comment_topics_sentiment ON comments.comment_topics(sentiment_score);

CREATE INDEX idx_comment_trends_temporal ON comments.comment_trends(window_start, window_duration);
CREATE INDEX idx_comment_trends_velocity ON comments.comment_trends(comment_velocity DESC);

-- Full Text Search
CREATE INDEX idx_comments_text_search ON comments.comments 
    USING GIN (to_tsvector('english', content));

-- Comment Statistics View
CREATE OR REPLACE VIEW comments.comment_activity_view AS
SELECT 
    c.article_id,
    c.portal_id,
    date_trunc('hour', c.posted_at) as hour_bucket,
    count(*) as comment_count,
    avg(c.sentiment_score) as avg_sentiment,
    sum(c.likes_count) as total_likes,
    sum(c.replies_count) as total_replies,
    array_agg(DISTINCT c.topic_categories) as active_topics
FROM 
    comments.comments c
GROUP BY 
    c.article_id,
    c.portal_id,
    date_trunc('hour', c.posted_at);

-- Triggers
CREATE TRIGGER update_comment_updated_at
    BEFORE UPDATE ON comments.comments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_comment_stats_updated_at
    BEFORE UPDATE ON comments.article_comment_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();



5. Social Media Integration
   - Comment Aggregation Structure
   - Engagement Metrics Storage
   - Platform-Specific Requirements

-- Social Media Integration Schema
CREATE SCHEMA IF NOT EXISTS social;

-- Social Media Platforms Configuration
CREATE TABLE social.platforms (
   platform_id SERIAL PRIMARY KEY,
   name VARCHAR(50) NOT NULL UNIQUE,
   api_version VARCHAR(50),
   enabled BOOLEAN DEFAULT true,
   rate_limits JSONB,                     -- API rate limiting rules
   auth_config JSONB,                     -- Authentication configuration
   feature_flags JSONB,                   -- Platform-specific features
   metrics_mapping JSONB,                 -- Platform to internal metrics mapping
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Social Media Posts
CREATE TABLE social.posts (
   post_id TEXT PRIMARY KEY,              -- Platform-specific ID
   platform_id INT REFERENCES social.platforms(platform_id),
   article_id INT NOT NULL,               -- Reference to news article
   portal_id INT REFERENCES public.news_portals(portal_id),
   
   -- Content
   content TEXT NOT NULL,
   content_type VARCHAR(50) CHECK (
       content_type IN ('text', 'image', 'video', 'link', 'poll', 'mixed')
   ),
   language_code VARCHAR(10),
   urls TEXT[],
   media_urls JSONB,
   hashtags TEXT[],
   mentions TEXT[],
   
   -- Author
   author_platform_id TEXT,
   author_username TEXT,
   author_display_name TEXT,
   author_verified BOOLEAN DEFAULT false,
   author_metrics JSONB,                  -- Follower count, etc.
   
   -- Engagement Metrics
   likes_count INT DEFAULT 0,
   shares_count INT DEFAULT 0,
   replies_count INT DEFAULT 0,
   quote_count INT DEFAULT 0,
   bookmark_count INT DEFAULT 0,
   click_count INT DEFAULT 0,
   impression_count INT DEFAULT 0,
   engagement_rate FLOAT,
   viral_score FLOAT,
   
   -- Reach Metrics
   potential_reach INT,                   -- Based on author's followers
   actual_reach INT,                      -- Actual impressions if available
   
   -- Analysis
   sentiment_score FLOAT,
   sentiment_keywords TEXT[5],
   topic_categories TEXT[],
   named_entities JSONB,
   
   -- Platform Data
   platform_specific_data JSONB,          -- Raw platform metrics/data
   monetization_data JSONB,               -- Sponsored content info
   
   -- Temporal
   posted_at TIMESTAMPTZ NOT NULL,
   peak_activity_at TIMESTAMPTZ,
   last_updated_at TIMESTAMPTZ,
   
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Social Media Comments/Replies
CREATE TABLE social.interactions (
   interaction_id TEXT PRIMARY KEY,        -- Platform-specific ID
   platform_id INT REFERENCES social.platforms(platform_id),
   post_id TEXT REFERENCES social.posts(post_id),
   
   -- Hierarchy
   parent_interaction_id TEXT REFERENCES social.interactions(interaction_id),
   thread_path LTREE,
   interaction_depth INT DEFAULT 0,
   
   -- Content
   interaction_type VARCHAR(50) CHECK (
       interaction_type IN ('reply', 'quote', 'mention', 'share')
   ),
   content TEXT,
   language_code VARCHAR(10),
   
   -- Author
   author_platform_id TEXT,
   author_username TEXT,
   author_verified BOOLEAN DEFAULT false,
   author_metrics JSONB,
   
   -- Engagement
   likes_count INT DEFAULT 0,
   replies_count INT DEFAULT 0,
   engagement_score FLOAT,
   
   -- Analysis
   sentiment_score FLOAT,
   sentiment_keywords TEXT[5],
   topic_relevance JSONB,
   quality_score FLOAT,
   
   -- Platform Data
   platform_specific_data JSONB,
   
   posted_at TIMESTAMPTZ NOT NULL,
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Aggregated Social Media Metrics
CREATE TABLE social.article_social_metrics (
   article_id INT NOT NULL,
   portal_id INT REFERENCES public.news_portals(portal_id),
   platform_id INT REFERENCES social.platforms(platform_id),
   
   -- Post Metrics
   total_posts_count INT DEFAULT 0,
   unique_authors_count INT DEFAULT 0,
   
   -- Engagement Totals
   total_likes_count INT DEFAULT 0,
   total_shares_count INT DEFAULT 0,
   total_replies_count INT DEFAULT 0,
   total_impressions_count INT DEFAULT 0,
   
   -- Engagement Rates
   avg_engagement_rate FLOAT,
   engagement_velocity FLOAT,             -- Change over time
   viral_coefficient FLOAT,               -- Sharing cascade factor
   
   -- Reach Metrics
   total_potential_reach INT,
   total_actual_reach INT,
   reach_efficiency FLOAT,                -- actual/potential ratio
   
   -- Audience Analysis
   audience_demographics JSONB,           -- Age, location distributions
   influencer_participation JSONB,        -- Influential user interactions
   
   -- Sentiment Analysis
   overall_sentiment_score FLOAT,
   sentiment_distribution JSONB,
   top_sentiment_keywords TEXT[10],
   
   -- Content Analysis
   trending_hashtags TEXT[],
   key_discussion_topics TEXT[],
   viral_content_pieces JSONB,            -- Most shared/engaged content
   
   -- Temporal
   first_mention_at TIMESTAMPTZ,
   peak_activity_at TIMESTAMPTZ,
   last_activity_at TIMESTAMPTZ,
   
   -- Time Series Data
   hourly_engagement_data JSONB,          -- 24-hour engagement distribution
   daily_trend_data JSONB,                -- Daily metrics for trending
   
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   
   PRIMARY KEY (article_id, portal_id, platform_id)
);

-- Real-time Social Trends
CREATE TABLE social.trending_metrics (
   trend_id SERIAL PRIMARY KEY,
   article_id INT NOT NULL,
   platform_id INT REFERENCES social.platforms(platform_id),
   
   window_start TIMESTAMPTZ NOT NULL,
   window_duration INTERVAL NOT NULL,
   
   -- Velocity Metrics
   posts_velocity FLOAT,                  -- New posts per minute
   engagement_velocity FLOAT,             -- New engagements per minute
   sentiment_velocity FLOAT,              -- Sentiment change rate
   
   -- Trending Content
   trending_hashtags TEXT[],
   trending_topics TEXT[],
   viral_posts TEXT[],                    -- Highly engaging posts
   
   -- Virality Metrics
   viral_coefficient FLOAT,
   amplification_rate FLOAT,
   
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   
   UNIQUE (article_id, platform_id, window_start)
);

-- Performance Indexes
CREATE INDEX idx_posts_article ON social.posts(article_id, portal_id);
CREATE INDEX idx_posts_platform ON social.posts(platform_id, posted_at);
CREATE INDEX idx_posts_engagement ON social.posts(engagement_rate DESC);
CREATE INDEX idx_posts_temporal ON social.posts(posted_at, last_updated_at);
CREATE INDEX idx_posts_viral ON social.posts(viral_score DESC);

CREATE INDEX idx_interactions_post ON social.interactions(post_id);
CREATE INDEX idx_interactions_thread ON social.interactions USING GIST (thread_path);
CREATE INDEX idx_interactions_temporal ON social.interactions(posted_at);
CREATE INDEX idx_interactions_author ON social.interactions(author_platform_id);

CREATE INDEX idx_metrics_temporal ON social.article_social_metrics(last_activity_at);
CREATE INDEX idx_metrics_engagement ON social.article_social_metrics(avg_engagement_rate DESC);
CREATE INDEX idx_metrics_viral ON social.article_social_metrics(viral_coefficient DESC);

CREATE INDEX idx_trends_temporal ON social.trending_metrics(window_start);
CREATE INDEX idx_trends_velocity ON social.trending_metrics(engagement_velocity DESC);

-- Platform-specific Full Text Search
CREATE INDEX idx_posts_text_search ON social.posts 
   USING GIN (to_tsvector('english', content));
CREATE INDEX idx_interactions_text_search ON social.interactions 
   USING GIN (to_tsvector('english', content));

-- Triggers
CREATE TRIGGER update_platform_updated_at
   BEFORE UPDATE ON social.platforms
   FOR EACH ROW
   EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_post_updated_at
   BEFORE UPDATE ON social.posts
   FOR EACH ROW
   EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_interaction_updated_at
   BEFORE UPDATE ON social.interactions
   FOR EACH ROW
   EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_metrics_updated_at
   BEFORE UPDATE ON social.article_social_metrics
   FOR EACH ROW
   EXECUTE FUNCTION update_updated_at_column();

6. Content Analysis Framework
   - Sentiment Analysis Storage
   - Key Words Management
   - Content Statistics Structure

-- Content Analysis Framework Schema
CREATE SCHEMA IF NOT EXISTS analysis;

-- Sentiment Dictionary
CREATE TABLE analysis.sentiment_lexicon (
   word_id SERIAL PRIMARY KEY,
   word VARCHAR(255) NOT NULL UNIQUE,
   language_code VARCHAR(10) NOT NULL DEFAULT 'en',
   base_score FLOAT NOT NULL,             -- Base sentiment score (-1 to 1)
   intensity_multiplier FLOAT DEFAULT 1.0, -- For word intensity
   context_modifiers JSONB,               -- Context-based score adjustments
   part_of_speech VARCHAR(50),            -- Grammatical role
   domain_specific_scores JSONB,          -- Domain-specific sentiment variations
   synonyms TEXT[],
   antonyms TEXT[],
   last_updated_at TIMESTAMPTZ,
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Keyword Management
CREATE TABLE analysis.keywords (
   keyword_id SERIAL PRIMARY KEY,
   keyword VARCHAR(255) NOT NULL,
   normalized_form VARCHAR(255) NOT NULL,
   language_code VARCHAR(10) NOT NULL DEFAULT 'en',
   
   -- Classification
   keyword_type VARCHAR(50) CHECK (
       keyword_type IN (
           'topic', 'entity', 'event', 
           'technical', 'industry', 'generic'
       )
   ),
   category VARCHAR(100),
   subcategories TEXT[],
   
   -- Relevance
   importance_score FLOAT CHECK (importance_score BETWEEN 0 AND 1),
   domain_relevance JSONB,                -- Relevance scores by domain
   
   -- Relationships
   related_keywords TEXT[],
   parent_keywords TEXT[],
   child_keywords TEXT[],
   cooccurring_keywords JSONB,            -- Frequently co-occurring terms
   
   -- Usage Statistics
   occurrence_count INT DEFAULT 0,
   last_seen_at TIMESTAMPTZ,
   trending_score FLOAT,
   
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   
   UNIQUE(normalized_form, language_code)
);

-- Content Analysis Results
CREATE TABLE analysis.content_analysis (
   content_id SERIAL PRIMARY KEY,
   source_type VARCHAR(50) NOT NULL CHECK (
       source_type IN ('article', 'comment', 'social_post', 'title', 'summary')
   ),
   source_id INT NOT NULL,
   portal_id INT REFERENCES public.news_portals(portal_id),
   
   -- Content Metadata
   content_length INT,
   language_code VARCHAR(10),
   content_hash TEXT,                     -- For change detection
   
   -- Readability Metrics
   readability_score FLOAT,
   complexity_score FLOAT,
   technical_density FLOAT,
   
   -- Sentiment Analysis
   overall_sentiment_score FLOAT,
   sentiment_magnitude FLOAT,
   sentiment_aspects JSONB,               -- Aspect-based sentiment
   emotion_scores JSONB,                  -- Different emotion dimensions
   
   -- Keyword Analysis
   extracted_keywords TEXT[],
   keyword_relevance JSONB,              -- Keyword to relevance mapping
   key_phrases TEXT[],
   
   -- Topic Analysis
   main_topics TEXT[],
   topic_distribution JSONB,
   topic_coherence_score FLOAT,
   
   -- Entity Analysis
   named_entities JSONB,
   entity_relationships JSONB,
   
   -- Linguistic Features
   grammar_quality FLOAT,
   style_metrics JSONB,
   language_variety JSONB,                -- Regional language markers
   
   -- Context Analysis
   context_tags TEXT[],
   reference_citations JSONB,
   external_links JSONB,
   
   analyzed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   
   UNIQUE(source_type, source_id)
);

-- Time-based Content Statistics
CREATE TABLE analysis.content_statistics (
   stat_id SERIAL PRIMARY KEY,
   source_type VARCHAR(50) NOT NULL,
   source_id INT NOT NULL,
   time_bucket TIMESTAMPTZ NOT NULL,
   bucket_duration INTERVAL NOT NULL,
   
   -- Volume Metrics
   word_count INT,
   unique_words_count INT,
   sentence_count INT,
   paragraph_count INT,
   
   -- Engagement Statistics
   view_count INT,
   read_time_avg FLOAT,
   completion_rate FLOAT,
   bounce_rate FLOAT,
   
   -- Content Dynamics
   content_velocity FLOAT,                -- Content generation rate
   update_frequency FLOAT,
   freshness_score FLOAT,
   
   -- Keyword Statistics
   keyword_density JSONB,
   trending_keywords TEXT[],
   keyword_velocity JSONB,
   
   -- Topic Evolution
   topic_shifts JSONB,
   topic_emergence JSONB,
   topic_decay JSONB,
   
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   
   UNIQUE(source_type, source_id, time_bucket)
);

-- Semantic Relationships
CREATE TABLE analysis.semantic_relationships (
   relationship_id SERIAL PRIMARY KEY,
   source_term VARCHAR(255) NOT NULL,
   target_term VARCHAR(255) NOT NULL,
   relationship_type VARCHAR(50) CHECK (
       relationship_type IN (
           'synonym', 'antonym', 'hypernym', 
           'hyponym', 'meronym', 'holonym'
       )
   ),
   strength FLOAT CHECK (strength BETWEEN 0 AND 1),
   confidence_score FLOAT,
   context_vector JSONB,                  -- Semantic context
   source_count INT DEFAULT 0,
   last_seen_at TIMESTAMPTZ,
   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
   
   UNIQUE(source_term, target_term, relationship_type)
);

-- Performance Indexes
CREATE INDEX idx_lexicon_word ON analysis.sentiment_lexicon(word);
CREATE INDEX idx_lexicon_language ON analysis.sentiment_lexicon(language_code);
CREATE INDEX idx_lexicon_score ON analysis.sentiment_lexicon(base_score);

CREATE INDEX idx_keywords_normalized ON analysis.keywords(normalized_form);
CREATE INDEX idx_keywords_type ON analysis.keywords(keyword_type, category);
CREATE INDEX idx_keywords_importance ON analysis.keywords(importance_score DESC);
CREATE INDEX idx_keywords_trending ON analysis.keywords(trending_score DESC);

CREATE INDEX idx_content_source ON analysis.content_analysis(source_type, source_id);
CREATE INDEX idx_content_sentiment ON analysis.content_analysis(overall_sentiment_score);
CREATE INDEX idx_content_temporal ON analysis.content_analysis(analyzed_at);

CREATE INDEX idx_stats_temporal ON analysis.content_statistics(time_bucket);
CREATE INDEX idx_stats_source ON analysis.content_statistics(source_type, source_id);

CREATE INDEX idx_semantic_terms ON analysis.semantic_relationships(source_term, target_term);
CREATE INDEX idx_semantic_type ON analysis.semantic_relationships(relationship_type);

-- Full Text Search
CREATE INDEX idx_keywords_text_search ON analysis.keywords 
   USING GIN (to_tsvector('english', keyword || ' ' || coalesce(array_to_string(related_keywords, ' '), '')));

-- Triggers
CREATE TRIGGER update_keyword_updated_at
   BEFORE UPDATE ON analysis.keywords
   FOR EACH ROW
   EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_analysis_updated_at
   BEFORE UPDATE ON analysis.content_analysis
   FOR EACH ROW
   EXECUTE FUNCTION update_updated_at_column();

-- Aggregated Analysis View
CREATE OR REPLACE VIEW analysis.content_trends AS
SELECT 
   source_type,
   date_trunc('hour', analyzed_at) as time_bucket,
   count(*) as analysis_count,
   avg(overall_sentiment_score) as avg_sentiment,
   avg(complexity_score) as avg_complexity,
   jsonb_object_agg(
       DISTINCT topic_distribution ORDER BY topic_distribution DESC
       LIMIT 10
   ) as trending_topics
FROM 
   analysis.content_analysis
GROUP BY 
   source_type,
   date_trunc('hour', analyzed_at);

7. Performance Optimization
   - Index Strategy
   - Partitioning Requirements
   - Query Optimization Structures

8. Schema Enhancement Requirements
   - Missing Table Structures
   - Additional Columns
   - Relationship Modifications

Let's begin with the first section to methodically review and enhance each component. Would you like me to start with the detailed analysis of the Core Schema Analysis section?