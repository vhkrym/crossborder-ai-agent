"""Manual browser QA only: all data temporary; model is explicitly Fake."""
from tempfile import TemporaryDirectory
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sqlalchemy.orm import sessionmaker
from app.db.session import build_engine,get_db
from app.demo.seed import seed_demo
from app.db.migrate_agent_tasks import migrate
from app.services.agent_tasks import AgentTaskService
from app.api.v1.agent_tasks import get_task_service
from app.agents.supervisor_graph import build_supervisor_graph
from fastapi import FastAPI
from app.api.v1.router import router
from app.db.migrate_decisions import migrate as md
from app.db.migrate_decision_approvals import migrate as ma
from app.db.migrate_decision_simulations import migrate as ms
from app.services.decisions import DecisionService
from app.services.decision_approvals import ApprovalService
from app.services.simulations import SimulationService
from app.api.v1.decisions import get_decision_service
from app.api.v1.decision_approvals import get_approval_service
from app.api.v1.simulations import get_simulation_service
from test_supervisor import FakeLLM
import uvicorn

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--port",type=int,default=8002);args=p.parse_args()
    with TemporaryDirectory() as tmp:
        engine=build_engine('sqlite:///'+(Path(tmp)/'qa.db').as_posix());seed_demo(engine);migrate(engine);md(engine);ma(engine);ms(engine)
        factory=sessionmaker(bind=engine)
        def runner(state,factory):
            import time
            time.sleep(3)
            return build_supervisor_graph(FakeLLM('profit'),factory).invoke(state.model_dump())
        service=AgentTaskService(factory,runner)
        app=FastAPI();app.include_router(router,prefix="/api/v1")
        def db():
            with factory() as session:yield session
        app.dependency_overrides[get_db]=db
        app.dependency_overrides[get_task_service]=lambda:service
        app.dependency_overrides[get_decision_service]=lambda:DecisionService(factory)
        app.dependency_overrides[get_approval_service]=lambda:ApprovalService(factory)
        app.dependency_overrides[get_simulation_service]=lambda:SimulationService(factory)
        uvicorn.run(app,host='127.0.0.1',port=args.port)
        engine.dispose()
if __name__=='__main__':main()
