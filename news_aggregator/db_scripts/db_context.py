# path: news_dagster-etl/news_aggregator/db_scripts/db_context.py
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
import sqlalchemy as sa
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from db_scripts.db_utils import load_db_config

class DatabaseContext:
    _instances: Dict[str, 'DatabaseContext'] = {}
    
    def __init__(self, env: str = 'dev'):
        """Initialize database context with environment-specific configuration"""
        self.env = env
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._setup_engine()
    
    @classmethod
    def get_instance(cls, env: str = 'dev') -> 'DatabaseContext':
        """Get or create a DatabaseContext instance for the specified environment"""
        if env not in cls._instances:
            cls._instances[env] = cls(env)
        return cls._instances[env]
    
    def _setup_engine(self) -> None:
        """Set up SQLAlchemy engine with proper pooling configuration"""
        db_config = load_db_config()
        if not db_config or self.env not in db_config:
            raise ValueError(f"No database configuration found for environment: {self.env}")
        
        params = db_config[self.env]
        shared_config = db_config.get('shared', {})
        
        # Construct connection URL
        url = f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['name']}"
        
        # Configure pooling
        pool_config = params.get('pool', {})
        pooling_args = {
            'poolclass': QueuePool,
            'pool_size': pool_config.get('max_connections', 10),
            'max_overflow': 5,
            'pool_timeout': 30,
            'pool_recycle': pool_config.get('idle_timeout', 300),
            'pool_pre_ping': True,
        }
        
        # Configure connection arguments
        connect_args = {
            'application_name': shared_config.get('application_name', 'news_aggregator'),
            'connect_timeout': shared_config.get('connect_timeout', 10),
            'options': f"-c statement_timeout={shared_config.get('statement_timeout', 30000)}",
        }
        
        if shared_config.get('ssl_mode'):
            connect_args['sslmode'] = shared_config['ssl_mode']
        
        self._engine = sa.create_engine(
            url,
            **pooling_args,
            connect_args=connect_args,
            echo=False  # Set to True for SQL query logging
        )
        
        self._session_factory = sessionmaker(
            bind=self._engine,
            expire_on_commit=False
        )
    
    @property
    def engine(self) -> Engine:
        """Get SQLAlchemy engine instance"""
        if not self._engine:
            self._setup_engine()
        return self._engine
    
    def get_connection_string(self) -> str:
        """Get database connection string for SQLAlchemy"""
        db_config = load_db_config()
        if not db_config or self.env not in db_config:
            raise ValueError(f"No database configuration found for environment: {self.env}")
        
        params = db_config[self.env]
        return f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['name']}"
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Get a database session context manager
        
        Returns:
            Generator[Session, None, None]: A context manager that yields a SQLAlchemy Session
        """
        if not self._session_factory:
            self._setup_engine()
            
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def connection(self) -> Generator[Connection, None, None]:
        """Get a raw connection context manager
        
        Returns:
            Generator[Connection, None, None]: A context manager that yields a SQLAlchemy Connection
        """
        with self.engine.connect() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def dispose(self) -> None:
        """Dispose of the engine and all connections"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
    
    def __enter__(self) -> 'DatabaseContext':
        return self
    
    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        self.dispose()
        
        
    def fetch_all(self, query: str) -> list:
        """
        Execute the given SQL query and return the result as a list of dictionaries.
        """
        with self.connection() as conn:
            result = conn.execute(sa.text(query))
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

