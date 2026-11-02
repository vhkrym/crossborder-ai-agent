from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from app.services.agent_tasks import AgentTaskService
from app.schemas.agent_tasks import TaskCreate,TaskCreated,TaskDetail,TaskPage,TaskStatus

router=APIRouter(prefix='/agent/tasks',tags=['local-demo-agent-tasks'])

def get_task_service():return AgentTaskService()
# Local trusted demo only. Add authenticated principal/store authorization here before public use.
@router.post('',response_model=TaskCreated,status_code=202)
def create_task(body:TaskCreate,background:BackgroundTasks,service=Depends(get_task_service)):
    try:task=service.create(body)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
    background.add_task(service.execute,str(task.task_id))
    return task

@router.get('',response_model=TaskPage)
def list_tasks(store_id:int=Query(gt=0),status:TaskStatus|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),service=Depends(get_task_service)):
    return service.list(store_id,status,page,page_size)

@router.get('/{task_id}',response_model=TaskDetail)
def task_detail(task_id:UUID,store_id:int|None=Query(None,gt=0),service=Depends(get_task_service)):
    try:return service.get(task_id,store_id)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
