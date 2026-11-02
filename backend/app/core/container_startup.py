"""Container-only explicit initialization/migration, then single-worker Uvicorn."""
import os
from pathlib import Path
from sqlalchemy import inspect, select, func
from sqlalchemy.engine import make_url
from app.db.session import build_engine
from app.demo.seed import seed_demo, MODELS
from app.db.migrate_agent_tasks import migrate as tasks
from app.db.migrate_decisions import migrate as decisions
from app.db.migrate_decision_approvals import migrate as approvals
from app.db.migrate_decision_simulations import migrate as simulations

def prepare_database(url: str):
    parsed=make_url(url)
    if parsed.drivername!='sqlite' or not parsed.database or not Path(parsed.database).is_absolute():
        raise ValueError('Container requires absolute SQLite path')
    path=Path(parsed.database)
    path.parent.mkdir(parents=True,exist_ok=True)
    fresh=not path.exists()
    engine=build_engine(url)
    try:
        if fresh:
            seed_demo(engine)
        else:
            expected=set(MODELS)
            if not expected.issubset(inspect(engine).get_table_names()):
                raise RuntimeError('Existing database is incomplete; refusing automatic reseed')
            schema=inspect(engine)
            for name,model in MODELS.items():
                required={column.name for column in model.__table__.columns}
                present={column['name'] for column in schema.get_columns(name)}
                if not required.issubset(present):raise RuntimeError('Existing business schema incompatible; refusing automatic reseed')
            with engine.connect() as c:
                if c.scalar(select(func.count()).select_from(MODELS['stores']))==0:
                    raise RuntimeError('Existing database has no stores; refusing automatic reseed')
        for migration in (tasks,decisions,approvals,simulations):migration(engine)
        with engine.connect() as c:
            if c.exec_driver_sql('PRAGMA foreign_key_check').fetchall():raise RuntimeError('Foreign key check failed')
        return 'initialized' if fresh else 'migrated_existing'
    finally:engine.dispose()

def main():
    # Do not log configuration or exception payloads; keys are runtime-only.
    url=os.environ.get('DATABASE_URL','')
    try:result=prepare_database(url)
    except Exception:
        print('Database initialization/migration failed; server not started. Inspect volume and migration prerequisites.',flush=True)
        raise SystemExit(1)
    print('Database ready: '+result,flush=True)
    os.execvp('python',['python','-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8000','--workers','1'])

if __name__=='__main__':main()
