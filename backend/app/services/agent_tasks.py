from uuid import uuid4
import json
import re
from sqlalchemy import select, update, inspect, func
from app.models import Store, Product
from app.models.agent_task import AgentTask, now
from app.db.session import SessionLocal
from app.agents.llm import create_llm
from app.agents.supervisor_graph import build_supervisor_graph
from app.agents.supervisor_state import SupervisorState
from app.schemas.agent_tasks import TaskDetail, TaskTrace

def scrub(value):
    text=json.dumps(value,ensure_ascii=False,default=str)
    try:
        from app.agents.llm import LLMSettings
        secret=LLMSettings().llm_api_key.get_secret_value()
        if secret:text=text.replace(secret,'[REDACTED]')
    except Exception:pass
    text=re.sub(r'Bearer [A-Za-z0-9._-]+','Bearer [REDACTED]',text)
    return json.loads(text)

TERMINAL={'completed','partial_failed','failed','unsupported','interrupted'}

class LLMNotConfiguredError(RuntimeError):pass

def run_graph(state,factory):
    from pydantic import ValidationError
    try:llm=create_llm()
    except ValidationError:raise LLMNotConfiguredError() from None
    return build_supervisor_graph(llm,factory).invoke(state.model_dump(),config={'recursion_limit':10})

class AgentTaskService:
    def __init__(self,factory=SessionLocal,runner=run_graph):self.factory=factory;self.runner=runner
    def create(self,request):
        with self.factory() as s:
            if not s.get(Store,request.store_id):raise LookupError('store_not_found')
            if request.selected_sku and not s.scalar(select(Product.id).where(Product.store_id==request.store_id,Product.sku==request.selected_sku)):raise LookupError('sku_not_found')
            task=AgentTask(task_id=str(uuid4()),**{**request.model_dump(),'user_query':scrub(request.user_query)},status='queued',trace_json={'schema_version':'1','route':None,'tools':[]})
            s.add(task);s.commit();s.refresh(task)
            return TaskDetail.model_validate(task)
    def get(self,task_id,store_id=None):
        with self.factory() as s:
            row=s.get(AgentTask,str(task_id))
            if not row or store_id is not None and row.store_id!=store_id:raise LookupError('task_not_found')
            return TaskDetail.model_validate(row)
    def list(self,store_id,status,page,page_size):
        with self.factory() as s:
            q=select(AgentTask).where(AgentTask.store_id==store_id)
            if status:q=q.where(AgentTask.status==status)
            total=s.scalar(select(func.count()).select_from(q.subquery()))
            rows=s.scalars(q.order_by(AgentTask.created_at.desc(),AgentTask.task_id.desc()).offset((page-1)*page_size).limit(page_size))
            return dict(items=[TaskDetail.model_validate(r) for r in rows],total=total,page=page,page_size=page_size)
    def finish(self,task_id,status,**values):
        if status not in TERMINAL:raise ValueError('invalid_terminal_state')
        with self.factory() as s:
            result=s.execute(update(AgentTask).where(AgentTask.task_id==str(task_id),AgentTask.status=='running').values(status=status,finished_at=now(),updated_at=now(),**values))
            s.commit();return result.rowcount==1
    def execute(self,task_id):
        # Claim and release transaction before any network call.
        with self.factory() as s:
            claim=s.execute(update(AgentTask).where(AgentTask.task_id==str(task_id),AgentTask.status=='queued').values(status='running',started_at=now(),updated_at=now()))
            s.commit()
            if claim.rowcount!=1:return False
            row=s.get(AgentTask,str(task_id))
            state=SupervisorState(task_id=row.task_id,store_id=row.store_id,user_query=row.user_query,start_date=row.start_date,end_date=row.end_date,selected_sku=row.selected_sku)
        try:
            result=SupervisorState.model_validate(self.runner(state,self.factory))
            if result.execution_status not in TERMINAL-{'interrupted'}:raise ValueError('invalid_graph_status')
            # Persist only typed report and trace, never raw provider errors/requests.
            trace=TaskTrace(route=result.route,tools=result.traces).model_dump(mode='json')
            report=result.report.model_dump(mode='json') if result.report else None
            code='analysis_partial_failure' if result.execution_status=='partial_failed' else 'analysis_failed' if result.execution_status=='failed' else None
            if result.errors:
                for candidate in ('llm_timeout','llm_api_error','llm_invalid_json','database_error','store_or_sku_not_found'):
                    if any(candidate in e for e in result.errors):code=candidate;break
            self.finish(task_id,result.execution_status,selected_agents=result.route.selected_agents if result.route else [],intent=result.route.intent if result.route else None,report_json=scrub(report),trace_json=scrub(trace),error_code=code,error_summary='部分分析失败，请复核结果。' if code=='analysis_partial_failure' else '分析失败，请检查模型配置、网络或数据。' if code else None)
        except Exception as exc:
            missing=isinstance(exc,LLMNotConfiguredError)
            self.finish(task_id,'failed',error_code='llm_not_configured' if missing else 'execution_error',error_summary='尚未配置有效的 LLM_BASE_URL、LLM_API_KEY 或 LLM_MODEL；没有调用模型。' if missing else '任务执行异常，请检查本地服务配置。')
        return True
    def recover(self):
        with self.factory() as s:
            if not inspect(s.get_bind()).has_table('agent_tasks'):return 0
            result=s.execute(update(AgentTask).where(AgentTask.status.in_(['running','queued'])).values(status='interrupted',error_code='process_restarted',error_summary='服务已重启，任务未自动恢复；请重新提交。',finished_at=now(),updated_at=now()))
            s.commit();return result.rowcount
