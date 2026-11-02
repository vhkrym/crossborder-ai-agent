from sqlalchemy import inspect
from app.db.session import engine
from app.models.decision_simulation import DecisionSimulation

def migrate(bind=engine):
    if not inspect(bind).has_table('decision_audits'):raise RuntimeError('Migrate approvals first')
    with bind.connect() as c:
        c.exec_driver_sql('BEGIN IMMEDIATE')
        try:
            DecisionSimulation.__table__.create(c,checkfirst=True)
            c.exec_driver_sql("CREATE TRIGGER IF NOT EXISTS simulations_no_delete BEFORE DELETE ON decision_simulations BEGIN SELECT RAISE(ABORT,'simulation_history_is_immutable'); END")
            c.exec_driver_sql("CREATE TRIGGER IF NOT EXISTS simulations_terminal_immutable BEFORE UPDATE ON decision_simulations WHEN OLD.status IN ('simulation_completed','simulation_failed','interrupted') BEGIN SELECT RAISE(ABORT,'terminal_simulation_is_immutable'); END")
            if c.exec_driver_sql('PRAGMA foreign_key_check').fetchall():raise RuntimeError('foreign_key_check_failed')
            c.commit()
        except Exception:c.rollback();raise
if __name__=='__main__':migrate()
