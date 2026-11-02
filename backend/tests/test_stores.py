from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db.session import build_engine, get_db
from app.db.init_db import init_db
from app.main import create_app
from app.models import Store

def test_stores(tmp_path):
    e=build_engine('sqlite:///'+(tmp_path/'stores.db').as_posix()); init_db(e)
    app=create_app()
    def db():
        with Session(e) as s: yield s
    app.dependency_overrides[get_db]=db
    with TestClient(app) as client:
        assert client.get('/api/v1/stores').json()==[]
        with Session(e) as s:
            s.add(Store(id=17,name='test',marketplace='Amazon',market='US',currency='USD')); s.commit()
        assert client.get('/api/v1/stores').json()==[dict(id=17,name='test',marketplace='Amazon',market='US',currency='USD')]
    e.dispose()
