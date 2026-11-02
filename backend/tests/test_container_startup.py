from sqlalchemy import text
import pytest
from app.core.container_startup import prepare_database
from app.db.session import build_engine


def test_first_boot_restart_preserves_existing_data(tmp_path):
    url='sqlite:///'+(tmp_path/'demo.db').as_posix()
    assert prepare_database(url)=='initialized'
    e=build_engine(url)
    with e.begin() as c:
        c.execute(text("UPDATE stores SET name='user edited' WHERE id=1"))
        before={t:c.scalar(text('SELECT COUNT(*) FROM '+t)) for t in ('stores','products','sales_records','ad_records','inventory_snapshots','cost_records','data_imports')}
    e.dispose()
    assert prepare_database(url)=='migrated_existing'
    assert prepare_database(url)=='migrated_existing'
    e=build_engine(url)
    with e.connect() as c:
        assert c.scalar(text('SELECT name FROM stores WHERE id=1'))=='user edited'
        assert before=={t:c.scalar(text('SELECT COUNT(*) FROM '+t)) for t in before}
        assert c.scalar(text('PRAGMA foreign_keys'))==1
        for t in ('agent_tasks','decision_proposals','decision_audits','decision_simulations'):
            assert c.scalar(text('SELECT COUNT(*) FROM '+t))==0
    e.dispose()


def test_existing_empty_file_never_reseeded(tmp_path):
    path=tmp_path/'existing.db';path.touch()
    with pytest.raises(RuntimeError,match='refusing automatic reseed'):prepare_database('sqlite:///'+path.as_posix())


def test_migration_error_prevents_ready(tmp_path,monkeypatch):
    import app.core.container_startup as module
    def fail(_):raise RuntimeError('migration failure')
    monkeypatch.setattr(module,'approvals',fail)
    with pytest.raises(RuntimeError,match='migration failure'):prepare_database('sqlite:///'+(tmp_path/'test.db').as_posix())

@pytest.mark.parametrize('url',['sqlite:///relative.db','sqlite:///:memory:','postgresql://localhost/test'])
def test_invalid_container_database_path(url):
    with pytest.raises(ValueError):prepare_database(url)


def test_old_business_schema_is_not_silently_accepted(tmp_path):
    url='sqlite:///'+(tmp_path/'old.db').as_posix();prepare_database(url)
    e=build_engine(url)
    with e.begin() as c:c.exec_driver_sql('ALTER TABLE stores DROP COLUMN currency')
    e.dispose()
    with pytest.raises(RuntimeError,match='business schema incompatible'):prepare_database(url)
