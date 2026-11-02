"""SQLite transactional copy migration for the existing status CHECK constraint."""
from sqlalchemy import text,inspect
from app.db.session import engine
from app.models.decision import DecisionProposal
from app.models.decision_audit import DecisionAudit

def migrate(bind=engine):
    if bind.dialect.name!='sqlite':raise RuntimeError('SQLite migration only')
    if not inspect(bind).has_table('decision_proposals'):raise RuntimeError('Migrate decisions first')
    with bind.connect() as c:
        c.exec_driver_sql('BEGIN IMMEDIATE')
        try:
            ddl=c.scalar(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='decision_proposals'"))
            if "'approved'" not in ddl:
                if inspect(c).has_table('decision_audits'):raise RuntimeError('Unexpected old constraint with existing audit table')
                newddl=ddl.replace("status IN ('draft','pending_review')", "status IN ('draft','pending_review','approved','rejected')")
                if newddl==ddl:raise RuntimeError('Unrecognized constraint; migration aborted')
                newddl=newddl.replace('CREATE TABLE decision_proposals','CREATE TABLE decision_proposals_v7b',1)
                c.exec_driver_sql(newddl)
                columns=','.join('"'+col.name+'"' for col in DecisionProposal.__table__.columns)
                c.exec_driver_sql(f'INSERT INTO decision_proposals_v7b ({columns}) SELECT {columns} FROM decision_proposals')
                old=c.scalar(text('SELECT COUNT(*) FROM decision_proposals'));new=c.scalar(text('SELECT COUNT(*) FROM decision_proposals_v7b'))
                if old!=new:raise RuntimeError('Copy count mismatch')
                c.exec_driver_sql('DROP TABLE decision_proposals')
                c.exec_driver_sql('ALTER TABLE decision_proposals_v7b RENAME TO decision_proposals')
                for index in DecisionProposal.__table__.indexes:index.create(c)
            c.exec_driver_sql('CREATE UNIQUE INDEX IF NOT EXISTS uq_proposal_store_identity ON decision_proposals(proposal_id,store_id)')
            DecisionAudit.__table__.create(c,checkfirst=True)
            for action in ('UPDATE','DELETE'):
                c.exec_driver_sql(f"CREATE TRIGGER IF NOT EXISTS decision_audits_no_{action.lower()} BEFORE {action} ON decision_audits BEGIN SELECT RAISE(ABORT, 'audit_log_is_immutable'); END")
            if c.exec_driver_sql('PRAGMA foreign_key_check').fetchall():raise RuntimeError('Foreign key check failed')
            c.commit()
        except Exception:c.rollback();raise
if __name__=='__main__':migrate()
