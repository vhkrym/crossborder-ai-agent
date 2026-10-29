from sqlalchemy.engine import Engine
from app.db.base import Base
from app.db.session import engine
import app.models  # Register all tables before create_all.


def init_db(bind: Engine = engine) -> None:
    """Create missing tables only; schema migrations are a separate operation."""
    Base.metadata.create_all(bind)


if __name__ == '__main__':
    init_db()
