I need to create category pages for my project. Category HTML pages after generated should be stored in :
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\categories

You need to define layout of category pages simillar to one of CCN - see atached. 
Rely on following db table to get data from:

Article table DDL:
CREATE TABLE IF NOT EXISTS pt_nyt.articles
(
    article_id uuid NOT NULL DEFAULT gen_random_uuid(),
    title text COLLATE pg_catalog."default" NOT NULL,
    url text COLLATE pg_catalog."default" NOT NULL,
    guid text COLLATE pg_catalog."default",
    description text COLLATE pg_catalog."default",
    content text COLLATE pg_catalog."default",
    author text[] COLLATE pg_catalog."default",
    pub_date timestamp with time zone,
    category_id uuid NOT NULL,
    keywords text[] COLLATE pg_catalog."default",
    reading_time_minutes integer,
    language_code character varying(10) COLLATE pg_catalog."default",
    image_url text COLLATE pg_catalog."default",
    sentiment_score double precision,
    share_count integer DEFAULT 0,
    view_count integer DEFAULT 0,
    comment_count integer DEFAULT 0,
    summary text COLLATE pg_catalog."default",
    tldr text COLLATE pg_catalog."default",
    topics jsonb,
    entities jsonb,
    relations jsonb,
    sentiment_label text COLLATE pg_catalog."default",
    nlp_updated_at timestamp with time zone,
    summary_generated_at timestamp with time zone,
    summary_article_gemini_title text COLLATE pg_catalog."default",
    summary_featured_image text COLLATE pg_catalog."default",
    summary_first_paragraph text COLLATE pg_catalog."default",
    popularity_score integer DEFAULT 0,
    CONSTRAINT articles_pkey PRIMARY KEY (article_id),
    CONSTRAINT articles_guid_key UNIQUE (guid),
    CONSTRAINT unique_url UNIQUE (url),
    CONSTRAINT fk_pt_nyt_article_category FOREIGN KEY (category_id)
        REFERENCES pt_nyt.categories (category_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT articles_sentiment_score_check CHECK (sentiment_score >= '-1'::integer::double precision AND sentiment_score <= 1::double precision)
)


Fields used for building category pages:
SELECT  
category_id,
summary_generated_at,
summary_article_gemini_title,
summary_featured_image,
summary_first_paragraph,
popularity_score
FROM pt_nyt.articles

Sample 2 records:
"summary_first_paragraph"
"<p class=""summary-intro"">A large-scale <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Israeli+Military"" target=""_blank"">Israeli Military</a></strong> operation, named ""Operation <strong class=""time-event"">Iron Wall</strong>"", across several cities in the <strong class=""location""><a href=""https://www.google.com/search?q=West+Bank"" target=""_blank"">West Bank</a></strong>, has resulted in the forced displacement of approximately 40,000 <strong class=""roles-categories"">Palestinians</strong>. This event is considered the largest displacement of civilians in the territory since the <strong class=""time-event"">1967 Six-Day War</strong>.</p>"

Featured image location is in:
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\static\images
Since category pages are located in :
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\categories
make sure you define relative path to images from categories in HTML of the categories pages. 




Popularity score should be used to rank articles on the page:
- highest 1 article is presented like in CNN page:with largest image in top left position. 
- align articles by popularity score and place them simillar to CNN category page: articles with higher popularity score get placed higher. 
- only first 4 articles in category get their featured images displayed
- subcategories should be clearly marked with title and solid line below and below that with titles below of 4 top popular articles as in CNN.
And below that links on 10 others articles, sorted by relevance from that category...displayed in simillar way as on CNN category page. 

When selecting articles to be displayed 