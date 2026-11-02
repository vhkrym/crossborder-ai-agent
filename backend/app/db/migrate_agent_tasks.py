"""Additive migration; never creates or modifies the seven business tables."""
from sqlalchemy import inspect
from app.models.agent_task import AgentTask
from app.db.session import engine

def migrate(bind=engine):
    if 'stores' not in inspect(bind).get_table_names():
        raise RuntimeError('Initialize business database first')
    AgentTask.__table__.create(bind,checkfirst=True)

if __name__=='__main__': migrate()
