# country_sources.py
"""
Curated mapping of countries to their most relevant subreddits, news sites,
and YouTube region codes for localized opinion collection.
"""

# Primary lookup by normalized country name.
# Each entry: {name, iso, subreddits, news_sites, youtube_regionCode}
COUNTRY_SOURCES = {
    "united states": {
        "name": "United States",
        "iso": "US",
        "subreddits": ["r/politics", "r/news", "r/worldnews", "r/conservative", "r/Liberal", "r/uspolitics"],
        "news_sites": ["foxnews.com", "cnn.com", "nytimes.com", "washingtonpost.com", "usatoday.com"],
        "youtube_regionCode": "US",
    },
    "united kingdom": {
        "name": "United Kingdom",
        "iso": "GB",
        "subreddits": ["r/unitedkingdom", "r/ukpolitics", "r/britishproblems"],
        "news_sites": ["bbc.co.uk", "theguardian.com", "thetimes.co.uk", "dailymail.co.uk", "telegraph.co.uk"],
        "youtube_regionCode": "GB",
    },
    "israel": {
        "name": "Israel",
        "iso": "IL",
        "subreddits": ["r/Israel", "r/IsraelPalestine", "r/MiddleEast"],
        "news_sites": ["haaretz.com", "jpost.com", "timesofisrael.com", "ynet.co.il", "ynetnews.com"],
        "youtube_regionCode": "IL",
    },
    "iran": {
        "name": "Iran",
        "iso": "IR",
        "subreddits": ["r/iran", "r/iranian", "r/MiddleEast"],
        "news_sites": ["irna.ir", "presstv.ir", "mehrnews.com", "tehrantimes.com", "isna.ir"],
        "youtube_regionCode": "IR",
    },
    "russia": {
        "name": "Russia",
        "iso": "RU",
        "subreddits": ["r/russia", "r/worldnews", "r/UkraineRussiaReport"],
        "news_sites": ["rt.com", "tass.com", "rbth.com", "interfax.com", "kommersant.com"],
        "youtube_regionCode": "RU",
    },
    "ukraine": {
        "name": "Ukraine",
        "iso": "UA",
        "subreddits": ["r/ukraine", "r/UkraineRussiaReport", "r/UkraineWarVideoReport"],
        "news_sites": ["kyivindependent.com", "pravda.com.ua", "ukrinform.ua", "unian.info", "lb.ua"],
        "youtube_regionCode": "UA",
    },
    "china": {
        "name": "China",
        "iso": "CN",
        "subreddits": ["r/Sino", "r/china", "r/ChinesePolitics"],
        "news_sites": ["globaltimes.cn", "scmp.com", "xinhuanet.com", "chinadaily.com.cn", "cgtn.com"],
        "youtube_regionCode": "CN",
    },
    "india": {
        "name": "India",
        "iso": "IN",
        "subreddits": ["r/india", "r/IndiaSpeaks", "r/indianews"],
        "news_sites": ["hindustantimes.com", "ndtv.com", "timesofindia.indiatimes.com", "thehindu.com", "indianexpress.com"],
        "youtube_regionCode": "IN",
    },
    "pakistan": {
        "name": "Pakistan",
        "iso": "PK",
        "subreddits": ["r/pakistan", "r/PakistanPolitics"],
        "news_sites": ["geo.tv", "dawn.com", "thenews.com.pk", "arynews.tv", "expresstribune.com.pk"],
        "youtube_regionCode": "PK",
    },
    "germany": {
        "name": "Germany",
        "iso": "DE",
        "subreddits": ["r/de", "r/germany", "r/GermanPolitics"],
        "news_sites": ["spiegel.de", "faz.net", "sueddeutsche.de", "dw.com", "tagesschau.de"],
        "youtube_regionCode": "DE",
    },
    "france": {
        "name": "France",
        "iso": "FR",
        "subreddits": ["r/france", "r/geopolitics"],
        "news_sites": ["lemonde.fr", "lefigaro.fr", "bfmtv.com", "liberation.fr", "france24.com"],
        "youtube_regionCode": "FR",
    },
    "turkey": {
        "name": "Turkey",
        "iso": "TR",
        "subreddits": ["r/Turkey", "r/turkishpolitics"],
        "news_sites": ["hurriyet.com.tr", "sabah.com.tr", "dailysabah.com", "trtworld.com", "hurriyetdailynews.com"],
        "youtube_regionCode": "TR",
    },
    "saudi arabia": {
        "name": "Saudi Arabia",
        "iso": "SA",
        "subreddits": ["r/saudiarabia", "r/MiddleEast"],
        "news_sites": ["arabnews.com", "saudigazette.com.sa", "aljazeera.com"],
        "youtube_regionCode": "SA",
    },
    "egypt": {
        "name": "Egypt",
        "iso": "EG",
        "subreddits": ["r/egypt", "r/MiddleEast"],
        "news_sites": ["ahram.org.eg", "egyptindependent.com", "madamasr.com", "dailynewsegypt.com"],
        "youtube_regionCode": "EG",
    },
    "australia": {
        "name": "Australia",
        "iso": "AU",
        "subreddits": ["r/australia", "r/AustralianPolitics"],
        "news_sites": ["abc.net.au", "smh.com.au", "theaustralian.com.au", "theguardian.com/au", "news.com.au"],
        "youtube_regionCode": "AU",
    },
    "canada": {
        "name": "Canada",
        "iso": "CA",
        "subreddits": ["r/canada", "r/CanadaPolitics"],
        "news_sites": ["cbc.ca", "globeandmail.com", "nationalpost.com", "thestar.com", "macleans.ca"],
        "youtube_regionCode": "CA",
    },
    "brazil": {
        "name": "Brazil",
        "iso": "BR",
        "subreddits": ["r/brasil", "r/brazilpolitics"],
        "news_sites": ["folha.uol.com.br", "g1.globo.com", "oglobo.globo.com", "agenciasenado.leg.br"],
        "youtube_regionCode": "BR",
    },
    "japan": {
        "name": "Japan",
        "iso": "JP",
        "subreddits": ["r/japan", "r/japannews"],
        "news_sites": ["japantimes.co.jp", "nhk.or.jp/nhkworld", "yomiuri.co.jp", "asahi.com", "mainichi.jp"],
        "youtube_regionCode": "JP",
    },
    "south korea": {
        "name": "South Korea",
        "iso": "KR",
        "subreddits": ["r/korea", "r/hanguk"],
        "news_sites": ["koreatimes.co.kr", "koreaherald.com", "yonhapnewsagency.com"],
        "youtube_regionCode": "KR",
    },
    "poland": {
        "name": "Poland",
        "iso": "PL",
        "subreddits": ["r/poland", "r/PolishPolitics"],
        "news_sites": ["polsatnews.pl", "tvn24.pl", "wyborcza.pl", "rp.pl"],
        "youtube_regionCode": "PL",
    },
    "netherlands": {
        "name": "Netherlands",
        "iso": "NL",
        "subreddits": ["r/Netherlands", "r/dutch"],
        "news_sites": ["nos.nl", "nu.nl", "telegraaf.nl", "rtlnieuws.nl"],
        "youtube_regionCode": "NL",
    },
    "sweden": {
        "name": "Sweden",
        "iso": "SE",
        "subreddits": ["r/sweden"],
        "news_sites": ["svt.se", "aftonbladet.se", "dn.se", "expressen.se"],
        "youtube_regionCode": "SE",
    },
    "mexico": {
        "name": "Mexico",
        "iso": "MX",
        "subreddits": ["r/mexico", "r/Mexican"],
        "news_sites": ["milenio.com", "excelsior.com.mx", "eluniversal.com.mx", "proceso.com.mx"],
        "youtube_regionCode": "MX",
    },
    "argentina": {
        "name": "Argentina",
        "iso": "AR",
        "subreddits": ["r/argentina"],
        "news_sites": ["infobae.com", "lanacion.com.ar", "clarin.com", "pagina12.com.ar"],
        "youtube_regionCode": "AR",
    },
    "nigeria": {
        "name": "Nigeria",
        "iso": "NG",
        "subreddits": ["r/Nigeria", "r/nairaland"],
        "news_sites": ["vanguardngr.com", "punchng.com", "thenationonlineng.net", "channels.tv"],
        "youtube_regionCode": "NG",
    },
}

# Aliases: alternative names/spellings → canonical key
_ALIASES = {
    "us": "united states",
    "usa": "united states",
    "america": "united states",
    "uk": "united kingdom",
    "britain": "united kingdom",
    "great britain": "united kingdom",
    "england": "united kingdom",
    "russian federation": "russia",
    "ussr": "russia",
    "prc": "china",
    "peoples republic of china": "china",
    "south korea": "south korea",
    "republic of korea": "south korea",
    "dprk": "north korea",
    "north korea": "north korea",
    "islamic republic of iran": "iran",
    "persia": "iran",
    "state of israel": "israel",
    "kingdom of saudi arabia": "saudi arabia",
    "ksa": "saudi arabia",
    "islamic republic of pakistan": "pakistan",
    "republic of india": "india",
    "republic of turkey": "turkey",
    "türkiye": "turkey",
    "argentine republic": "argentina",
    "federal republic of germany": "germany",
    "french republic": "france",
    "commonwealth of australia": "australia",
}

# Build a reverse lookup: subreddit → country name, for country inference from comments
SUBREDDIT_TO_COUNTRY = {}
for _key, _entry in COUNTRY_SOURCES.items():
    for _sub in _entry.get("subreddits", []):
        _normalized_sub = _sub.lower().replace("r/", "")
        SUBREDDIT_TO_COUNTRY[_normalized_sub] = _entry["name"]


def resolve_country(name_or_alias: str):
    """Return the COUNTRY_SOURCES entry for a given country name or alias, or None."""
    if not name_or_alias:
        return None
    key = name_or_alias.strip().lower()
    # Direct lookup first
    if key in COUNTRY_SOURCES:
        return COUNTRY_SOURCES[key]
    # Try aliases
    canonical = _ALIASES.get(key)
    if canonical and canonical in COUNTRY_SOURCES:
        return COUNTRY_SOURCES[canonical]
    # Partial match (country name appears as substring)
    for country_key, entry in COUNTRY_SOURCES.items():
        if key in country_key or country_key in key:
            return entry
    return None


def infer_country_from_subreddit(subreddit: str) -> str | None:
    """Return the country name inferred from a subreddit name, or None."""
    if not subreddit:
        return None
    normalized = subreddit.strip().lower().replace("r/", "")
    return SUBREDDIT_TO_COUNTRY.get(normalized)
