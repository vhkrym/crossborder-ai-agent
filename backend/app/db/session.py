from collections.abc import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import get_settings

def build_engine(url: str):
    result = create_engine(url, connect_args={'check_same_thread': False} if url.startswith('sqlite:') else {})
    if result.dialect.name == 'sqlite':
        @event.listens_for(result, 'connect')
        def enable_foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    return result

engine = build_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
