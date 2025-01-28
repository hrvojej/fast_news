import psycopg2
from dataclasses import dataclass
from typing import List, Optional
from abc import ABC, abstractmethod

@dataclass
class Portal:
    portal_id: int
    portal_name: str
    portal_domain: str
    bucket_prefix: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class Category:
    category_id: int
    name: str
    slug: str
    portal_id: int
    path: str
    level: int
    title: Optional[str] = None
    link: Optional[str] = None
    atom_link: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    copyright_text: Optional[str] = None
    last_build_date: Optional[str] = None
    pub_date: Optional[str] = None
    image_title: Optional[str] = None
    image_url: Optional[str] = None
    image_link: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class Article:
    article_id: int
    title: str
    url: str
    guid: Optional[str] = None
    description: Optional[str] = None
    author: Optional[List[str]] = None
    pub_date: Optional[str] = None
    category_id: int
    keywords: Optional[List[str]] = None
    image_url: Optional[str] = None
    image_width: Optional[int] = None
    image_credit: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class Event:
    event_id: int
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    status: Optional[str] = 'active'
    confidence_score: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class Topic:
    topic_id: int
    name: str
    description: Optional[str] = None
    parent_topic_id: Optional[int] = None
    confidence_score: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class Entity:
    entity_id: int
    name: str
    entity_type: str
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class EventArticle:
    event_id: int
    article_id: int
    portal_id: int
    similarity_score: float
    created_at: Optional[str] = None

@dataclass
class TopicEvent:
    topic_id: int
    event_id: int
    confidence_score: float
    created_at: Optional[str] = None

@dataclass
class EntityEvent:
    entity_id: int
    event_id: int
    role: Optional[str] = None
    confidence_score: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class DataAdapter(ABC):
    def __init__(self, conn):
        self.conn = conn
        # self.cursor = self.conn.cursor() # Cursor will be created in concrete classes - Removed from base class

    @abstractmethod
    def get_by_id(self, id):
        pass

    @abstractmethod
    def create(self, data_object):
        pass

    @abstractmethod
    def update(self, id, data_object):
        pass

    @abstractmethod
    def delete(self, id):
        pass

    @abstractmethod
    def list_all(self) -> list:
        pass


class PortalDataAdapter(DataAdapter):
    def get_by_id(self, portal_id: int) -> Optional[Portal]:
        self.cursor.execute("SELECT * FROM public.news_portals WHERE portal_id = %s", (portal_id,))
        record = self.cursor.fetchone()
        if record:
            return Portal(*record)
        return None

    def create(self, portal: Portal) -> Optional[Portal]:
        self.cursor.execute(
            """
            INSERT INTO public.news_portals (portal_name, portal_domain, bucket_prefix) 
            VALUES (%s, %s, %s) RETURNING *
            """,
            (portal.portal_name, portal.portal_domain, portal.bucket_prefix)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return Portal(*record)
        return None

    def update(self, portal_id: int, portal: Portal) -> Optional[Portal]:
        self.cursor.execute(
            """
            UPDATE public.news_portals 
            SET portal_name=%s, portal_domain=%s, bucket_prefix=%s 
            WHERE portal_id=%s RETURNING *
            """,
            (portal.portal_name, portal.portal_domain, portal.portal_prefix, portal_id)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return Portal(*record)
        return None

    def delete(self, portal_id: int) -> bool:
        self.cursor.execute("DELETE FROM public.news_portals WHERE portal_id = %s", (portal_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def list_all(self) -> List[Portal]:
        self.cursor.execute("SELECT * FROM public.news_portals")
        records = self.cursor.fetchall()
        portals = []
        for record in records:
            portals.append(Portal(*record))
        return portals

class CategoryDataAdapter(DataAdapter):
    def get_by_id(self, portal_prefix: str, category_id: int) -> Optional[Category]:
        self.cursor.execute(f"SELECT * FROM {portal_prefix}.categories WHERE category_id = %s", (category_id,))
        record = self.cursor.fetchone()
        if record:
            return Category(*record)
        return None

    def create(self, portal_prefix: str, category: Category) -> Optional[Category]:
        self.cursor.execute(
            f"""
            INSERT INTO {portal_prefix}.categories (name, slug, portal_id, path, level, title, link, atom_link, description, language, copyright_text, last_build_date, pub_date, image_title, image_url, image_link)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *
            """,
            (category.name, category.slug, category.portal_id, category.path, category.level, category.title, category.link, category.atom_link, category.description, category.language, category.copyright_text, category.last_build_date, category.pub_date, category.image_title, category.image_url, category.image_link)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return Category(*record)
        return None

    def update(self, portal_prefix: str, category_id: int, category: Category) -> Optional[Category]:
        self.cursor.execute(
            f"""
            UPDATE {portal_prefix}.categories 
            SET name=%s, slug=%s, portal_id=%s, path=%s, level=%s, title=%s, link=%s, atom_link=%s, description=%s, language=%s, copyright_text=%s, last_build_date=%s, pub_date=%s, image_title=%s, image_url=%s, image_link=%s
            WHERE category_id=%s RETURNING *
            """,
            (category.name, category.slug, category.portal_id, category.path, category.level, category.title, category.link, category.atom_link, category.description, category.language, category.copyright_text, category.last_build_date, category.pub_date, category.image_title, category.image_url, category.image_link, category_id)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return Category(*record)
        return None

    def delete(self, portal_prefix: str, category_id: int) -> bool:
        self.cursor.execute(f"DELETE FROM {portal_prefix}.categories WHERE category_id = %s", (category_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def list_all(self, portal_prefix: str) -> List[Category]:
        self.cursor.execute(f"SELECT * FROM {portal_prefix}.categories")
        records = self.cursor.fetchall()
        categories = []
        for record in records:
            categories.append(Category(*record))
        return categories


class ArticleDataAdapter(DataAdapter):
    def get_by_id(self, portal_prefix: str, article_id: int) -> Optional[Article]:
        self.cursor.execute(f"SELECT * FROM {portal_prefix}.articles WHERE article_id = %s", (article_id,))
        record = self.cursor.fetchone()
        if record:
            return Article(*record)
        return None

    def create(self, portal_prefix: str, article: Article) -> Optional[Article]:
        self.cursor.execute(
            f"""
            INSERT INTO {portal_prefix}.articles (title, url, guid, description, author, pub_date, category_id, keywords, image_url, image_width, image_credit)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *
            """,
            (article.title, article.url, article.guid, article.description, article.author, article.pub_date, article.category_id, article.keywords, article.image_url, article.image_width, article.image_credit)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return Article(*record)
        return None

    def update(self, portal_prefix: str, article_id: int, article: Article) -> Optional[Article]:
        self.cursor.execute(
            f"""
            UPDATE {portal_prefix}.articles
            SET title=%s, url=%s, guid=%s, description=%s, author=%s, pub_date=%s, category_id=%s, keywords=%s, image_url=%s, image_width=%s, image_credit=%s
            WHERE article_id=%s RETURNING *
            """,
            (article.title, article.url, article.guid, article.description, article.author, article.pub_date, article.category_id, article.keywords, article.image_url, article.image_width, article.image_credit, article_id)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return Article(*record)
        return None

    def delete(self, portal_prefix: str, article_id: int) -> bool:
        self.cursor.execute(f"DELETE FROM {portal_prefix}.articles WHERE article_id = %s", (article_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def list_all(self, portal_prefix: str) -> List[Article]:
        self.cursor.execute(f"SELECT * FROM {portal_prefix}.articles")
        records = self.cursor.fetchall()
        articles = []
        for record in records:
            articles.append(Article(*record))
        return articles


class EventDataAdapter(DataAdapter):
    def get_by_id(self, event_id: int) -> Optional[Event]:
        self.cursor.execute(f"SELECT * FROM events.events WHERE event_id = %s", (event_id,))
        record = self.cursor.fetchone()
        if record:
            return Event(*record)
        return None

    def create(self, event: Event) -> Optional[Event]:
        self.cursor.execute(
            """
            INSERT INTO events.events (title, description, start_time, end_time, status, confidence_score)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
            """,
            (event.title, event.description, event.start_time, event.end_time, event.status, event.confidence_score)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return Event(*record)
        return None

    def update(self, event_id: int, event: Event) -> Optional[Event]:
        self.cursor.execute(
            """
            UPDATE events.events
            SET title=%s, description=%s, start_time=%s, end_time=%s, status=%s, confidence_score=%s
            WHERE event_id=%s RETURNING *
            """,
            (event.title, event.description, event.start_time, event.end_time, event.status, event.confidence_score, event_id)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return Event(*record)
        return None

    def delete(self, event_id: int) -> bool:
        self.cursor.execute("DELETE FROM events.events WHERE event_id = %s", (event_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def list_all(self) -> List[Event]:
        self.cursor.execute("SELECT * FROM events.events")
        records = self.cursor.fetchall()
        events = []
        for record in records:
            events.append(Event(*record))
        return events


class TopicDataAdapter(DataAdapter):
    def get_by_id(self, topic_id: int) -> Optional[Topic]:
        self.cursor.execute(f"SELECT * FROM topics.topics WHERE topic_id = %s", (topic_id,))
        record = self.cursor.fetchone()
        if record:
            return Topic(*record)
        return None

    def create(self, topic: Topic) -> Optional[Topic]:
        self.cursor.execute(
            """
            INSERT INTO topics.topics (name, description, parent_topic_id, confidence_score)
            VALUES (%s, %s, %s, %s) RETURNING *
            """,
            (topic.name, topic.description, topic.parent_topic_id, topic.confidence_score)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return Topic(*record)
        return None

    def update(self, topic_id: int, topic: Topic) -> Optional[Topic]:
        self.cursor.execute(
            """
            UPDATE topics.topics
            SET name=%s, description=%s, parent_topic_id=%s, confidence_score=%s
            WHERE topic_id=%s RETURNING *
            """,
            (topic.name, topic.description, topic.parent_topic_id, topic.confidence_score, topic_id)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return Topic(*record)
        return None

    def delete(self, topic_id: int) -> bool:
        self.cursor.execute("DELETE FROM topics.topics WHERE topic_id = %s", (topic_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def list_all(self) -> List[Topic]:
        self.cursor.execute("SELECT * FROM topics.topics")
        records = self.cursor.fetchall()
        topics = []
        for record in records:
            topics.append(Topic(*record))
        return topics


class EntityDataAdapter(DataAdapter):
    def get_by_id(self, entity_id: int) -> Optional[Entity]:
        self.cursor.execute(f"SELECT * FROM entities.entities WHERE entity_id = %s", (entity_id,))
        record = self.cursor.fetchone()
        if record:
            return Entity(*record)
        return None

    def create(self, entity: Entity) -> Optional[Entity]:
        self.cursor.execute(
            """
            INSERT INTO entities.entities (name, entity_type, description)
            VALUES (%s, %s, %s) RETURNING *
            """,
            (entity.name, entity.entity_type, entity.description)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return Entity(*record)
        return None

    def update(self, entity_id: int, entity: Entity) -> Optional[Entity]:
        self.cursor.execute(
            """
            UPDATE entities.entities
            SET name=%s, entity_type=%s, description=%s
            WHERE entity_id=%s RETURNING *
            """,
            (entity.name, entity.entity_type, entity.description, entity_id)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return Entity(*record)
        return None

    def delete(self, entity_id: int) -> bool:
        self.cursor.execute("DELETE FROM entities.entities WHERE entity_id = %s", (entity_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def list_all(self) -> List[Entity]:
        self.cursor.execute("SELECT * FROM entities.entities")
        records = self.cursor.fetchall()
        entities = []
        for record in records:
            entities.append(Entity(*record))
        return entities


class EventArticleDataAdapter(DataAdapter):
    def get_by_id(self, event_id: int, article_id: int, portal_id: int) -> Optional[EventArticle]:
        self.cursor.execute("SELECT * FROM events.event_articles WHERE event_id = %s AND article_id = %s AND portal_id = %s", (event_id, article_id, portal_id))
        record = self.cursor.fetchone()
        if record:
            return EventArticle(*record)
        return None

    def create(self, event_article: EventArticle) -> Optional[EventArticle]:
        self.cursor.execute(
            """
            INSERT INTO events.event_articles (event_id, article_id, portal_id, similarity_score)
            VALUES (%s, %s, %s, %s) RETURNING *
            """,
            (event_article.event_id, event_article.article_id, event_article.portal_id, event_article.similarity_score)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return EventArticle(*record)
        return None

    def update(self, event_id: int, article_id: int, portal_id: int, event_article: EventArticle) -> Optional[EventArticle]:
        self.cursor.execute(
            """
            UPDATE events.event_articles
            SET similarity_score=%s
            WHERE event_id=%s AND article_id=%s AND portal_id=%s RETURNING *
            """,
            (event_article.similarity_score, event_id, article_id, portal_id)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return EventArticle(*record)
        return None

    def delete(self, event_id: int, article_id: int, portal_id: int) -> bool:
        self.cursor.execute("DELETE FROM events.event_articles WHERE event_id = %s AND article_id = %s AND portal_id = %s", (event_id, article_id, portal_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def list_all(self) -> List[EventArticle]:
        self.cursor.execute("SELECT * FROM events.event_articles")
        records = self.cursor.fetchall()
        event_articles = []
        for record in records:
            event_articles.append(EventArticle(*record))
        return event_articles


class TopicEventDataAdapter(DataAdapter):
    def get_by_id(self, topic_id: int, event_id: int) -> Optional[TopicEvent]:
        self.cursor.execute(f"SELECT * FROM topics.topic_events WHERE topic_id = %s AND event_id = %s", (topic_id, event_id))
        record = self.cursor.fetchone()
        if record:
            return TopicEvent(*record)
        return None

    def create(self, topic_event: TopicEvent) -> Optional[TopicEvent]:
        self.cursor.execute(
            """
            INSERT INTO topics.topic_events (topic_id, event_id, confidence_score)
            VALUES (%s, %s, %s) RETURNING *
            """,
            (topic_event.topic_id, topic_event.event_id, topic_event.confidence_score)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return TopicEvent(*record)
        return None

    def update(self, topic_id: int, event_id: int, topic_event: TopicEvent) -> Optional[TopicEvent]:
        self.cursor.execute(
            """
            UPDATE topics.topic_events
            SET confidence_score=%s
            WHERE topic_id=%s AND event_id=%s RETURNING *
            """,
            (topic_event.confidence_score, topic_id, event_id)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return TopicEvent(*record)
        return None

    def delete(self, topic_id: int, event_id: int) -> bool:
        self.cursor.execute("DELETE FROM topics.topic_events WHERE topic_id = %s AND event_id = %s", (topic_id, event_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def list_all(self) -> List[TopicEvent]:
        self.cursor.execute("SELECT * FROM topics.topic_events")
        records = self.cursor.fetchall()
        topic_events = []
        for record in records:
            topic_events.append(TopicEvent(*record))
        return topic_events



class EntityEventDataAdapter(DataAdapter):
    def get_by_id(self, entity_id: int, event_id: int) -> Optional[EntityEvent]:
        self.cursor.execute(f"SELECT * FROM entities.entity_events WHERE entity_id = %s AND event_id = %s", (entity_id, event_id))
        record = self.cursor.fetchone()
        if record:
            return EntityEvent(*record)
        return None

    def create(self, entity_event: EntityEvent) -> Optional[EntityEvent]:
        self.cursor.execute(
            """
            INSERT INTO entities.entity_events (entity_id, event_id, role, confidence_score)
            VALUES (%s, %s, %s, %s) RETURNING *
            """,
            (entity_event.entity_id, entity_event.event_id, entity_event.role, entity_event.confidence_score)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return EntityEvent(*record)
        return None

    def update(self, entity_id: int, event_id: int, entity_event: EntityEvent) -> Optional[EntityEvent]:
        self.cursor.execute(
            """
            UPDATE entities.entity_events
            SET role=%s, confidence_score=%s
            WHERE entity_id=%s AND event_id=%s RETURNING *
            """,
            (entity_event.role, entity_event.confidence_score, entity_id, event_id)
        )
        record = self.cursor.fetchone()
        if record:
            self.conn.commit()
            return EntityEvent(*record)
        return None

    def delete(self, entity_id: int, event_id: int) -> bool:
        self.cursor.execute("DELETE FROM entities.entity_events WHERE entity_id = %s AND event_id = %s", (entity_id, event_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def list_all(self) -> List[EntityEvent]:
        self.cursor.execute("SELECT * FROM entities.entity_events")
        records = self.cursor.fetchall()
        entity_events = []
        for record in records:
            entity_events.append(EntityEvent(*record))
        return entity_events
