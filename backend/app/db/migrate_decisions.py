from sqlalchemy import inspect,text
from app.db.session import engine
from app.models.decision import DecisionProposal,DecisionGeneration

def migrate(bind=engine):
    if not inspect(bind).has_table('agent_tasks'):raise RuntimeError('Migrate agent_tasks first')
    # Additive parent key index, no column changes or row changes.
    with bind.begin() as c:c.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_task_store_identity ON agent_tasks(task_id,store_id)'))
    DecisionGeneration.__table__.create(bind,checkfirst=True)
    DecisionProposal.__table__.create(bind,checkfirst=True)
if __name__=='__main__':migrate()
