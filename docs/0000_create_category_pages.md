I need to create category pages for my project. Category HTML pages after generated should be stored in :
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\categories

Category pages should link to articles stored in root article folder:
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\articles

relative location of individual articles is stored in field:
article_html_file_location

You need to define layout of category pages simillar to one of CCN - see atached. 
Rely on following db table to get data from articles:

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
    article_html_file_location text COLLATE pg_catalog."default",
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
summary_generated_at - time when article is generated
summary_article_gemini_title - article title
summary_featured_image - featured image of the article (if used - needs to be downsized to usuall image size for article page (maybe 300x200 from image center and store category/images folder))
popularity_score - use it to oreder images 
FROM pt_nyt.articles

Sample 2 records:
"article_id"	"title"	"url"	"guid"	"description"	"content"	"author"	"pub_date"	"category_id"	"keywords"	"reading_time_minutes"	"language_code"	"image_url"	"sentiment_score"	"share_count"	"view_count"	"comment_count"	"summary"	"tldr"	"topics"	"entities"	"relations"	"sentiment_label"	"nlp_updated_at"	"summary_generated_at"	"summary_article_gemini_title"	"summary_featured_image"	"summary_first_paragraph"	"popularity_score"	"article_html_file_location"
"0078e4d3-5782-4c73-a6ae-d791e7d8e914"	"FEMA Quietly Eases Rules Meant to Protect Buildings in Flood Zones"	"https://www.nytimes.com/2025/02/14/climate/fema-quietly-eases-rules-meant-to-protect-buildings-in-flood-zones.html"	"https://www.nytimes.com/2025/02/14/climate/fema-quietly-eases-rules-meant-to-protect-buildings-in-flood-zones.html"	"The agency issued an internal memo saying it would “pause” a regulation directing that schools, libraries and other public facilities damaged by disasters be rebuilt safely."	"The Federal Emergency Management Agency has decided to stop enforcing rules designed to prevent flood damage to schools, libraries, fire stations and other public buildings. Experts say the move, which has not been publicly announced, could endanger public safety and may be in violation of federal law.
The change in policy was laid out in a Feb. 4 memo by FEMA’s chief counsel, Adrian Sevier, that was viewed by The New York Times.
The rule in question, called the Federal Flood Risk Management Standard, was one of the Biden administration’s most significant efforts to address the growing costs of disasters. The rule says that when public buildings in a flood zone are damaged or destroyed, those structures must be rebuilt in a way that prevents future flood damage if they are to qualify for FEMA funding. That could include elevating a structure above the expected height of a future flood or relocating it to a safer spot.
In some cases, the standards also apply to private homes repaired or rebuilt in a flood plain.
The rule has a tortured history. FEMA first proposed it in 2016, in response to an executive order from President Barack Obama. The powerful home-building industry opposed the rule on the grounds that it would increase construction costs. When President Trump first took office in 2017, he revoked Mr. Obama’s order, stopping FEMA’s effort. Soon after taking office in 2021, President Joseph R. Biden Jr. signed a new executive order calling for a federal flood standard, which culminated in 
a final rule
 issued by FEMA last July.
The goal wasn’t just to protect people and property, according to Deanne Criswell, the head of FEMA at the time. It was also to save taxpayers’ money as climate change made flooding more frequent, causing buildings in flood plains to be repeatedly damaged and then repeatedly rebuilt with government help.
“We are going to be able to put a stop to the cycle of response and recovery, and rinse and repeat,” Ms. Criswell said at the time.
Mr. Trump, on his first day back in the White House, again revoked the executive order calling for a federal flood standard. In his memo last week, Mr. Sevier said that while FEMA considers how to amend the rule, the agency will not enforce it. “This pause must be implemented immediately while FEMA takes action to rescind or amend the policies,” Mr. Sevier wrote.
In a statement, FEMA said that the flood rule “is under review per the president’s executive order.”
But FEMA cannot simply stop enforcing a regulation, according to David A. Super, a visiting law professor at Yale University who specializes in administrative law.
If the agency wants to reverse course, it must follow a process clearly laid out by federal law: issuing a public notice, seeking and reviewing public comments and then publishing a new final rule.
Trump Administration: Live Updates
Updated 
Feb. 14, 2025, 7:59 p.m. ET
Feb. 14, 2025
A judge refuses to immediately reinstate inspectors general fired by Trump.
Senior officials could be forced to resign at C.D.C. and N.I.H.
Vance shocks Europe with a message that he has long promoted at home.
Repealing a regulation can take months or longer. Until that happens, the law says that the rule remains in effect, Mr. Super said.
FEMA’s effort to “pause” the rule is in keeping with Mr. Trump’s expansionist view of presidential authority, Mr. Super said. “The president is pursuing an extremely ambitious constitutional agenda to invalidate legislation regulating the executive branch.”
Jennifer Nou, a professor at the University of Chicago Law School, said the legality of FEMA’s decision depends the length of the pause in enforcement. If FEMA stops enforcing the flood rule for an extended period of time, that would put the agency in greater legal jeopardy than just a short pause, she said.
Courts generally give agencies discretion over enforcing rules, Ms. Nou said. “But that discretion is not unlimited,” she added — for example, if the agency’s position amounts to abdicating its responsibility.
Chad Berginnis, executive director of the Association of State Floodplain Managers, said failure to enforce the rule would make people less safe.
Mr. Berginnis offered the example of a water treatment plant that is damaged or destroyed and needs to be rebuilt. 
Under the flood rule, that plant must be built in a way that means it’s unlikely to be damaged by future flooding. Pausing the rule leaves the plant more vulnerable. “We are jeopardizing the safety of the people in that community,” Mr. Berginnis said.
He said pausing the rule also contradicted Mr. Trump’s state goal of reducing government waste.
“Wasteful spending is when you’re spending money on repairing something you know is going to get damaged again,” Mr. Berginnis said. If FEMA doesn’t insist on reasonable flood standards, “we literally are wasting taxpayer money.”"	"{""Christopher Flavelle""}"	"2025-02-14 22:20:15+01"	"2dcb0ef1-1c8a-492e-a434-4a9c25ce4461"	"{""Global Warming"",""Greenhouse Gas Emissions"",""United States Politics and Government"",Floods,""Executive Orders and Memorandums"",""Federal Emergency Management Agency"",""Trump, Donald J"",""Biden, Joseph R Jr""}"	1	"en"	"https://static01.nyt.com/images/2025/02/13/multimedia/00CLI-FEMA-FLOODPLAINS-fqtp/00CLI-FEMA-FLOODPLAINS-fqtp-mediumSquareAt3X-v2.jpg"	0	0	0	0	"<div>
<h1 class=""article-title"">Shockwave Policy Shift: <span class=""emphasis-keyword"">FEMA</span> Abruptly Halts <span class=""emphasis-keyword"">Flood Resilience Rule</span>, Igniting Legal Firestorm and Public Safety Fears</h1>
<div><p class=""source-attribution""><span class=""label"">Source:</span> <span>Federal Emergency Management Agency (FEMA)</span> <span>|</span> <span class=""label"">Published:</span> <span>February 2025</span></p></div>
<div class=""keywords-container"">
<p class=""keywords-heading""><strong class=""named-individual"">Keywords:</strong></p>
<div class=""keywords-tags"">
<span class=""keyword-pill"">FEMA</span>
<span class=""keyword-pill"">Federal Flood Risk Management Standard (FFRMS)</span>
<span class=""keyword-pill"">Flood Resilience</span>
<span class=""keyword-pill"">Executive Order</span>
<span class=""keyword-pill"">Trump Administration</span>
<span class=""keyword-pill"">Biden Administration</span>
<span class=""keyword-pill"">Climate Change Adaptation</span>
<span class=""keyword-pill"">Public Safety</span>
<span class=""keyword-pill"">Administrative Law</span>
<span class=""keyword-pill"">Taxpayer Money</span>
</div>
</div>
<div class=""separator""></div>
<strong class=""named-individual"">Entity Overview:</strong>
<div class=""entity-grid"">
<div class=""entity-category"">
<h3 class=""entity-category-title"">NAMED INDIVIDUALS:</h3>
<p class=""entity-list""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=Adrian+Sevier"" target=""_blank"">Adrian Sevier</a></u></strong> (FEMA Chief Counsel), <strong class=""named-individual""><u><a href=""https://www.google.com/search?q=President+Barack+Obama"" target=""_blank"">President Barack Obama</a></u></strong>, <strong class=""named-individual""><u><a href=""https://www.google.com/search?q=President+Donald+Trump"" target=""_blank"">President Donald Trump</a></u></strong>, <strong class=""named-individual""><u><a href=""https://www.google.com/search?q=President+Joseph+R.+Biden+Jr."" target=""_blank"">President Joseph R. Biden Jr.</a></u></strong>, <strong class=""named-individual""><u><a href=""https://www.google.com/search?q=Deanne+Criswell"" target=""_blank"">Deanne Criswell</a></u></strong> (former FEMA head), <strong class=""named-individual""><u><a href=""https://www.google.com/search?q=David+A.+Super"" target=""_blank"">David A. Super</a></u></strong> (Yale Law Professor), <strong class=""named-individual""><u><a href=""https://www.google.com/search?q=Jennifer+Nou"" target=""_blank"">Jennifer Nou</a></u></strong> (University of Chicago Law Professor), <strong class=""named-individual""><u><a href=""https://www.google.com/search?q=Chad+Berginnis"" target=""_blank"">Chad Berginnis</a></u></strong> (Association of State Floodplain Managers)</p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">ROLES &amp; CATEGORIES:</h3>
<p class=""entity-list""><span class=""roles-categories"">Experts</span>, <span class=""roles-categories"">Taxpayers</span>, <span class=""roles-categories"">Law professors</span>, <span class=""roles-categories"">Floodplain managers</span>, <span class=""roles-categories"">Federal agencies</span></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">ORGANIZATIONS &amp; PRODUCTS:</h3>
<p class=""entity-list""><strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">Federal Emergency Management Agency (FEMA)</a></strong>, <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Biden+administration"" target=""_blank"">Biden administration</a></strong>, <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Trump+administration"" target=""_blank"">Trump administration</a></strong>, <strong class=""orgs-products""><a href=""https://www.google.com/search?q=home-building+industry"" target=""_blank"">Home-building industry</a></strong>, <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Yale+University"" target=""_blank"">Yale University</a></strong>, <strong class=""orgs-products""><a href=""https://www.google.com/search?q=University+of+Chicago+Law+School"" target=""_blank"">University of Chicago Law School</a></strong>, <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Association+of+State+Floodplain+Managers"" target=""_blank"">Association of State Floodplain Managers</a></strong>, <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Public+buildings"" target=""_blank"">Public buildings</a></strong> (schools, libraries, fire stations, water treatment plants), <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Private+homes"" target=""_blank"">Private homes</a></strong>, <strong class=""orgs-products""><a href=""https://www.google.com/search?q=National+Flood+Insurance+Program+(NFIP)"" target=""_blank"">National Flood Insurance Program (NFIP)</a></strong></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">LOCATIONS:</h3>
<p class=""entity-list""><strong class=""location""><a href=""https://www.google.com/search?q=United+States"" target=""_blank"">United States</a></strong>, <strong class=""location""><a href=""https://www.google.com/search?q=Flood+zones"" target=""_blank"">Flood zones / Flood plains</a></strong>, <strong class=""location""><a href=""https://www.google.com/search?q=White+House"" target=""_blank"">White House</a></strong></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">TIME PERIODS &amp; EVENTS:</h3>
<p class=""entity-list""><span class=""time-event"">Feb. 4, 2025</span> (Memo date), <span class=""time-event"">2015</span> (Obama EO 13690), <span class=""time-event"">2016</span> (FEMA first proposes rule), <span class=""time-event"">2017</span> (Trump revokes Obama EO), <span class=""time-event"">2021</span> (Biden reinstates standard via EO 14030), <span class=""time-event"">July 2024</span> (FEMA final rule issued), <span class=""time-event"">Jan. 20, 2025</span> (Trump revokes Biden EO 14030), <span class=""time-event"">Future</span></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">ARTISTIC CONCEPTS &amp; DESIGN ELEMENTS:</h3>
<p class=""entity-list""><em class=""no-entity"">None identified</em></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">INDUSTRY TERMINOLOGY:</h3>
<p class=""entity-list""><span class=""industry"">Federal Flood Risk Management Standard (FFRMS)</span>, <span class=""industry"">Floodplain management</span>, <span class=""industry"">Flood resilience</span>, <span class=""industry"">Disaster recovery</span>, <span class=""industry"">Climate change adaptation</span>, <span class=""industry"">Sea-level rise</span>, <span class=""industry"">Base Flood Elevation (BFE)</span>, <span class=""industry"">100-year floodplain</span>, <span class=""industry"">500-year floodplain</span>, <span class=""industry"">Critical actions</span></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">FINANCIAL &amp; BUSINESS TERMS:</h3>
<p class=""entity-list""><span class=""financial"">FEMA funding</span>, <span class=""financial"">Construction costs</span>, <span class=""financial"">Taxpayer money</span>, <span class=""financial"">Government waste</span>, <span class=""financial"">Disaster aid</span>, <span class=""financial"">Insurance costs</span>, <span class=""financial"">Climate-related financial risk</span></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">KEY ACTIONS &amp; RELATIONSHIPS:</h3>
<p class=""entity-list""><span class=""key-actions"">Stop enforcing</span>, <span class=""key-actions"">Prevent flood damage</span>, <span class=""key-actions"">Endanger public safety</span>, <span class=""key-actions"">Violate federal law</span>, <span class=""key-actions"">Rebuild</span>, <span class=""key-actions"">Elevate structure</span>, <span class=""key-actions"">Relocate</span>, <span class=""key-actions"">Oppose rule</span>, <span class=""key-actions"">Revoke order</span>, <span class=""key-actions"">Reinstate standard</span>, <span class=""key-actions"">Save money</span>, <span class=""key-actions"">Pause implementation</span>, <span class=""key-actions"">Rescind/Amend policies</span>, <span class=""key-actions"">Follow process</span>, <span class=""key-actions"">Jeopardize safety</span>, <span class=""key-actions"">Waste money</span></p>
</div>
</div>
<div class=""divider""></div>
<strong class=""named-individual"">Summary:</strong>
<p class=""summary-intro""><span class=""key-sentence"">A significant and potentially illegal policy reversal is underway at the <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">Federal Emergency Management Agency (FEMA)</a></strong>, which has abruptly decided to stop enforcing crucial regulations designed to protect <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Public+buildings"" target=""_blank"">public buildings</a></strong> like schools, libraries, and fire stations from devastating flood damage.</span> This unannounced shift, revealed through an internal memo dated <span class=""time-event"">Feb. 4, 2025</span>, from <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong>'s chief counsel, <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=Adrian+Sevier"" target=""_blank"">Adrian Sevier</a></u></strong></span>, effectively shelves the <span class=""industry"">Federal Flood Risk Management Standard (FFRMS)</span>, a key initiative aimed at bolstering national resilience against the escalating costs and dangers of flooding, exacerbated by <span class=""industry"">climate change</span>. <span class=""roles-categories"">Experts</span> warn this move not only <span class=""key-actions"">endangers public safety</span> but may also directly <span class=""key-actions"">violate federal law</span>, setting the stage for potential legal battles and leaving communities vulnerable.</p>
<p class=""supporting-point"">The <span class=""industry"">Federal Flood Risk Management Standard (FFRMS)</span> represents a cornerstone of recent federal efforts to adapt to worsening flood risks. Finalized by <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong> in <span class=""time-event"">July 2024</span> under the <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Biden+administration"" target=""_blank"">Biden administration</a></strong>, the <span class=""industry"">rule</span> mandated that when <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Public+buildings"" target=""_blank"">public buildings</a></strong> (and in some cases, <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Private+homes"" target=""_blank"">private homes</a></strong>) located in designated <strong class=""location""><a href=""https://www.google.com/search?q=Flood+zones"" target=""_blank"">flood zones</a></strong> are substantially damaged or destroyed, they must be <span class=""key-actions"">rebuilt</span> using methods that actively <span class=""key-actions"">prevent future flood damage</span> to qualify for <span class=""financial"">FEMA funding</span>. These methods could include <span class=""key-actions"">elevating the structure</span> significantly above anticipated future flood levels (often defined by adding freeboard to the <span class=""industry"">Base Flood Elevation (BFE)</span> or using the <span class=""industry"">500-year floodplain</span> standard) or <span class=""key-actions"">relocating</span> the entire facility to a less hazardous area. Some approaches under the <span class=""industry"">FFRMS</span> even called for using climate-informed science to anticipate future conditions like <span class=""industry"">sea-level rise</span>.</p>
<p class=""secondary-detail"">The stated goal, articulated by former <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong> head <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=Deanne+Criswell"" target=""_blank"">Deanne Criswell</a></u></strong></span>, was twofold: safeguard lives and property, and crucially, <span class=""key-actions"">save</span> <span class=""financial"">taxpayer money</span>. By breaking the costly cycle of ""flood-rebuild-repeat""—where structures in <strong class=""location""><a href=""https://www.google.com/search?q=Flood+zones"" target=""_blank"">flood plains</a></strong> are repeatedly damaged by worsening floods and subsequently rebuilt, often to inadequate pre-flood standards, with federal <span class=""financial"">disaster aid</span>—the <span class=""industry"">rule</span> aimed for long-term fiscal responsibility and enhanced community safety. Search results indicate that between <span class=""time-event"">2015</span> and <span class=""time-event"">2024</span>, <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong> spent over <span class=""crucial-fact"">$60 billion</span> rebuilding public infrastructure after floods, largely to standards now considered inadequate under <span class=""industry"">FFRMS</span>, highlighting the immense costs involved.</p>
<p class=""supporting-point"">The path to the <span class=""industry"">FFRMS</span> was politically turbulent. It originated from an <span class=""industry"">executive order</span> (EO 13690) signed by <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=President+Barack+Obama"" target=""_blank"">President Barack Obama</a></u></strong></span> in <span class=""time-event"">2015</span>. <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong> first proposed the implementing <span class=""industry"">rule</span> in <span class=""time-event"">2016</span>, but faced strong opposition from the powerful <strong class=""orgs-products""><a href=""https://www.google.com/search?q=home-building+industry"" target=""_blank"">home-building industry</a></strong>, concerned about increased <span class=""financial"">construction costs</span>. Upon taking office in <span class=""time-event"">2017</span>, <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=President+Donald+Trump"" target=""_blank"">President Donald Trump</a></u></strong></span> promptly <span class=""key-actions"">revoked</span> <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=President+Barack+Obama"" target=""_blank"">Obama</a></u></strong></span>'s order (via EO 13807), halting <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong>'s efforts. The <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Biden+administration"" target=""_blank"">Biden administration</a></strong> prioritized its revival, with <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=President+Joseph+R.+Biden+Jr."" target=""_blank"">President Joseph R. Biden Jr.</a></u></strong></span> signing a new <span class=""industry"">executive order</span> (EO 14030) in <span class=""time-event"">2021</span> that explicitly <span class=""key-actions"">reinstated</span> the <span class=""industry"">standard</span>, leading to the final <span class=""industry"">rule</span> issued by <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong> in <span class=""time-event"">July 2024</span>.</p>
<img alt=""Flood waters surrounding homes, illustrating vulnerability in flood zones"" src=""https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/FEMA_-_42461_-_Flood_waters_surround_homes_in_North_Dakota.jpg/640px-FEMA_-_42461_-_Flood_waters_surround_homes_in_North_Dakota.jpg""/>
<p class=""transition-text"">However, echoing his previous actions, <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=President+Donald+Trump"" target=""_blank"">President Trump</a></u></strong></span>, reportedly on his first day back in the <strong class=""location""><a href=""https://www.google.com/search?q=White+House"" target=""_blank"">White House</a></strong> (<span class=""time-event"">Jan. 20, 2025</span>), issued EO 14148, once again <span class=""key-actions"">revoking</span> the <span class=""industry"">executive order</span> underpinning the <span class=""industry"">FFRMS</span>. Following this directive, <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong>'s chief counsel, <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=Adrian+Sevier"" target=""_blank"">Adrian Sevier</a></u></strong></span>, issued the <span class=""time-event"">Feb. 4</span> memo instructing staff to immediately <span class=""key-actions"">pause implementation</span> of the <span class=""industry"">FFRMS</span> policies while the agency determines whether to formally <span class=""key-actions"">rescind or amend</span> them. <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong> publicly stated the <span class=""industry"">rule</span> ""is under review per the president's <span class=""industry"">executive order</span>.""</p>
<p class=""supporting-point""><span class=""key-sentence"">This ""pause"" has triggered significant legal alarm bells.</span> According to <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=David+A.+Super"" target=""_blank"">David A. Super</a></u></strong></span>, a visiting <span class=""roles-categories"">law professor</span> at <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Yale+University"" target=""_blank"">Yale University</a></strong> specializing in <span class=""industry"">administrative law</span>, <span class=""roles-categories"">federal agencies</span> like <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong> cannot simply decide to <span class=""key-actions"">stop enforcing</span> a duly enacted regulation. The <span class=""industry"">Administrative Procedure Act (APA)</span> mandates a specific, public process for changing or repealing regulations. This involves issuing a public notice of the proposed change, soliciting and reviewing public comments, and finally publishing a new final <span class=""industry"">rule</span> in the Federal Register. Until this process is completed, which can take months or even years, the existing <span class=""industry"">rule</span> legally remains in effect. <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=David+A.+Super"" target=""_blank"">Super</a></u></strong></span> suggests this move aligns with an ""extremely ambitious constitutional agenda"" by the <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Trump+administration"" target=""_blank"">Trump administration</a></strong> seeking to expand presidential authority over the executive branch.</p>
<p class=""secondary-detail""><span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=Jennifer+Nou"" target=""_blank"">Jennifer Nou</a></u></strong></span>, a professor at the <strong class=""orgs-products""><a href=""https://www.google.com/search?q=University+of+Chicago+Law+School"" target=""_blank"">University of Chicago Law School</a></strong>, concurs that while courts generally grant agencies discretion in enforcement, this discretion is not absolute. An extended pause, potentially amounting to an abdication of <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong>'s responsibility to enforce its own regulations, would place the agency in greater legal jeopardy than a short-term suspension. The failure to follow the APA's required procedures opens the door to legal challenges arguing the pause itself is unlawful.</p>
<img alt=""Elevated home in a flood-prone area, showcasing resilient building practices"" src=""https://api.army.mil/e2/c/images/2012/11/13/271313/max1200.jpg""/>
<p class=""supporting-point"">Beyond the legal questions, the practical consequences of suspending the <span class=""industry"">FFRMS</span> are dire, according to <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=Chad+Berginnis"" target=""_blank"">Chad Berginnis</a></u></strong></span>, executive director of the <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Association+of+State+Floodplain+Managers"" target=""_blank"">Association of State Floodplain Managers</a></strong>. <span class=""key-sentence"">He argues forcefully that failing to enforce the <span class=""industry"">rule</span> directly <span class=""key-actions"">jeopardizes public safety</span>.</span> Using the example of a damaged water treatment plant, <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=Chad+Berginnis"" target=""_blank"">Berginnis</a></u></strong></span> explains that under the <span class=""industry"">FFRMS</span>, it would have to be rebuilt to withstand future floods. Pausing the <span class=""industry"">rule</span> means it could be rebuilt to older, less protective standards, leaving it vulnerable to the next flood and potentially cutting off essential services when most needed. ""We are jeopardizing the safety of the people in that community,"" he stated emphatically.</p>
<p class=""supporting-point""><span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=Chad+Berginnis"" target=""_blank"">Berginnis</a></u></strong></span> and other critics, like Rob Moore from the Natural Resources Defense Council, also highlight a stark contradiction: the pause undermines the <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Trump+administration"" target=""_blank"">Trump administration</a></strong>'s stated goal of reducing <span class=""financial"">government waste</span>. <span class=""key-sentence"">True <span class=""financial"">wasteful spending</span>, <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=Chad+Berginnis"" target=""_blank"">Berginnis</a></u></strong></span> argues, occurs ""when you're spending money on repairing something you know is going to get damaged again.""</span> By not insisting on reasonable, forward-looking <span class=""industry"">flood resilience</span> standards for federally funded rebuilding projects, <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong> ensures that billions more in <span class=""financial"">taxpayer money</span> will inevitably be spent repairing the same structures after future, predictable flood events. The incremental cost of building to a higher standard now is often far less than the repeated costs of repair and replacement, not to mention the disruption and potential loss of life.</p>
<p class=""transition-text"">The decision throws into sharp relief the ongoing tension between short-term <span class=""financial"">construction costs</span>, a major concern for the <strong class=""orgs-products""><a href=""https://www.google.com/search?q=home-building+industry"" target=""_blank"">home-building industry</a></strong>, and the long-term benefits of investing in <span class=""industry"">flood resilience</span>. As <span class=""industry"">climate change</span> continues to drive more frequent and intense flooding across the <strong class=""location""><a href=""https://www.google.com/search?q=United+States"" target=""_blank"">United States</a></strong>, the <span class=""industry"">FFRMS</span> was seen as a critical tool for federal <span class=""industry"">climate change adaptation</span>.</p>
<p class=""supporting-point"">The suspension of its enforcement raises profound questions about the nation's preparedness for future disasters, the stability of federal regulatory processes, and the responsible stewardship of public funds. Communities recovering from floods now face uncertainty about rebuilding standards, while <span class=""roles-categories"">taxpayers</span> face the prospect of footing ever-larger bills for disaster recovery efforts that fail to account for the escalating risks of a changing climate. The full legal and societal ramifications of <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong>'s abrupt policy shift are yet to unfold but are likely to be significant and far-reaching.</p>
<div class=""gradient-divider""></div>
<strong class=""named-individual"">Interesting Facts:</strong>
<div class=""facts-container"">
<ul class=""facts-list"">
<li class=""fact-primary"">
<span class=""fact-bullet"">•</span> The <span class=""industry"">Federal Flood Risk Management Standard (FFRMS)</span> builds upon Executive Order 11988, originally signed by President Carter in <span class=""date-numeric"">May 1977</span>, which first directed federal agencies to avoid supporting development in <strong class=""location""><a href=""https://www.google.com/search?q=Flood+zones"" target=""_blank"">flood plains</a></strong> unless no practicable alternative exists.
      </li>
<li class=""fact-secondary"">
<span class=""fact-bullet-secondary"">•</span> Under the <span class=""industry"">FFRMS</span>, agencies could choose one of three approaches to determine the required flood protection level: the Freeboard Value Approach (adding 2-3 feet to the <span class=""industry"">100-year flood</span> elevation), the <span class=""industry"">500-year flood</span> elevation, or a Climate-Informed Science Approach (CISA) using future climate projections.
      </li>
<li class=""fact-primary"">
<span class=""fact-bullet"">•</span> <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong> estimated that buildings constructed to <strong class=""orgs-products""><a href=""https://www.google.com/search?q=National+Flood+Insurance+Program+(NFIP)"" target=""_blank"">NFIP</a></strong> standards (which are less stringent than <span class=""industry"">FFRMS</span> in some cases) suffer approximately <span class=""number-numeric"">80%</span> less damage annually than non-compliant buildings, suggesting higher standards yield significant savings.
      </li>
<li class=""fact-secondary"">
<span class=""fact-bullet-secondary"">•</span> Suspending a community from the <strong class=""orgs-products""><a href=""https://www.google.com/search?q=National+Flood+Insurance+Program+(NFIP)"" target=""_blank"">National Flood Insurance Program (NFIP)</a></strong> for non-compliance with <span class=""industry"">floodplain management</span> rules can make federally backed mortgages unavailable in Special Flood Hazard Areas and render the community ineligible for certain federal grants. While the <span class=""industry"">FFRMS</span> pause isn't an <strong class=""orgs-products""><a href=""https://www.google.com/search?q=National+Flood+Insurance+Program+(NFIP)"" target=""_blank"">NFIP</a></strong> suspension, it reflects a similar disregard for established risk reduction measures.
      </li>
<li class=""fact-primary"">
<span class=""fact-bullet"">•</span> The <span class=""industry"">Administrative Procedure Act (APA)</span> generally requires agencies to follow ""notice-and-comment"" rulemaking to issue, amend, or repeal regulations, ensuring public participation and transparency. Exceptions exist but are narrow, particularly for substantive rule changes.
      </li>
<li class=""fact-secondary"">
<span class=""fact-bullet-secondary"">•</span> Studies show proactive investments in climate resilience offer significant returns; estimates suggest every <span class=""financial"">$1</span> invested can save more than <span class=""financial"">$6</span> in future disaster recovery costs.
      </li>
<li class=""fact-primary"">
<span class=""fact-bullet"">•</span> <span class=""industry"">Climate change</span> is measurably increasing flood risk. Heavy downpours have become more frequent and intense across the <strong class=""location""><a href=""https://www.google.com/search?q=United+States"" target=""_blank"">US</a></strong> over the past <span class=""number-numeric"">50-60</span> years, particularly in the Northeast, Midwest, and Southeast. Hourly rainfall intensity has increased by an average of <span class=""number-numeric"">15%</span> since <span class=""date-numeric"">1970</span> in many cities.
      </li>
<li class=""fact-conclusion"">
<span class=""fact-bullet"">•</span> The Union of Concerned Scientists projects that by <span class=""date-numeric"">2050</span>, nearly <span class=""number-numeric"">1,100</span> critical infrastructure assets (including housing, hospitals, power plants) along <strong class=""location""><a href=""https://www.google.com/search?q=United+States"" target=""_blank"">US</a></strong> coastlines could face tidal flooding <span class=""number-numeric"">12</span> times per year, highlighting the urgent need for resilience standards like the <span class=""industry"">FFRMS</span>.
      </li>
</ul>
</div>
<div class=""facts-divider""></div>
<strong class=""named-individual"">Sentiment Analysis:</strong>
<div class=""entity-sentiment"">
<h4 class=""entity-name""><strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">Federal Emergency Management Agency (FEMA)</a></strong></h4>
<p class=""entity-sentiment-details"">
       Positive: <span class=""sentiment-positive"">5</span> | Negative: <span class=""sentiment-negative"">35</span>
</p>
<p class=""entity-summary"">Comments express strong criticism regarding FEMA's decision to pause the FFRMS, viewing it as irresponsible, legally dubious, and harmful to public safety and taxpayer interests. Some acknowledge FEMA's role in disaster response but see this specific action as undermining its mission.</p>
<p class=""entity-keywords"">Key words/phrases: Irresponsible, illegal pause, endangering public, wasting taxpayer money, political decision, needs enforcement, disaster response</p>
</div>
<div class=""entity-sentiment"">
<h4 class=""entity-name""><strong class=""orgs-products""><a href=""https://www.google.com/search?q=Trump+administration"" target=""_blank"">Trump Administration</a></strong></h4>
<p class=""entity-sentiment-details"">
       Positive: <span class=""sentiment-positive"">8</span> | Negative: <span class=""sentiment-negative"">42</span>
</p>
<p class=""entity-summary"">Sentiment is largely negative, framing the revocation of the FFRMS executive order and subsequent pause as short-sighted, anti-environment, and prioritizing deregulation over safety and fiscal responsibility. Supporters might view it as reducing burdensome regulations.</p>
<p class=""entity-keywords"">Key words/phrases: Deregulation, anti-climate, short-sighted, wasteful, executive order, reducing burden, political interference</p>
</div>
<div class=""entity-sentiment"">
<h4 class=""entity-name""><span class=""industry"">Federal Flood Risk Management Standard (FFRMS)</span></h4>
<p class=""entity-sentiment-details"">
       Positive: <span class=""sentiment-positive"">45</span> | Negative: <span class=""sentiment-negative"">10</span>
</p>
<p class=""entity-summary"">The FFRMS itself receives overwhelmingly positive commentary, seen as a common-sense, necessary measure for climate adaptation, public safety, and saving taxpayer dollars long-term. Negative comments typically echo industry concerns about increased building costs or regulatory overreach.</p>
<p class=""entity-keywords"">Key words/phrases: Necessary, common sense, protects lives, saves money, resilience, climate adaptation, long overdue, increased costs, burdensome</p>
</div>
<div class=""entity-sentiment"">
<h4 class=""entity-name""><strong class=""orgs-products""><a href=""https://www.google.com/search?q=Biden+administration"" target=""_blank"">Biden Administration</a></strong></h4>
<p class=""entity-sentiment-details"">
       Positive: <span class=""sentiment-positive"">25</span> | Negative: <span class=""sentiment-negative"">5</span>
</p>
<p class=""entity-summary"">Comments generally praise the Biden administration for reinstating and finalizing the FFRMS, viewing it as a positive step towards addressing climate risks and improving infrastructure resilience. Criticism is minimal in this specific context.</p>
<p class=""entity-keywords"">Key words/phrases: Climate action, resilience, responsible policy, reinstated standard, forward-looking, necessary regulation</p>
</div>
<div class=""popularity-container"">
<h2 class=""popularity-title"">Popularity</h2>
<div class=""popularity-score"">
<div class=""popularity-number"">65</div>
<div class=""popularity-description"">The topic has moderate public interest, primarily discussed in policy, environmental, and disaster management circles.</div>
</div>
</div>
<strong class=""named-individual"">More on topic and related terminology:</strong>
<div class=""more-on-topic-container"">
<ul class=""related-terminology-list"">
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=FEMA+Halts+Rule+That+Protects+Against+Future+Floods+-+ASFPM"" target=""_blank"">FEMA Halts Rule That Protects Against Future Floods - ASFPM</a> - <span class=""resource-description"">ASFPM reports on the Trump administration ordering FEMA to halt FFRMS implementation, quoting experts on the dangers and wasted taxpayer money.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=FEMA+halts+enforcement+of+flood+rebuild+rule+Facilities+Dive"" target=""_blank"">FEMA halts enforcement of flood rebuild rule - Facilities Dive</a> - <span class=""resource-description"">Discusses the unannounced decision based on the Sevier memo, the rule's goal, and criticism about costs vs. long-term savings, plus potential legal challenges.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=FEMA+pauses+enforcement+of+flood+protection+rules+following+Trump+executive+order+Port+City+Daily"" target=""_blank"">FEMA pauses enforcement of flood protection rules following Trump executive order - Port City Daily</a> - <span class=""resource-description"">Covers the history of the FFRMS under Obama, Trump, and Biden, details the pause via the Sevier memo, and includes quotes on the impact and contradiction with saving money.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=FEMA+Eases+Floodplain+Requirements+for+Federally+Funded+Projects+March+2025"" target=""_blank"">FEMA Eases Floodplain Requirements for Federally Funded Projects - FEMA Press Release (Simulated)</a> - <span class=""resource-description"">A simulated FEMA press release announcing the cessation of FFRMS implementation effective March 25, 2025, citing Trump's EO 14148 and aiming to reduce burdens.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=The+Federal+Flood+Risk+Management+Standard+(FFRMS)+CRS+Report"" target=""_blank"">The Federal Flood Risk Management Standard (FFRMS) - CRS Report</a> - <span class=""resource-description"">Congressional Research Service overview explaining the FFRMS, its purpose, and the history of relevant Executive Orders (11988, 13690, 13807, 13990, 14030).</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Report:+FEMA+Stops+Enforcing+Biden-Era+Flood+Rule+Newsmax"" target=""_blank"">Report: FEMA Stops Enforcing Biden-Era Flood Rule - Newsmax</a> - <span class=""resource-description"">Reports on the NYT story about FEMA stopping FFRMS enforcement, details the rule's history, and includes quotes on legality and consequences from experts like Super and Berginnis.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=FEMA+halts+enforcement+of+flood+protection+rule+for+public+buildings+EHN"" target=""_blank"">FEMA halts enforcement of flood protection rule for public buildings - EHN</a> - <span class=""resource-description"">Summarizes the situation, highlighting the suspension of the Biden-era rule, the role of Trump's EO, legal concerns about the APA, and the implications for safety and taxpayer spending.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Federal+Flood+Risk+Management+Standard+FEMA.gov+overview"" target=""_blank"">Federal Flood Risk Management Standard | FEMA.gov</a> - <span class=""resource-description"">FEMA's official page (pre-pause) explaining the FFRMS, its purpose for resilience, the final rule publication date, and the flexible approaches allowed.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Flooded+and+Unprepared:+How+Climate+Change+is+Testing+U.S.+Infrastructure"" target=""_blank"">Flooded and Unprepared: How Climate Change is Testing U.S. Infrastructure</a> - <span class=""resource-description"">Discusses the increasing strain on US infrastructure due to climate change-driven flooding and the need for updated standards and resilient investments.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Formal+Agency+Rulemaking+Under+the+Law+Administrative+Law+Center+Justia"" target=""_blank"">Formal Agency Rulemaking Under the Law | Administrative Law Center - Justia</a> - <span class=""resource-description"">Explains the formal and informal rulemaking processes under the Administrative Procedure Act (APA), including notice, comment, and hearing requirements.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Agency+Rescissions+of+Legislative+Rules+CRS+Report"" target=""_blank"">Agency Rescissions of Legislative Rules - CRS Report</a> - <span class=""resource-description"">Details how the APA's notice-and-comment requirements generally apply to the repeal and amendment of existing rules, not just their initial issuance.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Administrative+Procedure+Act+Cornell+LII"" target=""_blank"">Administrative Procedure Act | Wex | US Law | LII / Legal Information Institute</a> - <span class=""resource-description"">Provides a legal overview of the APA, defining rulemaking (formulating, amending, or repealing a rule) and outlining the governance of formal and informal processes.</span>
</li>
</ul>
</div>
<div class=""more-topic-divider""></div>
<img alt=""Destroyed building foundations after a major flood event, emphasizing the need for resilient construction"" src=""https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/Hurricane_Ike_damage_10.jpg/640px-Hurricane_Ike_damage_10.jpg""/>
</div>"						"2025-03-27 12:16:27.746199+01"	"2025-03-27 12:16:00+01"	"FEMA's Shock Move : Flood Protection Rules Halted, Igniting Safety Fears and Legal Firestorm"	"{""url"": ""FEMA_Quietly_Eases_Rules_Meant_1.jpg"", ""alt"": ""FEMA - 3608 - Photograph by Leif Skoogfors taken on 07-27-2001 in West Virginia"", ""caption"": ""FEMA - 3608 - Photograph by Leif Skoogfors taken on 07-27-2001 in West Virginia""}"	"<p class=""summary-intro""><span class=""key-sentence"">A significant and potentially illegal policy reversal is underway at the <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">Federal Emergency Management Agency (FEMA)</a></strong>, which has abruptly decided to stop enforcing crucial regulations designed to protect <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Public+buildings"" target=""_blank"">public buildings</a></strong> like schools, libraries, and fire stations from devastating flood damage.</span> This unannounced shift, revealed through an internal memo dated <span class=""time-event"">Feb. 4, 2025</span>, from <strong class=""orgs-products""><a href=""https://www.google.com/search?q=Federal+Emergency+Management+Agency"" target=""_blank"">FEMA</a></strong>'s chief counsel, <span class=""entity-spacing""><strong class=""named-individual""><u><a href=""https://www.google.com/search?q=Adrian+Sevier"" target=""_blank"">Adrian Sevier</a></u></strong></span>, effectively shelves the <span class=""industry"">Federal Flood Risk Management Standard (FFRMS)</span>, a key initiative aimed at bolstering national resilience against the escalating costs and dangers of flooding, exacerbated by <span class=""industry"">climate change</span>. <span class=""roles-categories"">Experts</span> warn this move not only <span class=""key-actions"">endangers public safety</span> but may also directly <span class=""key-actions"">violate federal law</span>, setting the stage for potential legal battles and leaving communities vulnerable.</p>"	65	"climate\FEMAs_Shock_Move_Flood_Protection_Rules_Halted_Ign.html"
"0aca5c83-6d29-4eff-863e-8e8e1d61f205"	"How to Use Up Rotisserie Chicken"	"https://cooking.nytimes.com/article/rotisserie-chicken-recipes"	"https://cooking.nytimes.com/article/rotisserie-chicken-recipes"	"Last night, a hot bird saved my life."	"Last night, a hot bird saved my life."	"{""Michael Linares""}"	"2025-02-18 19:46:57+01"	"e795d2e7-0f8a-47ff-9efc-b5c570e5dcec"	"{""Cooking and Cookbooks"",""Content Type: Service"",Poultry}"	1	"en"	"https://static01.nyt.com/images/2025/02/18/multimedia/18ROTISSERIE-CHICKEN-Chili-vjgq/18ROTISSERIE-CHICKEN-Chili-vjgq-mediumSquareAt3X.jpg"	0	0	0	0	"<div>
<h1 class=""article-title"">Miracle in the Night: How a Mysterious <span class=""emphasis-keyword"">""Hot Bird""</span> Became an Unlikely Savior</h1>
<div><p class=""source-attribution""><span class=""label"">Source:</span> <span>Author: Unknown</span> <span>|</span> <span class=""label"">Published:</span> <span>March 2025</span></p></div>
<div class=""keywords-container"">
<p class=""keywords-heading""><strong class=""named-individual"">Keywords:</strong></p>
<div class=""keywords-tags"">
<span class=""keyword-pill"">hot bird</span>
<span class=""keyword-pill"">saved life</span>
<span class=""keyword-pill"">rescue</span>
<span class=""keyword-pill"">salvation</span>
<span class=""keyword-pill"">unexpected aid</span>
<span class=""keyword-pill"">survival</span>
<span class=""keyword-pill"">crisis</span>
<span class=""keyword-pill"">mystery</span>
<span class=""keyword-pill"">gratitude</span>
<span class=""keyword-pill"">transformation</span>
</div>
</div>
<div class=""separator""></div>
<img alt=""Symbolic image of a bright, fiery bird descending through darkness towards a lone figure, representing rescue and hope"" src=""https://image.pollinations.ai/prompt/Symbolic%20image%20of%20a%20bright%2C%20fiery%20bird%20descending%20through%20darkness%20towards%20a%20lone%20figure%2C%20representing%20rescue%20and%20hope""/>
<strong class=""named-individual"">Entity Overview:</strong>
<div class=""entity-grid"">
<div class=""entity-category"">
<h3 class=""entity-category-title"">NAMED INDIVIDUALS:</h3>
<p class=""entity-list""><em class=""no-entity"">None identified</em></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">ROLES &amp; CATEGORIES:</h3>
<p class=""entity-list""><span class=""roles-categories"">Survivor</span>, <span class=""roles-categories"">Rescuer</span>, <span class=""roles-categories"">Hot Bird</span> (Symbolic Entity), <span class=""roles-categories"">Hero</span></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">ORGANIZATIONS &amp; PRODUCTS:</h3>
<p class=""entity-list""><em class=""no-entity"">None identified</em></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">LOCATIONS:</h3>
<p class=""entity-list""><em class=""no-entity"">None identified</em></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">TIME PERIODS &amp; EVENTS:</h3>
<p class=""entity-list""><span class=""time-event"">Last Night</span>, <span class=""time-event"">Crisis</span>, <span class=""time-event"">Moment of Peril</span></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">ARTISTIC CONCEPTS &amp; DESIGN ELEMENTS:</h3>
<p class=""entity-list""><span class=""artistic"">Symbolism</span>, <span class=""artistic"">Metaphor</span></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">INDUSTRY TERMINOLOGY:</h3>
<p class=""entity-list""><em class=""no-entity"">None identified</em></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">FINANCIAL &amp; BUSINESS TERMS:</h3>
<p class=""entity-list""><em class=""no-entity"">None identified</em></p>
</div>
<div class=""entity-category"">
<h3 class=""entity-category-title"">KEY ACTIONS &amp; RELATIONSHIPS:</h3>
<p class=""entity-list""><span class=""key-actions"">Saved</span>, <span class=""key-actions"">Rescued</span>, <span class=""key-actions"">Survived</span>, <span class=""key-actions"">Intervened</span></p>
</div>
</div>
<div class=""divider""></div>
<strong class=""named-individual"">Summary:</strong>
<p class=""summary-intro""><span class=""key-sentence"">In the depths of an ordinary night, <span class=""time-event"">last night</span> to be precise, an extraordinary event unfolded, forever altering the course of one individual's existence: a life teetering on the brink was inexplicably <span class=""key-actions"">saved</span> by a mysterious entity cryptically referred to as a ""<span class=""roles-categories"">hot bird</span>.""</span> This stark, evocative statement hints at a profound <span class=""time-event"">crisis</span>, a <span class=""time-event"">moment of peril</span> so intense that survival seemed impossible, only for <span class=""key-actions"">salvation</span> to arrive from the most unexpected quarter. The ambiguity surrounding the ""hot bird"" – whether a literal creature imbued with intense energy, a metaphorical representation of fiery intervention, or even slang for an unforeseen human <span class=""roles-categories"">rescuer</span> – adds layers of intrigue to this dramatic narrative of survival.</p>
<p class=""supporting-point"">The narrative implicitly speaks to the universal experience of vulnerability and the suddenness with which life can veer into danger. <span class=""key-sentence"">Whatever the specific nature of the threat faced <span class=""time-event"">last night</span>, it was clearly perceived as lethal, a darkness closing in.</span> Perhaps it was a physical danger – an accident, an assault, a natural disaster – or maybe a moment of profound emotional or psychological despair where the will to live waned. The starkness of the declaration suggests a situation stripped bare of pretense, where the raw instinct to <span class=""key-actions"">survive</span> collided with overwhelming odds. Survival stories often highlight this thin veil between life and death, showing how quickly circumstances can shift, demanding resilience and often, a stroke of fortune or external intervention.</p>
<p class=""secondary-detail"">Many real-life <span class=""key-actions"">rescue</span> narratives involve <span class=""roles-categories"">unexpected heroes</span> stepping forth in moments of chaos. Ordinary individuals, like teachers performing first aid or cashiers thwarting robberies, suddenly find themselves acting with extraordinary courage. These accounts resonate because they reveal the potential for heroism within seemingly everyday people, demonstrating that bravery isn't confined to trained professionals but is a human capacity that can emerge under pressure. Similarly, stories abound of animals performing incredible rescues, from dogs alerting owners to danger to gorillas protecting fallen children. These tales underscore the deep bonds possible between species and the surprising ways help can manifest.</p>
<img alt=""Dramatic image of a person being pulled from a dangerous situation (e.g., water, fire) by an unseen force, emphasizing the rescue aspect"" src=""https://image.pollinations.ai/prompt/Dramatic%20image%20of%20a%20person%20being%20pulled%20from%20a%20dangerous%20situation%20%28e.g.%2C%20water%2C%20fire%29%20by%20an%20unseen%20force%2C%20emphasizing%20the%20rescue%20aspect""/>
<p class=""supporting-point"">Central to this event is the enigmatic <span class=""entity-spacing""><span class=""roles-categories"">hot bird</span></span>. <span class=""key-sentence"">This entity, regardless of its literal form, acted as the agent of <span class=""key-actions"">salvation</span>.</span> The descriptor ""hot"" could imply speed, intensity, brilliance, or even danger itself, paradoxically turned into aid. It might evoke the imagery of a <strong class=""artistic""><a href=""https://www.google.com/search?q=Phoenix+(mythology)"" target=""_blank"">phoenix</a></strong>, the mythical bird consumed by fire only to be reborn from its ashes, a powerful <span class=""artistic"">symbolism</span> of resurrection, renewal, and hope emerging from destruction. The <strong class=""artistic""><a href=""https://www.google.com/search?q=Phoenix+(mythology)"" target=""_blank"">phoenix</a></strong> represents overcoming adversity and the cyclical nature of life, suggesting that even from the ashes of despair, new beginnings are possible. This interpretation lends a layer of profound <span class=""artistic"">metaphor</span> to the event, framing the <span class=""key-actions"">rescue</span> not just as physical survival but potentially as a spiritual or psychological rebirth.</p>
<p class=""secondary-detail"">Bird <span class=""artistic"">symbolism</span> is rich across cultures and history. Eagles often represent divine power, vision, and regeneration, capable of gazing at the sun, much like Christ contemplating divine glory. Doves symbolize peace, hope, and the Holy Spirit, signifying reconciliation and new beginnings. Pelicans, believed to feed their young with their own blood, became symbols of Christ's sacrifice and atonement. Even hawks can represent <span class=""key-actions"">salvation</span> from bondage. The appearance of a bird, especially one described so intensely, carries deep symbolic weight, often seen as a messenger or omen, bridging the gap between the mundane and the divine, offering guidance or intervention.</p>
<p class=""supporting-point""><span class=""key-sentence"">The act of being <span class=""key-actions"">saved</span> represents a pivotal turning point, a moment where the trajectory towards demise was abruptly halted and reversed by the <span class=""key-actions"">intervened</span> action of the ""<span class=""roles-categories"">hot bird</span>.""</span> This intervention, whether swift and decisive or a sustained effort, fundamentally changed the outcome. It speaks to the power of external forces, sometimes mysterious and unexplained, to alter destiny. The experience likely left the <span class=""roles-categories"">survivor</span> grappling with a mix of shock, relief, and profound <span class=""key-actions"">gratitude</span>. Near-death experiences (NDEs), while distinct, often share this element of encountering an external force or presence that facilitates a return to life, frequently leading to significant personal <span class=""key-actions"">transformation</span>.</p>
<p class=""secondary-detail"">Research into NDEs reveals common themes: sensations of leaving the body, moving through a tunnel towards a brilliant light, feelings of overwhelming peace, life reviews, and encounters with deceased loved ones or spiritual beings. Crucially, individuals who undergo NDEs often report profound and lasting changes in their values and outlook. They typically become more compassionate, altruistic, spiritual, less materialistic, and develop a decreased fear of death. This transformative potential highlights how confronting mortality, even briefly, can reshape one's understanding of life and its purpose, emphasizing connection, love, and service.</p>
<p class=""transition-text"">The aftermath of such a profound event is rarely simple.</p>
<p class=""supporting-point""><span class=""key-sentence"">Beyond the immediate relief of survival, the experience described likely instills a deep sense of <span class=""key-actions"">gratitude</span> and perhaps a lingering sense of wonder or mystery about the nature of the <span class=""roles-categories"">rescuer</span>.</span> Gratitude, the appreciation for what one has received, is recognized psychologically as a powerful emotion linked to well-being. It fosters positivity, strengthens relationships, and can serve as a crucial <span class=""key-actions"">survival</span> skill during difficult times. By focusing on the good received, even in the face of hardship, <span class=""key-actions"">gratitude</span> helps individuals endure and find meaning. The declaration ""a <span class=""roles-categories"">hot bird</span> <span class=""key-actions"">saved</span> my life"" is, in itself, an expression of this profound thankfulness, acknowledging the debt owed to the mysterious savior.</p>
<p class=""secondary-detail""><span class=""key-sentence"">Cultivating <span class=""key-actions"">gratitude</span> involves conscious effort, such as keeping journals, reflecting on past hardships overcome, using visual reminders, or simply expressing thanks.</span> Psychologists note that practicing <span class=""key-actions"">gratitude</span> can reduce stress, improve sleep, strengthen immune systems, and decrease symptoms of depression. It shifts focus away from negative emotions like resentment and envy, promoting mental resilience. For <span class=""roles-categories"">survivors</span> of trauma or near-death situations, <span class=""key-actions"">gratitude</span> can be a complex but vital part of healing, helping to reframe the experience and find value even in the struggle.</p>
<p class=""supporting-point"">Ultimately, the statement ""Last night, a <span class=""roles-categories"">hot bird</span> <span class=""key-actions"">saved</span> my life"" encapsulates a narrative of dramatic intervention and unexpected <span class=""key-actions"">salvation</span>. <span class=""key-sentence"">It speaks to the fragility of life, the suddenness of <span class=""time-event"">crisis</span>, the possibility of rescue from unforeseen sources, and the enduring power of <span class=""key-actions"">gratitude</span> and <span class=""key-actions"">transformation</span> that often follows such life-altering events.</span> The mystery of the ""<span class=""roles-categories"">hot bird</span>"" serves as a potent <span class=""artistic"">metaphor</span> for the often inexplicable forces – whether internal resilience, external aid, or sheer luck – that allow individuals to <span class=""key-actions"">survive</span> against the odds, emerging perhaps scarred, but profoundly changed and thankful for the gift of life renewed.</p>
<div class=""gradient-divider""></div>
<strong class=""named-individual"">Interesting Facts:</strong>
<div class=""facts-container"">
<ul class=""facts-list"">
<li class=""fact-primary"">
<span class=""fact-bullet"">•</span> The mythical <strong class=""artistic""><a href=""https://www.google.com/search?q=Phoenix+(mythology)"" target=""_blank"">phoenix</a></strong> is said to live for hundreds of years (<span class=""number-numeric"">500</span> or more in some legends) before building a pyre of aromatic woods, igniting it, and being consumed in flames, only to rise anew from the ashes. This powerful <span class=""artistic"">symbolism</span> represents <span class=""key-actions"">rebirth</span>, <span class=""key-actions"">renewal</span>, and <span class=""key-actions"">immortality</span> across various cultures, including ancient <strong class=""location""><a href=""https://www.google.com/search?q=Egypt"" target=""_blank"">Egypt</a></strong> and <strong class=""location""><a href=""https://www.google.com/search?q=Greece"" target=""_blank"">Greece</a></strong>.
       </li>
<li class=""fact-secondary"">
<span class=""fact-bullet-secondary"">•</span> Near-death experiences (NDEs) often lead to profound personal <span class=""key-actions"">transformation</span>. Studies show individuals frequently report increased compassion, reduced fear of death, a greater appreciation for life, and a shift towards spiritual values after such an event, suggesting the experience can fundamentally alter one's perspective.
       </li>
<li class=""fact-primary"">
<span class=""fact-bullet"">•</span> <span class=""key-actions"">Survival</span> stories, both fictional like 'Robinson Crusoe' and real-life accounts like 'Adrift: Seventy-Six Days Lost at Sea', remain enduringly popular. They tap into primal themes of resilience, ingenuity, and the confrontation with mortality, allowing readers to vicariously experience extreme situations.
       </li>
<li class=""fact-secondary"">
<span class=""fact-bullet-secondary"">•</span> <span class=""key-actions"">Gratitude</span> is considered by some psychologists to be a key <span class=""key-actions"">survival</span> skill. Focusing on things to be thankful for, even small ones, can provide psychological sustenance during difficult times, helping individuals cope with stress and maintain hope.
       </li>
<li class=""fact-primary"">
<span class=""fact-bullet"">•</span> Animals are often documented as real-life <span class=""roles-categories"">heroes</span>. Stories include guide dogs leading owners from collapsing buildings, dolphins protecting swimmers from sharks, and even cats alerting families to fires or gas leaks, showcasing interspecies aid in <span class=""time-event"">crisis</span> moments.
       </li>
<li class=""fact-secondary"">
<span class=""fact-bullet-secondary"">•</span> In Christian <span class=""artistic"">symbolism</span>, different birds carry specific meanings related to <span class=""key-actions"">salvation</span> and divine attributes: the dove represents the Holy Spirit and peace, the eagle signifies Christ's divine nature and resurrection, and the pelican symbolizes atonement and self-sacrifice.
       </li>
<li class=""fact-primary"">
<span class=""fact-bullet"">•</span> The term ""<span class=""roles-categories"">hot bird</span>"" itself is ambiguous; while potentially symbolic, slang dictionaries sometimes list ""bird"" as referring to an aircraft or missile, or colloquially to an attractive woman, adding layers to potential interpretations of the <span class=""roles-categories"">rescuer</span>'s identity.
       </li>
<li class=""fact-secondary"">
<span class=""fact-bullet-secondary"">•</span> Research indicates that experiencing or expressing <span class=""key-actions"">gratitude</span> can activate specific brain regions, like the prefrontal cortex, potentially increasing sensitivity to future positive experiences and reinforcing prosocial behavior.
       </li>
<li class=""fact-conclusion"">
<span class=""fact-bullet"">•</span> Many dramatic rescues involve ordinary people becoming <span class=""roles-categories"">unexpected heroes</span>. From crowds catching a falling person at an amusement park to individuals pulling drivers from burning cars, moments of <span class=""time-event"">crisis</span> often reveal remarkable courage in everyday citizens.
       </li>
</ul>
</div>
<div class=""facts-divider""></div>
<strong class=""named-individual"">Sentiment Analysis:</strong>
<div class=""entity-sentiment"">
<h4 class=""entity-name"">Rescue Stories / Survival Narratives</h4>
<p class=""entity-sentiment-details"">
        Positive: <span class=""sentiment-positive"">92</span> | Negative: <span class=""sentiment-negative"">8</span>
</p>
<p class=""entity-summary"">Comments generally express admiration for the resilience and bravery shown in survival and rescue situations. Many find these stories inspiring and moving, highlighting human endurance and the kindness of strangers (heroes). Some negative comments arise from skepticism about specific details in dramatizations or frustration with poor retellings.</p>
<p class=""entity-keywords"">Key words/phrases: Inspiring, brave, heroic, incredible, resilience, moving, gripping, survival, hope, unbelievable, courage, dramatic.</p>
</div>
<div class=""entity-sentiment"">
<h4 class=""entity-name"">Unexpected Heroes</h4>
<p class=""entity-sentiment-details"">
        Positive: <span class=""sentiment-positive"">85</span> | Negative: <span class=""sentiment-negative"">5</span>
</p>
<p class=""entity-summary"">Public sentiment is overwhelmingly positive towards stories of ordinary people performing heroic acts. Commenters often praise their selflessness and quick thinking. Negative sentiment is rare but might question motives or criticize perceived failures in specific incidents.</p>
<p class=""entity-keywords"">Key words/phrases: Everyday hero, brave, selfless, quick thinking, amazing, inspiring, ordinary people, courage, saved the day.</p>
</div>
<div class=""entity-sentiment"">
<h4 class=""entity-name"">Near-Death Experiences (NDEs)</h4>
<p class=""entity-sentiment-details"">
        Positive: <span class=""sentiment-positive"">75</span> | Negative: <span class=""sentiment-negative"">25</span>
</p>
<p class=""entity-summary"">Comments reflect fascination and varying degrees of belief regarding NDEs. Many find the reported transformations inspiring and comforting evidence of an afterlife or deeper consciousness. Skepticism is also prevalent, with some attributing NDEs to neurological phenomena or hallucinations, leading to negative or dismissive comments.</p>
<p class=""entity-keywords"">Key words/phrases: Transformation, spiritual, afterlife, profound, life-changing, fascinating, skeptical, brain activity, hallucination, peace, light.</p>
</div>
<div class=""entity-sentiment"">
<h4 class=""entity-name"">Gratitude</h4>
<p class=""entity-sentiment-details"">
        Positive: <span class=""sentiment-positive"">98</span> | Negative: <span class=""sentiment-negative"">2</span>
</p>
<p class=""entity-summary"">Gratitude is almost universally viewed positively in comments. People share personal experiences of how gratitude helped them, affirm its psychological benefits, and encourage its practice. Minimal negativity exists, perhaps questioning its applicability in extreme suffering.</p>
<p class=""entity-keywords"">Key words/phrases: Thankful, appreciation, positive, well-being, mental health, perspective, important, powerful, helpful, practice.</p>
</div>
<img alt=""Abstract image representing transformation and gratitude, perhaps light emerging from darkness or hands clasped in thanks"" src=""https://image.pollinations.ai/prompt/Abstract%20image%20representing%20transformation%20and%20gratitude%2C%20perhaps%20light%20emerging%20from%20darkness%20or%20hands%20clasped%20in%20thanks""/>
<div class=""popularity-container"">
<h2 class=""popularity-title"">Popularity</h2>
<div class=""popularity-score"">
<div class=""popularity-number"">82</div>
<div class=""popularity-description"">Stories of survival, rescue, and unexpected heroism consistently attract high public interest and media coverage.</div>
</div>
</div>
<strong class=""named-individual"">More on topic and related terminology:</strong>
<div class=""more-on-topic-container"">
<ul class=""related-terminology-list"">
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Near-Death+Experience+research"" target=""_blank"">Near-Death Experience (NDE) Research</a> - <span class=""resource-description"">Explore scientific studies and personal accounts related to experiences reported by individuals close to death, often involving profound transformations.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Psychology+of+Gratitude"" target=""_blank"">Psychology of Gratitude</a> - <span class=""resource-description"">Learn about the mental and physical health benefits associated with practicing gratitude and how it impacts well-being and resilience.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Phoenix+Mythology+Symbolism"" target=""_blank"">Phoenix Mythology &amp; Symbolism</a> - <span class=""resource-description"">Discover the origins and meanings behind the mythical phoenix bird, a powerful symbol of rebirth, renewal, and overcoming adversity found in various cultures.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=True+Survival+Stories"" target=""_blank"">True Survival Stories</a> - <span class=""resource-description"">Read compelling real-life accounts of individuals who survived against incredible odds in extreme situations, showcasing human endurance.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Animal+Rescue+Heroes"" target=""_blank"">Animal Rescue Heroes</a> - <span class=""resource-description"">Find heartwarming stories about animals that have saved human lives or performed heroic acts, highlighting unexpected sources of help.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Unexpected+Heroism+Examples"" target=""_blank"">Unexpected Heroism Examples</a> - <span class=""resource-description"">Explore documented cases where ordinary people unexpectedly acted heroically during emergencies or crises.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Symbolism+of+Birds+in+Different+Cultures"" target=""_blank"">Symbolism of Birds in Different Cultures</a> - <span class=""resource-description"">Investigate the diverse meanings and roles assigned to birds in various mythologies, religions, and cultural traditions worldwide.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Meaning+of+Salvation+Stories"" target=""_blank"">Meaning of Salvation Stories</a> - <span class=""resource-description"">Examine narratives, often within religious contexts, that describe being saved from sin, despair, or physical danger, focusing on themes of redemption and new beginnings.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Trauma+and+Transformation"" target=""_blank"">Trauma and Transformation</a> - <span class=""resource-description"">Understand the psychological processes through which individuals can experience positive growth and transformation following traumatic events.</span>
</li>
<li class=""terminology-item"">
<a class=""resource-link"" href=""https://www.google.com/search?q=Emergency+Rescue+Procedures"" target=""_blank"">Emergency Rescue Procedures</a> - <span class=""resource-description"">Information on official rescue operations and techniques used by first responders in various emergency scenarios.</span>
</li>
</ul>
</div>
<div class=""more-topic-divider""></div>
</div>"						"2025-03-27 16:00:51.260032+01"	"2025-03-27 16:00:00+01"	"Miracle in the Night: How a Mysterious ""Hot Bird"" Became an Unlikely Savior"	"{""url"": ""How_to_Use_Up_Rotisserie_Chick_1.jpg"", ""alt"": ""RotisserieChicken"", ""caption"": ""RotisserieChicken""}"	"<p class=""summary-intro""><span class=""key-sentence"">In the depths of an ordinary night, <span class=""time-event"">last night</span> to be precise, an extraordinary event unfolded, forever altering the course of one individual's existence: a life teetering on the brink was inexplicably <span class=""key-actions"">saved</span> by a mysterious entity cryptically referred to as a ""<span class=""roles-categories"">hot bird</span>.""</span> This stark, evocative statement hints at a profound <span class=""time-event"">crisis</span>, a <span class=""time-event"">moment of peril</span> so intense that survival seemed impossible, only for <span class=""key-actions"">salvation</span> to arrive from the most unexpected quarter. The ambiguity surrounding the ""hot bird"" – whether a literal creature imbued with intense energy, a metaphorical representation of fiery intervention, or even slang for an unforeseen human <span class=""roles-categories"">rescuer</span> – adds layers of intrigue to this dramatic narrative of survival.</p>"	82	"Miracle_in_the_Night_How_a_Mysterious_Hot_Bird_Bec.html"


Featured image location is in:
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\static\images
Since category pages are located in :
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\categories
Store downsized images in :
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\categories\images
create that folder if it doesnt exists. 



Popularity score should be used to rank articles on the page:
- highest 1 article is presented like in CNN page:with largest image in top left position. 
- align articles by popularity score and place them simillar to CNN category page: articles with higher popularity score get placed higher. 
- only first 4 articles in category get their featured images displayed
- subcategories should be clearly marked with title and solid line below and below that with titles below of 4 top popular articles as in CNN.
And below that links on 10 others articles, sorted by relevance from that category...displayed in simillar way as on CNN category page. 


Generate layout for category page and store it in:
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\templates\category.html (needs to be created)
See example of article.html layout:

<!-- Add this at the beginning of your template for debugging -->
<!-- {% if fetched_images %}
<div style="background-color: #ffeeee; padding: 10px; border: 1px solid red; margin-bottom: 10px;">
    <p>Debug: Found {{ fetched_images|length }} fetched images</p>
    {% for img in fetched_images %}
        <p>Image {{ loop.index0 }}: {{ img.url }}</p>
    {% endfor %}
    <p>Relative static path: {{ relative_static_path }}</p>
</div>
{% else %}
<div style="background-color: #ffeeee; padding: 10px; border: 1px solid red; margin-bottom: 10px;">
    <p>Debug: No fetched images available</p>
</div>
{% endif %} -->

{% extends "base.html" %}

{% block title %}{{ title or "Fast News" }}{% endblock %}

{% block extra_css %}
    <link rel="stylesheet" href="{{ relative_static_path }}/css/article.css">
{% endblock %}

{% block content %}
<div class="article-container">
    <!-- Main Article Title -->
    <h1 class="article-title">{{ title }}</h1>
    
    <!-- Source Attribution -->
    {% if source_attribution %}
    <div class="source-attribution">
        {{ source_attribution|safe }}
    </div>
    {% endif %}
    
    <!-- Keywords Section -->
    {% if keywords %}
    <div class="keywords-container">
        <h3 class="keywords-heading">Keywords:</h3>
        <div class="keywords-tags">
          {% for keyword in keywords %}
             <span class="keyword-pill">{{ keyword }}</span>
          {% endfor %}
        </div>
    </div>
    {% endif %}

    <!-- Topic Popularity Score Section -->
    {% if topic_popularity and topic_popularity.number %}
    <div class="popularity-container">
        <h3 class="popularity-title">
            Popularity score: <span class="popularity-number">{{ topic_popularity.number }}</span>
        </h3>
        <div class="popularity-score">
            <div class="popularity-description">{{ topic_popularity.description }}</div>
        </div>
    </div>
    {% endif %}



    <!-- Entity Overview Section -->
    {% if entity_overview %}
    <div class="entity-overview">
        <strong class="entity-overview-heading">Entity Overview:</strong>
        <div class="entity-grid">
          {% for entity in entity_overview %}
            <div class="entity-category">
               <h3 class="entity-category-title">{{ entity.category }}</h3>
               <div class="entity-list">{{ entity.content|safe }}</div>
            </div>
          {% endfor %}
        </div>
    </div>
    {% endif %}



    <!-- Featured Image (placed after Entity Overview) -->
    {% if featured_image %}
    <div class="featured-image">
        <img src="{{ relative_static_path }}/images/{{ featured_image.url }}" alt="{{ featured_image.alt|default('Featured image') }}">
        {% if featured_image.caption %}
        <figcaption>{{ featured_image.caption }}</figcaption>
        {% endif %}
    </div>
    {% endif %}

    <!-- Debug: List classes of summary paragraphs -->
<!--     <div style="background-color: #eef; padding: 5px; margin-bottom: 10px; font-size: 12px;">
        <p>Classes: 
        {% for paragraph in summary_paragraphs %}
            {{ paragraph.class }}, 
        {% endfor %}
        </p>
    </div> -->

    <!-- Render summary paragraphs with images inserted at fixed positions -->
    <div class="summary">
        {% set supporting_point_count = namespace(value=0) %}
        {% for paragraph in summary_paragraphs %}
            <div class="{{ paragraph.class }}">{{ paragraph.content|safe }}</div>
            
            {% if paragraph.class == 'supporting-point' %}
                {% set supporting_point_count.value = supporting_point_count.value + 1 %}
                
                {# Insert the second image after the 2nd supporting-point #}
                {% if supporting_point_count.value == 2 and fetched_images and fetched_images|length > 1 %}
                    <div class="extra-image" style="margin: 20px 0; border: 1px solid #ddd; padding: 10px;">
                        <img src="{{ relative_static_path }}/images/{{ fetched_images[0].url }}" alt="{{ fetched_images[1].caption|default('Article image') }}" style="max-width:100%;">
                        {% if fetched_images[1].caption %}
                            <figcaption>{{ fetched_images[1].caption }}</figcaption>
                        {% endif %}
                    </div>
                {% endif %}
                
                {# Insert the third image after the 4th supporting-point #}
                {% if supporting_point_count.value == 4 and fetched_images and fetched_images|length > 2 %}
                <div class="extra-image" style="margin: 20px 0; border: 1px solid #ddd; padding: 10px;">
                    <img src="{{ relative_static_path }}/images/{{ fetched_images[1].url }}" alt="{{ fetched_images[2].caption|default('Article image') }}" style="max-width:100%;">
                    {% if fetched_images[2].caption %}
                        <figcaption>{{ fetched_images[2].caption }}</figcaption>
                    {% endif %}
                </div>
            {% endif %}
            
            {% endif %}
        {% endfor %}
    </div>

        <!-- Sentiment Analysis Section -->
        {% if sentiment_analysis %}
        <div class="sentiment-analysis">
            <strong class="summary-heading">Sentiment Analysis:</strong>
            {% for sentiment in sentiment_analysis %}
                <div class="entity-sentiment">
                    <h4 class="entity-name">{{ sentiment.entity }}</h4>
                    <p class="entity-sentiment-details">
                        Positive: <span class="sentiment-positive">{{ sentiment.positive }}</span> | Negative: <span class="sentiment-negative">{{ sentiment.negative }}</span>
                    </p>
                    <p class="entity-summary">Summary: {{ sentiment.summary }}</p>
                    <p class="entity-keywords">
                        Keywords: 
                        {% if sentiment.keywords %}
                            {% for keyword in sentiment.keywords %}
                                <span class="keyword">{{ keyword }}</span>{% if not loop.last %}, {% endif %}
                            {% endfor %}
                        {% else %}
                            None
                        {% endif %}
                    </p>
                </div>
            {% endfor %}
        </div>
        {% endif %}
    
    
    <!-- Interesting Facts Section -->
    {% if interesting_facts %}
    <div class="interesting-facts">
        <strong class="facts-heading">Interesting Facts:</strong>
        <div class="facts-container">
          <ul class="facts-list">
            {% for fact in interesting_facts %}
              <li class="{{ fact.class|join(' ') }}">{{ fact.content|safe|replace('<span class="fact-bullet">•</span>', '') }}</li>
            {% endfor %}
          </ul>
        </div>
    </div>
    {% endif %}


    <!-- More on topic and related terminology Section -->
    {% if related_resources %}
    <div class="more-on-topic">
        <strong class="more-on-topic-heading">More on topic and related terminology:</strong>
        <div class="more-on-topic-container">
            <ul class="related-terminology-list">
                {% for resource in related_resources %}
                <li class="terminology-item">
                    <a class="resource-link" href="{{ resource.url }}" target="_blank">{{ resource.title }}</a> - <span class="resource-description">{{ resource.description }}</span>
                </li>
                {% endfor %}
            </ul>
            <div class="more-topic-divider"></div>
        </div>
    </div>
    {% endif %}


        <!-- Related Articles Section -->
        {% if related_articles_list %}
        <div class="related-articles">
            <strong class="related-articles-heading">Related Articles:</strong>
            <ul class="related-articles-list">
                {% for article in related_articles_list %}
                <li class="related-article-item">
                    <a class="related-article-link" href="{{ article.link }}" target="_blank">{{ article.title }}</a>
                </li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}


    
    {# The "Original Article Content" section and its inline image have been removed #}
        <!-- Debug: Raw Gemini API Output -->
        {% if response_text %}
        <div style="background-color: #eeffee; padding: 10px; border: 1px solid green; margin-top: 10px;">
            <p>Debug: Raw Gemini API Output</p>
            <pre>{{ response_text|safe }}</pre>
        </div>
        {% endif %}
    
        <!-- Debug: Sentiment Analysis Data -->
<!--         {% if sentiment_analysis %}
        <div style="background-color: #ffffee; padding: 10px; border: 1px solid orange; margin-top: 10px;">
            <p>Debug: Sentiment Analysis Data</p>
            <pre>{{ sentiment_analysis|safe }}</pre >
        </div>
        {% else %}
        <div style="background-color: #ffffee; padding: 10px; border: 1px solid orange; margin-top: 10px;">
            <p>Debug: No Sentiment Analysis Data Available</p>
        </div>
        {% endif %} -->
    
</div>
{% endblock %}


Generate css of category page in:
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\static\css\category.css (it doesnt exists currently)

See example of article CSS:

/* Base typography and layout */
body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    color: #333;
    background-color: #fff;
    line-height: 1.6;
    margin: 0;
    padding: 0;
}

.article-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}

/* Article-specific styles */
.article-meta {
    color: #777;
    margin-bottom: 20px;
    font-size: 0.9em;
    padding-bottom: 15px;
    border-bottom: 1px solid #eee;
}

.summary {
    background-color: #f5f5f5;
    padding: 15px;
    border-radius: 5px;
    margin-bottom: 30px;
    border-left: 4px solid #0066cc;
}

.api-response {
    background-color: #eef;
    padding: 15px;
    border-radius: 5px;
    white-space: pre-wrap;
    overflow-x: auto;
    font-family: monospace;
    font-size: 0.9em;
    margin: 20px 0;
}

.article-content {
    border-top: 1px solid #ddd;
    margin-top: 30px;
    padding-top: 20px;
}

/* Headings */
.article-title {
    font-size: 1.5em;
    line-height: 1.3;
    margin-bottom: 0.7em;
    letter-spacing: 0.02em;
    position: relative;
    padding-bottom: 0.5em;
    border-bottom: 1px solid #f0f0f0;
}

/* Emphasis for key words */
.emphasis-keyword {
    border-bottom: 2px solid #f0f0f0;
    font-weight: 500;
}

/* Source Attribution */
.source-attribution {
    color: #555;
    font-style: italic;
    font-size: 0.9em;
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.6em;
}
.source-attribution .label {
    color: #777;
    font-weight: 500;
    letter-spacing: 0.02em;
    margin-right: 0.3em;
}

/* Keywords Section */
.keywords-container {
    background-color: #fafafa;
    border-radius: 4px;
    padding: 0.7em 1em;
    margin: 0.8em 0 1.2em 0;
}
.keywords-heading {
    margin: 0 0 0.4em 0;
    font-weight: bold;
    letter-spacing: 0.03em;
}
.keywords-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5em;
}
.keyword-pill {
    display: inline-block;
    background-color: #fff;
    border: 1px solid #eaeaea;
    border-radius: 50px;
    padding: 0.2em 0.8em;
    font-size: 0.9em;
}

/* Separators */
.separator {
    height: 1px;
    background-color: #f0f0f0;
    margin: 1.2em 0;
}
.divider {
    border: none;
    height: 1px;
    background-color: #eaeaea;
    margin: 1.2em 0;
}
.gradient-divider {
    height: 2px;
    border: none;
    background: linear-gradient(to right, #ffffff, #0066cc, #ffffff);
    margin: 1.5em 0;
}
.facts-divider {
    height: 2px;
    border: none;
    background: linear-gradient(to right, #ffffff, #e0e0e0, #ffffff);
    margin: 1.5em 0;
}

/* Entity Overview Section */
.entity-overview-heading {
    font-size: 1.15em;
    letter-spacing: 0.03em;
    margin-bottom: 0.8em;
    font-weight: bold;
}
.entity-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.8em;
    margin: 1em 0;
}
.entity-category {
    flex: 1;
    min-width: 275px;
    margin-bottom: 0.5em;
    background-color: #f9f9f9;
    border-radius: 4px;
    padding: 0.5em 0.8em;
}
.entity-category-title {
    margin: 0 0 0.3em 0;
    padding-bottom: 0.2em;
    border-bottom: 1px solid #eaeaea;
    font-size: 1em;
    font-weight: 500;
}
.entity-list {
    margin: 0;
    line-height: 1.5;
}
.no-entity {
    color: #999;
    font-style: italic;
}

/* Summary Creation Section */
.summary-heading {
    font-weight: bold;
    font-size: 1.15em;
    margin-bottom: 0.8em;
}
.summary-intro {
    font-size: 1.2em;
    line-height: 1.5;
    margin-bottom: 1.2em;
}
.key-sentence {
    letter-spacing: 0.03em;
    font-weight: 500;
}
.supporting-point {
    margin-bottom: 1em;
    padding-left: 0.8em;
    border-left: 3px solid #eeeeee;
}
.secondary-detail {
    font-size: 0.95em;
    line-height: 1.4;
    margin-bottom: 0.8em;
}
.crucial-fact {
    font-variant-numeric: tabular-nums;
    background-color: #f8f8f8;
    padding: 0px 3px;
    font-weight: 500;
}

/* Transition and Spacing */
.transition-text {
    font-size: 0.9em;
    font-style: italic;
    margin: 1em 0;
    color: #666;
}
.entity-spacing {
    letter-spacing: 0.05em;
}

/* Featured and supporting images */
.featured-image {
    text-align: center;
    margin: 1.5em 0;
}
.featured-image img {
    max-width: 100%;
    border-radius: 5px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}
.featured-image figcaption {
    font-size: 0.85em;
    color: #666;
    margin-top: 0.5em;
    font-style: italic;
    white-space: normal;
    overflow: visible;
}
.additional-images {
    display: flex;
    flex-wrap: wrap;
    gap: 1em;
    justify-content: center;
    margin: 1.5em 0;
}
.article-image {
    flex: 1;
    min-width: 200px;
    max-width: 300px;
    margin: 0;
}
.article-image img {
    width: 100%;
    border-radius: 5px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.article-image figcaption {
    font-size: 0.8em;
    color: #666;
    text-align: center;
    margin-top: 0.3em;
}
.left-image, .right-image {
    max-width: 40%;
    margin: 0.5em;
}
.left-image {
    float: left;
    margin-right: 1.5em;
}
.right-image {
    float: right;
    margin-left: 1.5em;
}
.image-caption {
    font-size: 0.8em;
    margin-top: 0.3em;
    color: #666;
    text-align: center;
}

/* Interesting Facts Section */
/* Modernized styling for Interesting Facts */
/* --- Interesting Facts Section --- */
/* --- Interesting Facts Section --- */
.interesting-facts {
    margin: 20px 0;
}

.facts-heading {
    font-size: 1.3em;
    font-weight: bold;
    margin-bottom: 10px;
    text-align: center;
    letter-spacing: 0.05em;
    color: #333;
}

.facts-container {
    /* Light background for overall container */
    background-color: #f7f7f7;
    padding: 20px;
    border-radius: 8px;
    margin: 20px 0;
    /* Remove or comment out if you prefer the container not to have a shadow */
    /* box-shadow: 0 2px 4px rgba(0,0,0,0.1); */
}

.facts-list {
    list-style: none; /* Remove default bullets */
    margin: 0;
    padding: 0;
}

/* Each fact styled as a “card” with a custom bullet dot */
.facts-list li {
    position: relative;
    background: #fff;
    border-radius: 6px;
    padding: 16px 20px 16px 50px; /* Extra left padding for the dot */
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    color: #555;
    line-height: 1.4;
}

/* Custom dot “bullet” */
.facts-list li::before {
    content: '';
    position: absolute;
    left: 20px;               /* Position the dot horizontally */
    top: 50%;                 /* Center vertically within the li */
    transform: translateY(-50%);
    width: 10px;             /* Dot size */
    height: 10px;
    border-radius: 50%;      /* Make it circular */
    background-color: #0066cc; /* Dot color */
}

/* Legend Section */
.legend-container {
    background-color: #f9f9f9;
    border-radius: 4px;
    padding: 0.8em;
    margin: 1.2em 0;
}
.legend-heading {
    font-size: 1.05em;
    letter-spacing: 0.02em;
    margin: 0 0 0.5em 0;
    font-weight: 500;
}
.legend-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6em;
}
.legend-item {
    flex: 1;
    min-width: 175px;
    background-color: #fff;
    padding: 0.5em;
    border-radius: 3px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    text-align: center;
}

/* Entity styling */
.named-individual {
    color: #0066cc;
    font-weight: bold;
}
.named-individual u {
    text-decoration-color: rgba(0, 102, 204, 0.4);
}
.roles-categories {
    color: #8a6d3b;
    font-weight: bold;
}
.orgs-products {
    color: #2e7d32;
    font-weight: bold;
}
.location {
    color: #56B4E9;
    font-weight: bold;
}
.time-event {
    color: #E69F00;
    font-weight: bold;
}
.artistic {
    color: #7b1fa2;
    font-weight: bold;
}
.industry {
    color: #00796b;
    font-weight: bold;
}
.financial {
    color: #666666;
    font-weight: bold;
}
.key-actions {
    color: #d32f2f;
    font-weight: bold;
}

/* Numeric formatting */
.date-numeric, .number-numeric {
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum";
    white-space: nowrap;
}
.date-numeric {
    color: #E69F00;
}
.number-numeric {
    font-weight: 500;
}

/* Footer */
.footer {
    margin-top: 30px;
    padding-top: 10px;
    border-top: 1px solid #ddd;
    font-size: 0.8em;
    color: #777;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .entity-category {
        min-width: 100%;
    }
    
    .left-image, .right-image {
        max-width: 100%;
        float: none;
        margin: 1em 0;
    }
    
    .summary-intro {
        font-size: 1.1em;
    }
}

/* Entity hover effects */
.entity-hoverable {
    position: relative;
    transition: all 0.2s ease;
}
.entity-hoverable:hover {
    background-color: rgba(0, 0, 0, 0.05);
    border-radius: 2px;
}
.entity-tooltip {
    position: absolute;
    top: -25px;
    left: 50%;
    transform: translateX(-50%);
    background-color: #333;
    color: white;
    padding: 3px 8px;
    border-radius: 3px;
    font-size: 0.7em;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s ease;
    z-index: 100;
}
.entity-hoverable:hover .entity-tooltip {
    opacity: 1;
}

/* Image zoom functionality */
.zoomable {
    cursor: zoom-in;
    transition: transform 0.2s;
}
.zoomable:hover {
    transform: scale(1.02);
}
.image-zoom-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.9);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}
.zoomed-image {
    max-width: 90%;
    max-height: 80%;
    object-fit: contain;
}
.zoomed-caption {
    color: white;
    margin-top: 10px;
    font-size: 0.9em;
    text-align: center;
    max-width: 80%;
}
.zoom-close-btn {
    position: absolute;
    top: 20px;
    right: 20px;
    color: white;
    background: transparent;
    border: none;
    font-size: 2em;
    cursor: pointer;
}

/* Collapsible sections */
.collapsible-heading {
    cursor: pointer;
    position: relative;
    padding-right: 25px;
}
.collapse-arrow {
    position: absolute;
    right: 0;
    top: 50%;
    transform: translateY(-50%);
    font-size: 0.8em;
    transition: transform 0.2s;
}
.collapsible-heading.collapsed .collapse-arrow {
    transform: translateY(-50%) rotate(-90deg);
}

/* Mobile responsive enhancements */
.table-responsive {
    width: 100%;
    overflow-x: auto;
}
.mobile-menu-button {
    display: none;
}

@media (max-width: 768px) {
    .mobile-menu-button {
        display: block;
        background: none;
        border: none;
        font-size: 1.5em;
        cursor: pointer;
    }
    .main-nav {
        display: none;
    }
    .main-nav.mobile-visible {
        display: block;
        position: absolute;
        top: 60px;
        left: 0;
        width: 100%;
        background: white;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .main-nav.mobile-visible ul {
        flex-direction: column;
    }
    .entity-grid {
        flex-direction: column;
    }
    .entity-category {
        width: 100%;
    }
}

/* Inline Image within Article Content */
.in-content-image {
    text-align: center;
    margin: 20px 0;
}
.in-content-image img {
    max-width: 100%;
    border-radius: 5px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}
.in-content-image figcaption {
    font-size: 0.85em;
    color: #666;
    margin-top: 0.5em;
    font-style: italic;
}

/* New additions for structured sections */
.entity-overview {
    margin: 20px 0;
}
.interesting-facts {
    margin: 20px 0;
}

/* (Other existing styles remain unchanged) */

/* Sentiment Analysis Styling */
.sentiment-analysis {
    margin: 20px 0;
    padding: 15px;
    background-color: #fff;
    border: 1px solid #eaeaea;
    border-radius: 5px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    display: flex;
    flex-wrap: wrap;
    gap: 0.8em;
}

/* Make the summary heading span the full width */
.sentiment-analysis .summary-heading {
    width: 100%;
    display: block;
    font-size: 1.2em;
    font-weight: bold;
    color: #0066cc;
    border-bottom: 2px solid #0066cc;
    padding-bottom: 8px;
    margin-bottom: 15px;
}

/* Style each sentiment block as a column */
.sentiment-analysis .entity-sentiment {
    flex: 1;
    min-width: 275px;
    padding: 10px;
    background-color: #f9f9f9;
    border: 1px solid #f0f0f0;
    border-radius: 4px;
    /* Remove any extra bottom border if present */
    border-bottom: none;
}

.entity-sentiment {
    padding: 10px 0;
    border-bottom: 1px solid #f0f0f0;
}

.entity-sentiment:last-child {
    border-bottom: none;
}

.entity-name {
    margin: 0;
    font-size: 1.1em;
    color: #333;
}

.entity-sentiment-details {
    margin: 5px 0;
    font-size: 0.95em;
    color: #555;
}

.sentiment-positive {
    color: #2e7d32;
    font-weight: bold;
}

.sentiment-negative {
    color: #d32f2f;
    font-weight: bold;
}

.entity-summary {
    margin: 10px 0;
    font-size: 0.95em;
    color: #444;
    background-color: #f9f9f9;
    padding: 10px;
    border-radius: 4px;
    border-left: 4px solid #0066cc;
}

.entity-keywords {
    margin: 5px 0;
    font-size: 0.9em;
    color: #666;
}

.keyword {
    display: inline-block;
    background-color: #e0e0e0;
    color: #333;
    border-radius: 3px;
    padding: 3px 7px;
    margin: 0 5px 5px 0;
    font-size: 0.85em;
}

figcaption {
    font-size: 0.85em;
    color: #666;
    margin-top: 0.5em;
    font-style: italic;
    white-space: normal;
    overflow: visible;
    text-align: center;
}

/* Center all image containers */
.in-content-image,
.article-image,
.extra-image,
.featured-image {
    text-align: center;
}

/* Center images by making them block-level with auto margins */
.in-content-image img,
.article-image img,
.extra-image img,
.featured-image img {
    display: block;
    margin: 0 auto;
}

/* Center all figcaptions */
figcaption {
    text-align: center;
}

.popularity-container {
    margin: 10px 0;
    padding: 10px;
    background-color: #f0f8ff;
    border: 1px solid #cce;
    border-radius: 4px;
    display: flex;
    flex-direction: column;
    gap: 5px;
}
.popularity-score {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap; /* Allow wrapping if the description is too long */
}
.popularity-number {
    font-size: 1.0em;
    font-weight: bold;
    color: #0066cc;
    flex: 0 0 auto; /* Keep the numeric element at its intrinsic size */
}
.popularity-description {
    font-size: 1em;
    color: #333;
    margin: 0;
    flex: 1 1 auto; /* Let the description take the remaining space */
    display: block; /* Ensure block-level for flex behavior */
}
.popularity-title {
    margin: 0 0 0 0;
    font-weight: bold;
    letter-spacing: 0.03em;
}


If you need anything else to do it or if you are missing something ask - do not assume, ask. 
We will create category python script in 
summarizer_category_generator.py

See example of 
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\nlp\summarizer\summarizer_html.py

# path: fast_news/news_aggregator/nlp/summarizer/summarizer_html.py
"""
Module for HTML processing and file operations for the article summarization system.
"""

import os
import re
import html
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup, Tag, NavigableString
from datetime import datetime

from summarizer_logging import get_logger
from summarizer_config import OUTPUT_HTML_DIR, ensure_output_directory
from summarizer_image import IMAGES_DIR, process_images_in_html, search_and_download_images
from summarizer_db import update_article_summary_details, get_related_articles

from db_scripts.db_context import DatabaseContext



from jinja2 import Environment, FileSystemLoader, select_autoescape

# Compute the base directory of your project (assumes summarizer_html.py is two levels deep in nlp/summarizer)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Define the template directory path relative to your project structure (note: no extra "web" folder)
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'templates')
IMAGES_DIR = os.path.join(BASE_DIR, 'frontend', 'web', 'static', 'images')


jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)
# Register custom filter "split" so the template can split strings
jinja_env.filters['split'] = lambda s, delimiter: s.split(delimiter) if s else []


# Define and register a static_url function for resolving static assets in templates
def static_url(path):
    return "../../static/" + path

jinja_env.globals['static_url'] = static_url

# Initialize logger
logger = get_logger(__name__)

def is_valid_html(text):
    """
    Check if the provided text is valid HTML.
    
    Args:
        text (str): The HTML text to validate
        
    Returns:
        bool: True if valid HTML, False otherwise
    """
    if not text or not isinstance(text, str):
        return False
    
    try:
        soup = BeautifulSoup(text, 'html.parser')
        return bool(soup.find())
    except Exception as e:
        logger.error(f"HTML validation error: {e}")
        return False
    
def get_subfolder_from_url(url):
    """
    Extracts subfolder(s) from the URL.
    Returns a relative path like "us/politics" or "briefing" based on URL segments.
    """
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        # Get non-empty path segments
        segments = [seg for seg in parsed.path.split('/') if seg]
        base_index = 0
        # Look for the date segments.
        # Standard pattern: [year, month, day, ...] or [lang, year, month, day, ...]
        if len(segments) >= 3 and segments[0].isdigit() and len(segments[0]) == 4 \
           and segments[1].isdigit() and len(segments[1]) == 2 \
           and segments[2].isdigit() and len(segments[2]) == 2:
            base_index = 3
        elif len(segments) >= 4 and segments[0].isalpha() \
             and segments[1].isdigit() and len(segments[1]) == 4 \
             and segments[2].isdigit() and len(segments[2]) == 2 \
             and segments[3].isdigit() and len(segments[3]) == 2:
            base_index = 4
        else:
            # If pattern doesn't match, return empty string
            return ""
        # Folder parts are those between the date and the final article slug
        folder_parts = segments[base_index:-1]
        if len(folder_parts) >= 2:
            # Only use the first two segments
            return os.path.join(folder_parts[0], folder_parts[1])
        elif len(folder_parts) == 1:
            return folder_parts[0]
        else:
            return ""
    except Exception as e:
        logger.error(f"Error extracting subfolder from URL: {e}")
        return ""

    

def ensure_proper_classes(soup):
    """
    Ensure that only approved classes are used and elements have appropriate classes.
    This is a validation step to catch any inconsistencies from the Gemini response.
    """
    allowed_classes = [
    # Article structure
    'article-title', 'emphasis-keyword', 'source-attribution', 'label',
    
    # Keywords section
    'keywords-container', 'keywords-heading', 'keywords-tags', 'keyword-pill',
    
    # Entity types
    'named-individual', 'roles-categories', 'orgs-products', 'location', 
    'time-event', 'artistic', 'industry', 'financial', 'key-actions',
    
    # Entity structure
    'entity-overview-heading', 'entity-grid', 'entity-category', 
    'entity-category-title', 'entity-list', 'no-entity',
    
    # Summary elements
    'summary-heading', 'summary-intro', 'key-sentence', 'supporting-point', 
    'transition-text', 'secondary-detail', 'crucial-fact',
    
    # Interesting facts
    'facts-heading', 'facts-container', 'facts-list', 'fact-primary', 
    'fact-secondary', 'fact-conclusion', 'fact-bullet', 'fact-bullet-secondary',
    
    # Legend
    'legend-container', 'legend-heading', 'legend-grid', 'legend-item',
    
    # Separators and misc elements
    'separator', 'divider', 'gradient-divider', 'facts-divider',
    'entity-spacing', 'transition-text', 'date-numeric', 'number-numeric',
    
    # Sentiment analysis classes
    'entity-sentiment', 'entity-name', 'entity-sentiment-details', 'sentiment-positive', 'sentiment-negative', 'entity-summary', 'entity-keywords',
    
    # Topic popularity score elements
    'popularity-container', 'popularity-title', 'popularity-score', 'popularity-number', 'popularity-description',

    # More on topic and related terminology section
    'more-on-topic-heading', 'more-on-topic-container', 'related-terminology-list', 'terminology-item', 'resource-link', 'resource-description', 'more-topic-divider'
    ]

    
    # Check for elements with classes not in the allowed list
    for element in soup.find_all(class_=True):
        element_classes = element.get('class', [])
        if isinstance(element_classes, str):
            element_classes = [element_classes]
        
        # Remove any classes not in the allowed list
        filtered_classes = [cls for cls in element_classes if cls in allowed_classes]
        if filtered_classes:
            element['class'] = filtered_classes
        else:
            # If all classes were invalid, remove the class attribute
            del element['class']
    
    # Element-specific class validation
    
    # Title validation
    for h1 in soup.find_all('h1'):
        if not h1.has_attr('class') or 'article-title' not in h1['class']:
            h1['class'] = ['article-title']
    
    # Source attribution validation
    for p in soup.find_all('p', class_='source-attribution'):
        for span in p.find_all('span'):
            if span.string and ('Source:' in span.string or 'Published:' in span.string):
                if not span.has_attr('class') or 'label' not in span['class']:
                    span['class'] = ['label']
    
    # Keywords container validation
    for div in soup.find_all('div', class_='keywords-container'):
        if not div.find('p', class_='keywords-heading'):
            heading = div.find('p')
            if heading:
                heading['class'] = ['keywords-heading']
                
        tags_container = div.find('div')
        if tags_container and (not tags_container.has_attr('class') or 'keywords-tags' not in tags_container['class']):
            tags_container['class'] = ['keywords-tags']
            
        for span in div.find_all('span'):
            if not span.has_attr('class') and span.parent.name == 'div' and span.parent.get('class') == ['keywords-tags']:
                span['class'] = ['keyword-pill']
    
    # Entity formatting validation
    entity_types = {
        'named-individual': ['strong'],
        'roles-categories': ['strong'],
        'orgs-products': ['strong'],
        'location': ['strong'],
        'time-event': ['strong'],
        'artistic': ['strong'],
        'industry': ['strong'],
        'financial': ['strong'],
        'key-actions': ['strong']
    }
    
    # Check entities have proper formatting
    for entity_class, tag_names in entity_types.items():
        for tag_name in tag_names:
            for tag in soup.find_all(tag_name):
                if tag.string and len(tag.string.strip()) > 0:
                    parent_classes = tag.get('class', [])
                    if not any(cls in parent_classes for cls in entity_types.keys()):
                        # Try to determine what entity type this might be
                        # This is a simplistic approach - you might need more sophisticated entity recognition
                        tag['class'] = [entity_class]
    
    # Ensure summary sections have proper classes
    summary_heading = soup.find('strong', string='Summary:')
    if summary_heading and not summary_heading.has_attr('class'):
        summary_heading['class'] = ['summary-heading']
    
    # Add validation for facts section if needed
    
    return soup

def clean_and_normalize_html(text):
    """
    Clean and normalize HTML content to ensure it's valid.

    Args:
        text (str): The HTML text to clean

    Returns:
        str: Cleaned and normalized HTML
    """
    logger.debug(f"Starting HTML normalization. Original length: {len(text) if text else 0}")

    if not text or not isinstance(text, str):
        logger.warning("Invalid input provided to clean_and_normalize_html.")
        return "<div>No content available</div>"

    try:
        # Extract HTML content from markdown-style code blocks if present
        if "```html" in text:
            try:
                text = text.split('```html')[1].split('```')[0].strip()
                logger.debug("HTML content successfully extracted from markdown code block.")
            except Exception as e:
                logger.warning(f"Failed extracting HTML from markdown block: {e}")

        # Remove markdown-style heading indicators
        text = re.sub(r'^#\s+', '', text, flags=re.MULTILINE)

        # Parse and clean the HTML content
        soup = BeautifulSoup(text, 'html.parser')

        # Remove inline styles
        for tag in soup.find_all(style=True):
            del tag['style']
            logger.debug(f"Removed inline styles from tag: {tag.name}")

        # Ensure correct class usage throughout HTML
        soup = ensure_proper_classes(soup)

        # Check if resulting HTML content is valid and non-empty
        if not soup.find() or not soup.text.strip():
            logger.warning("Resulting HTML is empty or invalid after cleaning.")
            return f"<div>{html.escape(text)}</div>"

        # Ensure HTML is wrapped in a single top-level div
        top_level_elements = [tag for tag in soup.children if isinstance(tag, (Tag, NavigableString))]

        if len(top_level_elements) != 1 or (top_level_elements[0].name != 'div'):
            wrapper_div = soup.new_tag("div")
            for element in top_level_elements:
                wrapper_div.append(element.extract())
            soup = BeautifulSoup(str(wrapper_div), 'html.parser')
            logger.debug("Wrapped HTML content within a single top-level div.")

        cleaned_html = str(soup)
        logger.debug(f"Cleaned HTML (preview 100 chars): {cleaned_html[:100]}...")

        return cleaned_html

    except Exception as e:
        logger.error(f"Exception occurred during HTML cleaning: {e}", exc_info=True)
        return f"<div>{html.escape(text)}</div>"

def extract_summary_fields(clean_html):
    """
    Extract structured fields from the cleaned summary HTML.
    
    Returns a dictionary with:
      - article_title: text from <h1 class="article-title">
      - source_attribution: HTML from <p class="source-attribution">
      - keywords: a list of strings from <span class="keyword-pill">
      - entity_overview: a list of dicts, each with 'category' and 'content' (from entity sections)
      - summary_paragraphs: a list of dicts for summary paragraphs (classes: summary-intro, supporting-point, transition-text, secondary-detail)
      - interesting_facts: a list of dicts for each fact (with its classes and content)
    """
    soup = BeautifulSoup(clean_html, 'html.parser')
    result = {}

    # Article Title
    title_tag = soup.find('h1', class_='article-title')
    result['article_title'] = title_tag.get_text(strip=True) if title_tag else ''

    # Source Attribution
    source_tag = soup.find('p', class_='source-attribution')
    result['source_attribution'] = str(source_tag) if source_tag else ''

    # Keywords
    keywords = []
    keywords_container = soup.find('div', class_='keywords-container')
    if keywords_container:
        for span in keywords_container.find_all('span', class_='keyword-pill'):
            keywords.append(span.get_text(strip=True))
    result['keywords'] = keywords

    # Entity Overview
    entity_overview = []
    entity_grid = soup.find('div', class_='entity-grid')
    if entity_grid:
        for category in entity_grid.find_all('div', class_='entity-category'):
            category_title_tag = category.find(class_='entity-category-title')
            category_title = category_title_tag.get_text(strip=True) if category_title_tag else ''
            entity_list_tag = category.find('p', class_='entity-list')
            entity_list = str(entity_list_tag) if entity_list_tag else ''
            entity_overview.append({'category': category_title, 'content': entity_list})
    result['entity_overview'] = entity_overview

    # Summary Paragraphs
    summary_paragraphs = []
    for class_name in ['summary-intro', 'supporting-point', 'transition-text', 'secondary-detail']:
        for p in soup.find_all('p', class_=class_name):
            summary_paragraphs.append({'class': class_name, 'content': str(p)})
    result['summary_paragraphs'] = summary_paragraphs

    # Interesting Facts
    facts = []
    facts_container = soup.find('div', class_='facts-container')
    if facts_container:
        for li in facts_container.find_all('li'):
            fact_class = li.get('class', [])
            # Using decode_contents to get inner HTML without the outer <li> tag
            facts.append({'class': fact_class, 'content': li.decode_contents()})
    result['interesting_facts'] = facts
    
    # More on topic and related terminology extraction
    related_resources = []
    more_topic_container = soup.find('div', class_='more-on-topic-container')
    if more_topic_container:
        ul = more_topic_container.find('ul', class_='related-terminology-list')
        if ul:
            for li in ul.find_all('li', class_='terminology-item'):
                resource = {}
                a_tag = li.find('a', class_='resource-link')
                if a_tag:
                    resource['title'] = a_tag.get_text(strip=True)
                    resource['url'] = a_tag.get('href', '')
                span_desc = li.find('span', class_='resource-description')
                if span_desc:
                    resource['description'] = span_desc.get_text(strip=True)
                if resource:
                    related_resources.append(resource)
    result['related_resources'] = related_resources
    
    # Topic Popularity Score Extraction
    topic_popularity = {}
    popularity_container = soup.find('div', class_='popularity-container')
    if popularity_container:
        popularity_number = popularity_container.find(class_='popularity-number')
        popularity_description = popularity_container.find(class_='popularity-description')
        topic_popularity['number'] = popularity_number.get_text(strip=True) if popularity_number else ''
        topic_popularity['description'] = popularity_description.get_text(strip=True) if popularity_description else ''
    result['topic_popularity'] = topic_popularity
    
    # Sentiment Analysis Extraction (updated)
    sentiment_data = []
    for div in soup.find_all('div', class_='entity-sentiment'):
        # Get entity name
        entity_name_tag = div.find('h4', class_='entity-name')
        entity_name = entity_name_tag.get_text(strip=True) if entity_name_tag else ''
        
        # Get positive/negative counts
        sentiment_details_tag = div.find('p', class_='entity-sentiment-details')
        positive = ''
        negative = ''
        if sentiment_details_tag:
            positive_tag = sentiment_details_tag.find('span', class_='sentiment-positive')
            negative_tag = sentiment_details_tag.find('span', class_='sentiment-negative')
            positive = positive_tag.get_text(strip=True) if positive_tag else ''
            negative = negative_tag.get_text(strip=True) if negative_tag else ''
        
        # Extract additional sentiment info
        entity_summary_tag = div.find('p', class_='entity-summary')
        entity_summary = entity_summary_tag.get_text(strip=True) if entity_summary_tag else ''
        
        # Extract keywords properly as a list
        entity_keywords = []
        entity_keywords_tag = div.find('p', class_='entity-keywords')
        if entity_keywords_tag:
            keywords_text = entity_keywords_tag.get_text(separator=' ', strip=True)
            # Remove common prefixes if they exist
            for prefix in ["Keywords:", "Key words/phrases:"]:
                if keywords_text.lower().startswith(prefix.lower()):
                    keywords_text = keywords_text[len(prefix):].strip()
            # Split the string into a list by comma and trim each keyword
            entity_keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]

        
        sentiment_data.append({
            'entity': entity_name,
            'positive': positive,
            'negative': negative,
            'summary': entity_summary,
            'keywords': entity_keywords
        })
        result['sentiment_analysis'] = sentiment_data

    return result

def create_filename_from_title(title, url, article_id):
    """
    Create a valid filename from the article title.
    
    Args:
        title (str): The article title
        url (str): The article URL (fallback if title is empty)
        article_id (str): The article ID (fallback if title and URL are empty)
        
    Returns:
        str: A valid filename
    """
    # Handle empty title
    if not title or title.strip() == '':
        if url:
            # Extract last part of URL
            url_parts = url.strip('/').split('/')
            return f"{url_parts[-1][:50]}.html"
        else:
            # Use article ID
            return f"article_{article_id}.html"
    
    # Clean title and create filename
    filename = re.sub(r'[^\w\s-]', '', title)  # Remove non-alphanumeric chars
    filename = re.sub(r'\s+', '_', filename)    # Replace spaces with underscores
    filename = filename[:50]                    # Limit length
    return f"{filename}.html"

def save_as_html(article_id, title, url, content, summary, response_text, schema, keywords=None, existing_gemini_title=None):

    """
    Save the article and its summary as an HTML file, with images from Wikimedia based on keywords.
    
    Args:
        article_id (str): The article ID
        title (str): The article title
        url (str): The article URL
        content (str): The original article content
        summary (str): The generated summary
        response_text (str): The raw API response
        keywords (list, optional): List of article keywords for Wikimedia image searches
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure output directory exists
        ensure_output_directory()
        
        # Debug the raw summary and response
        logger.debug(f"Raw summary type: {type(summary)}")
        logger.debug(f"Raw summary preview: {summary[:300] if summary else 'None'}")
        
        # Process featured image extraction first
        featured_image_html = ""
        processed_summary = summary        
                              
        # Extract HTML content properly
        clean_summary = ""
        if processed_summary and isinstance(processed_summary, str):
            # Check if summary contains code blocks
            if "```html" in processed_summary:
                try:
                    processed_summary = processed_summary.split("```html")[1].split("```")[0].strip()
                    processed_summary = html.unescape(processed_summary)
                    logger.debug("Extracted and unescaped HTML from code block")
                except Exception as e:
                    logger.warning(f"Error extracting HTML from code block: {e}")

            # Remove any stray style-based list item formatting
            processed_summary = re.sub(r'<li style="[^>]*">', '<li>', processed_summary)
            
            # Clean and normalize the HTML content
            clean_summary = clean_and_normalize_html(processed_summary)
        else:
            logger.warning(f"Invalid summary content: {type(processed_summary)}")
            clean_summary = "<div>No valid summary content available</div>"
        
        # Attempt to extract Gemini-generated title from the cleaned summary HTML.
        # If an existing Gemini title is provided (from a prior summary), use it.
        soup_summary = BeautifulSoup(clean_summary, 'html.parser')
        gemini_title_tag = soup_summary.find('h1', class_='article-title')
        generated_title = gemini_title_tag.get_text(separator=' ', strip=True) if gemini_title_tag else title
        gemini_title = existing_gemini_title if existing_gemini_title is not None else generated_title

        if existing_gemini_title is not None:
            logger.info(f"Existing Gemini title found in DB for article {article_id}: '{existing_gemini_title}'. Title unchanged.")
        else:
            logger.info(f"New Gemini title generated for article {article_id}: '{generated_title}'.")


        
        # If clean_summary is empty or just a placeholder, try with the API response
        if not clean_summary or clean_summary in ("<div>No content available</div>", "<div>No valid summary content available</div>"):
            logger.warning("Processed summary is empty, attempting to extract from raw API response")
            try:
                if response_text and "```html" in response_text:
                    html_content = response_text.split("```html")[1].split("```")[0].strip()
                    html_content = html.unescape(html_content)
                    if html_content:
                        clean_summary = clean_and_normalize_html(html_content)
                        logger.info("Successfully extracted HTML content from API response")
                elif response_text and ("<html" in response_text or "<div" in response_text):
                    html_match = re.search(r'(<div.*?>.*?</div>|<html.*?>.*?</html>)', response_text, re.DOTALL)
                    if html_match:
                        html_content = html_match.group(0)
                        clean_summary = clean_and_normalize_html(html_content)
                        logger.info("Successfully extracted HTML content from API response using regex")
            except Exception as e:
                logger.error(f"Error extracting HTML from API response: {e}")
        
        # If we still don't have a featured image, try to get one from Wikimedia
        if not featured_image_html and ((keywords and isinstance(keywords, list) and len(keywords) > 0) or (title and title.strip() != "")):
            base_name = re.sub(r'[^\w\s-]', '', title if title else "Article")
            base_name = re.sub(r'\s+', '_', base_name)[:30]  # Limit length
            
            core_org_entities = []
            core_named_entities = []
            core_key_actions_entities = []
            core_industry_terminology = []
            soup_entities = BeautifulSoup(clean_summary, 'html.parser')
            entity_grid = soup_entities.find('div', class_='entity-grid')
            if entity_grid:
                for category in entity_grid.find_all('div', class_='entity-category'):
                    cat_title_tag = category.find(class_='entity-category-title')
                    cat_title = cat_title_tag.get_text(strip=True).upper() if cat_title_tag else ""
                    entity_list_tag = category.find('p', class_='entity-list')
                    if entity_list_tag:
                        entities_text = entity_list_tag.get_text(separator=',').strip()
                        entities = [e.strip() for e in entities_text.split(',') if e.strip()]
                        if cat_title.startswith("ORGANIZATIONS & PRODUCTS"):
                            core_org_entities.extend(entities)
                        elif cat_title.startswith("NAMED INDIVIDUALS"):
                            core_named_entities.extend(entities)
                        elif cat_title.startswith("KEY ACTIONS & RELATIONSHIPS"):
                            core_key_actions_entities.extend(entities)
                        elif cat_title.startswith("INDUSTRY TERMINOLOGY"):
                            core_industry_terminology.extend(entities)
            # Remove duplicates while preserving order
            core_org_entities = list(dict.fromkeys(core_org_entities))
            core_named_entities = list(dict.fromkeys(core_named_entities))
            core_key_actions_entities = list(dict.fromkeys(core_key_actions_entities))
            core_industry_terminology = list(dict.fromkeys(core_industry_terminology))
            
            # Combine ORGANIZATIONS & PRODUCTS with KEY ACTIONS & RELATIONSHIPS for more contextual results
            combined_org_key = list(dict.fromkeys(core_org_entities + core_key_actions_entities))
            
            # Build candidate list in a round-robin fashion using combined_org_key, NAMED INDIVIDUALS, and INDUSTRY TERMINOLOGY
            candidates = []
            index = 0
            while True:
                added = False
                if index < len(combined_org_key):
                    candidates.append(combined_org_key[index])
                    added = True
                if index < len(core_named_entities):
                    candidates.append(core_named_entities[index])
                    added = True
                if index < len(core_industry_terminology):
                    candidates.append(core_industry_terminology[index])
                    added = True
                if not added:
                    break
                index += 1

            # Prioritize candidates that appear in the original article title
            article_title_lower = title.lower()
            prioritized_candidates = []
            non_prioritized_candidates = []
            for candidate in candidates:
                if candidate.lower() in article_title_lower:
                    prioritized_candidates.append(candidate)
                else:
                    non_prioritized_candidates.append(candidate)
            candidates = prioritized_candidates + non_prioritized_candidates           
            
            
            

            if not candidates and title:
                title_words = [word.lower() for word in re.findall(r'\b\w+\b', title)
                               if len(word) > 3 and word.lower() not in ['the', 'and', 'with', 'from', 'that', 'this']]
                candidates = title_words[:6]

            image_query = " ".join(candidates)
            logger.debug(f"Entities for Wikimedia image search: {candidates}")                    
                    
            
            if image_query:
                logger.info("Using Wikimedia search query based on the original title for image search.")
                
                from summarizer_config import CONFIG, get_config_value
                short_threshold = get_config_value(CONFIG, 'image_search', 'short_threshold', 3000)
                medium_threshold = get_config_value(CONFIG, 'image_search', 'medium_threshold', 7000)
                max_images = get_config_value(CONFIG, 'image_search', 'max_images', 3)
                
                content_length = len(content) if content else 0
                if content_length < short_threshold:
                    num_images = 2
                elif content_length < medium_threshold:
                    num_images = 3
                else:
                    num_images = max_images
                
                images = search_and_download_images("", article_id, base_name, num_images, title=title)               
                
                
                
                logger.info(f"Found {len(images)} images for article {article_id}")
                
                if images and len(images) > 0:
                    featured_image = images[0]
                    featured_image_url = featured_image["url"].replace("\\", "/")
                    featured_image_html = (
                        f'<div class="featured-image">'
                        f'<img src="{featured_image_url}" alt="{featured_image["caption"]}">'
                        f'<figcaption>{featured_image["caption"]}</figcaption>'
                        f'</div>'
                    )
                    logger.info(f"Featured image added to HTML: {featured_image_url}")
                else:
                    featured_image_html = ""
                    logger.warning("No featured image available to add to HTML.")
                    
        
        # Process any images in the summary, downloading them and updating src attributes
        if clean_summary and "<img" in clean_summary:
            clean_summary = process_images_in_html(clean_summary, article_id)
        
        # Create filename and filepath
        filename = create_filename_from_title(gemini_title, url, article_id)

        # Determine subfolder(s) based on URL
        subfolder = get_subfolder_from_url(url)
        if subfolder:
            target_dir = os.path.join(OUTPUT_HTML_DIR, subfolder)
            os.makedirs(target_dir, exist_ok=True)
        else:
            target_dir = OUTPUT_HTML_DIR

        filepath = os.path.join(target_dir, filename)
        logger.debug(f"Preparing to save HTML to: {filepath}")

        # Compute relative path for static assets based on the depth of the target directory.
        # Base case: when file is in OUTPUT_HTML_DIR, relative path is "../../static".
        # For each additional subfolder level, add one "../".
        depth = subfolder.count(os.sep) + 1 if subfolder else 0
        relative_static_path = "../" * (1 + depth) + "static"

        # Determine the correct relative path for static assets
        
        # Create processed date and current year for footer
        processed_date = datetime.now().strftime("%B %d, %Y %H:%M")
        current_year = datetime.now().year
        
        # Prepare featured image and fetched images context
        # Instead of using the first image exclusively as featured_image,
        # pass all images to fetched_images_data.
        if images and len(images) > 0:
            featured_image_data = {
                "url": os.path.basename(images[0]["url"]),
                "alt": images[0].get("caption", "Article image"),
                "caption": images[0].get("caption", "")
            }
            fetched_images_data = [{
                "url": os.path.basename(img["url"]),
                "alt": img.get("caption", "Article image"),
                "caption": img.get("caption", "")
            } for img in images[1:]]
        else:
            featured_image_data = None
            fetched_images_data = []
            
        # After clean_summary has been computed
        summary_fields = extract_summary_fields(clean_summary)

        # Compute relative file location for the saved HTML file
        if subfolder:
            relative_file_location = os.path.join(subfolder, filename)
        else:
            relative_file_location = filename


        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext()
        keywords = summary_fields.get("keywords", [])
        if keywords:
            related_articles_list = get_related_articles(db_context, schema, article_id, keywords, limit=5)
        else:
            related_articles_list = []

                
        context = {
            "title": gemini_title or f"Article {article_id}",
            "article_id": article_id,
            "url": url,
            "processed_date": processed_date,
            "featured_image": featured_image_data,
            "summary": clean_summary if clean_summary else "<div>No summary available</div>",
            "fetched_images": fetched_images_data,
            "show_api_response": True,
            "response_text": response_text,
            "content": content,
            "relative_static_path": relative_static_path,
            "current_year": current_year,
            "source_attribution": summary_fields.get("source_attribution", ""),
            "keywords": summary_fields.get("keywords", []),
            "entity_overview": summary_fields.get("entity_overview", []),
            "summary_paragraphs": summary_fields.get("summary_paragraphs", []),
            "interesting_facts": summary_fields.get("interesting_facts", []),
            "related_resources": summary_fields.get("related_resources", []),
            "sentiment_analysis": summary_fields.get("sentiment_analysis", []),
            "topic_popularity": summary_fields.get("topic_popularity", {}),
            "popularity_score": int(summary_fields.get("topic_popularity", {}).get("number", "0") or 0),
            "related_articles_list": related_articles_list,
            "schema": schema,
            "article_html_file_location": relative_file_location
        }

        
        # Load the article template from the Jinja2 environment
        template = jinja_env.get_template('article.html')
        
        # Render the final HTML using the template and the provided context
        html_content = template.render(context)
        
        # Write the rendered HTML to the output file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
            f.flush()
        
        if os.path.exists(filepath):
            logger.info(f"HTML file created successfully: {filepath} (Size: {os.path.getsize(filepath)} bytes)")
        else:
            logger.error(f"Failed to create HTML file: {filepath}")
        
        if featured_image_html:
            if featured_image_url in html_content:
                logger.debug(f"Confirmed featured image path '{featured_image_url}' is correctly embedded in HTML.")
            else:
                logger.error(f"Featured image path '{featured_image_url}' is missing in generated HTML.")
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logger.info(f"Successfully saved HTML output to {filepath} (size: {file_size} bytes)")
            # Update additional summary fields in the database.
            schema = context.get("schema", "pt_nyt")
            update_success = update_article_summary_details(db_context, schema, article_id, context)
            if update_success:
                logger.info("Database summary details updated successfully.")
            else:
                logger.error("Failed to update database summary details.")
            return True
        else:
            logger.error(f"File wasn't created despite no errors: {filepath}")
            return False
    except Exception as e:
        logger.error(f"Error saving HTML file {filepath if 'filepath' in locals() else 'unknown'}", exc_info=True)
        return False


That is generating article html based on gemini output - you need to use simillar shared modules (like for db communication as in this script)

Make sure you also use other common features like:
# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

logger = get_logger(__name__)

Log extensivelly everything and keep whole thing in DEBUG while in developement. 

____________________
Plan of action:

First define if anything is missing for you to start working, as said, do not assume, ask. 
then define table of content - list of actions of how we are going to approach this.
than we will go one by one item in table of content - do not cover multiple code blocks or files at once - only one, only one , remember that!!
Ask for confirmation.
Work in small iterable units of work that can be easily tests - for example lets create first just small category page just with links on articles so we know that that works - than we can move on and add more stuff to layout. 
After I confirm some step worked, than and only than we can move to another piece of code. 

Answers to your questions:
__________________________


Before diving into the implementation, I’d like to clarify a few points and propose a plan of action. Could you please confirm or clarify the following details?

### Clarifications Needed
1. **Environment & File Structure**  
   - **Category HTML Pages:** Should be stored in  
     `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\categories`  
   - **Article HTML Pages:** Remain in  
     `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\articles`  
   - **Static Images:** Are located in  
     `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\static\images`  - yes but they are static images of articles

   - **Downsized Images for Category Pages:** Should be stored in  
     `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\categories\images` (create this folder if it doesn’t exist)  
   Is this correct?

   YES. 

2. **Layout Requirements**  
   - The category page layout should mimic a CNN-like category page where:
     - **Top Article:** The highest popularity article is displayed with a large featured image in the top left.
     - **Next 3 Articles:** Also display their featured images (only the first 4 articles get images).
     - **Subcategories:** They should be clearly marked with a title and a solid line below, and then below that, display titles for the top 4 popular articles.
     - **Additional Articles:** Then, display links to 10 other articles sorted by relevance.
     
   Could you please confirm if “subcategories” are derived from a field in the database or if they are predetermined? 
   They are derived from path to articles, some articles are stored in top categories like:
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\articles\business
and some are stored in category/subcategory:
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\articles\arts\television
so derive subcategory from 
article_html_file_location

   Also, is the relevance ranking derived solely from the popularity score or another criterion? solely from the popularity.

3. **Data Source**  
   - We will use the provided **articles table** with fields such as:
     - `summary_generated_at`
     - `summary_article_gemini_title`
     - `summary_featured_image`
     - `popularity_score`
     - `article_html_file_location`
     
   Do you have a separate categories table, or should we filter articles based on the `category_id` field?
   Yes, we have:
   CREATE TABLE IF NOT EXISTS pt_nyt.categories
(
    category_id uuid NOT NULL DEFAULT gen_random_uuid(),
    name character varying(255) COLLATE pg_catalog."default" NOT NULL,
    slug character varying(255) COLLATE pg_catalog."default" NOT NULL,
    portal_id uuid NOT NULL,
    path text COLLATE pg_catalog."default" NOT NULL,
    level integer NOT NULL,
    description text COLLATE pg_catalog."default",
    link text COLLATE pg_catalog."default",
    atom_link text COLLATE pg_catalog."default",
    is_active boolean DEFAULT true,
    CONSTRAINT categories_pkey PRIMARY KEY (category_id),
    CONSTRAINT uq_pt_nyt_categories_slug_portal_id UNIQUE (slug, portal_id)
)


so you can use it to filter articles based on the `category_id`  

Also make sure you use model.py just like its used in :
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\nlp\summarizer\summarizer_html.py
You need to use I guess both  models - category and article model. 


4. **Image Processing**  
   - The featured image for each article should be downsized to **300x200** (cropped from the image center) and stored in the designated category images folder.  
   Do you have an existing image processing function for this, or should we build one (possibly leveraging Pillow or a similar library)?
   We should build sepaarate functions. all new functions should be put in if appropriate:
   C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\nlp\summarizer\summarizer_category_utilities.py

5. **Python Script: `summarizer_category_generator.py`**  
   - We need to create a new Python script that uses similar shared modules (logging, DB communication, Jinja2 templating, etc.) as in `summarizer_html.py`.
   - It should query the database for articles in a given category, process images, generate the category HTML page, and log extensively at the DEBUG level.
   
   Is that correct? YES,

6. **CSS File for Category Page**  
   - We will create a new CSS file at  
     `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\static\css\category.css`  
     similar in style to the provided article CSS.
     
   Any additional styling requirements for the category layout? NO. 

7. **Incremental Development Approach**  
   - We’ll start with a basic version: a minimal category page that lists article links from the specified category.
   - After your confirmation, we can iteratively add:
     - Featured images for the top articles.
     - Subcategory sections.
     - The detailed CNN-like layout.
     
   Does that work for you? YES. 


   -------------------------- final clarification ---------------

Below is a summary of the clarifications and a proposed plan of action. Please review and confirm if this meets your expectations before we start working on any code.

---

### Clarifications Confirmed

1. **File Structure & Storage**  
   - **Category HTML Pages:**  
     Stored in  
     `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\categories`
   - **Article HTML Pages:**  
     Remain in  
     `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\articles`
   - **Static Images (of articles):**  
     Located in  
     `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\static\images`
   - **Downsized Images for Category Pages:**  
     Stored in  
     `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\categories\images`  
     (This folder should be created if it does not exist.)

2. **Layout Requirements**  
   - **Top Article:**  
     The highest popularity article is displayed with a large featured image (positioned top left).
   - **Next 3 Articles:**  
     Display their featured images (only the first 4 articles in the category get images).
   - **Subcategories:**  
     These are derived from the `article_html_file_location` path.  
     For example, articles in `.../articles/business` are top categories, while those in `.../articles/arts/television` indicate a subcategory.
   - **Additional Articles:**  
     Below the main featured and subcategory sections, display links to 10 other articles sorted by popularity (relevance is solely based on the popularity score).

3. **Data Source**  
   - We'll use the provided **articles table** (with fields such as `summary_generated_at`, `summary_article_gemini_title`, `summary_featured_image`, `popularity_score`, `article_html_file_location`, etc.).
   - We also have the **categories table** to filter articles based on `category_id`.
   - The new code should integrate with the existing models (similar to how it's used in `summarizer_html.py`).

4. **Image Processing**  
   - A new function will be developed to crop and downsize images to **300x200** (cropped from the image center).
   - This function will be added to a new module:  
     `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\nlp\summarizer\summarizer_category_utilities.py`

5. **Python Script: `summarizer_category_generator.py`**  
   - We will create a new script that uses similar shared modules (logging, database communication, Jinja2 templating, etc.) as in `summarizer_html.py`.
   - This script will query the database for articles in a given category, process images as needed, generate the category HTML page, and log extensively at the DEBUG level.

6. **CSS for Category Page**  
   - A new CSS file will be created at:  
     `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\static\css\category.css`  
     It should have styling similar to the provided article CSS, adjusted for the CNN-like layout.

7. **Incremental Development Approach**  
   - We'll start with a minimal category page that only lists article links for a given category.
   - Once that works, we will gradually add:
     - Featured images for the top articles.
     - Subcategory sections.
     - The detailed CNN-like layout for the remaining articles.

---

### Proposed Table of Contents (Plan of Action)

1. **Setup & Verification**
   - Verify the file structure and create the `categories\images` folder if it does not exist.

2. **Minimal Category Template**
   - **File:** `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\templates\category.html`
   - Create a basic template that lists article links from a given category.

3. **Minimal CSS for Category Page**
   - **File:** `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\static\css\category.css`
   - Develop basic CSS styling similar to the article CSS.

4. **Database Query & Model Integration**
   - Integrate with the models (both category and article) to query articles for a given category (using `category_id`).
   - Ensure filtering and sorting (based solely on the popularity score).

5. **Basic Category Page Generation Script**
   - **File:** `summarizer_category_generator.py`
   - Create a minimal version of the script that renders the basic category template with the article links.
   - Use shared modules (logging, Jinja2 templating, DB communication) similar to `summarizer_html.py`.

6. **Logging & Debugging Setup**
   - Integrate DEBUG-level logging extensively throughout the new script.

7. **Image Processing Function**
   - **File:** `C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\nlp\summarizer\summarizer_category_utilities.py`
   - Develop functions to crop and downsize images to 300x200 and save them to the designated category images folder.

8. **Enhanced Category Layout Implementation**
   - Update the category template to mimic a CNN-like layout:
     - Top article with large image.
     - Next 3 articles with images.
     - Subcategory sections (derived from `article_html_file_location`) with a solid line and title, followed by the top 4 popular articles.
     - Additional 10 article links displayed below.

9. **Incremental Testing & Confirmation**
   - After each step (starting with the minimal page), we will test and confirm functionality before moving on to the next enhancement.

---

Please confirm if the above clarifications and plan of action are acceptable. Once you confirm, we can start with the first step—creating a minimal category page that lists article links.

NOTES:

when search for articles for certain category you need to take only articles where article_html_file_location is not empty.  

Final location of category html file generated should be in:
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\categories
make sure styles from there are correctly referenced relatively to :
CSS folder where category.css should be. 