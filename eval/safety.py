"""Evaluation-only prompt adapter; production Graph and default prompt stay intact."""
import ast
import hashlib
import json
from pathlib import Path
from langchain_core.messages import SystemMessage
from eval.common import ROOT, Case
from app.agents.supervisor_graph import AGENT_TO_TOOL
from app.agents.supervisor_state import RouteDecision

DATASET=ROOT/'eval/datasets/safety_routing_cases.jsonl'
MANIFEST=ROOT/'eval/datasets/safety_routing_manifest.json'
PROMPTS=ROOT/'eval/prompts'


def production_prompt():
    source=(ROOT/'backend/app/agents/supervisor_graph.py').read_text(encoding='utf-8')
    tree=ast.parse(source)
    matches=[n.args[2].value for n in ast.walk(tree) if isinstance(n,ast.Call)
             and isinstance(n.func,ast.Name) and n.func.id=='ask_json'
             and isinstance(n.args[1],ast.Name) and n.args[1].id=='RouteDecision']
    if len(matches)!=1:raise ValueError('production Supervisor prompt contract changed')
    return matches[0]


def prompt_config(variant):
    if variant not in ('baseline','candidate'):raise ValueError('invalid variant')
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    text=(PROMPTS/(variant+'.txt')).read_text(encoding='utf-8').rstrip('\n')
    digest=hashlib.sha256(text.encode('utf-8')).hexdigest()
    if digest!=manifest['prompt_sha256'][variant]:raise ValueError('prompt SHA mismatch')
    baseline=(PROMPTS/'baseline.txt').read_text(encoding='utf-8').rstrip('\n')
    if baseline!=production_prompt():raise ValueError('frozen baseline differs from production')
    return text,digest


class PromptVariant:
    def __init__(self,llm,variant):
        self.llm=llm;self.prompt,self.sha=prompt_config(variant)
        self.baseline=production_prompt()

    def invoke(self,messages):
        marker=' Return only valid JSON matching: '
        messages=list(messages)
        if messages and isinstance(messages[0].content,str) and messages[0].content.startswith(self.baseline+marker):
            suffix=messages[0].content[len(self.baseline):]
            messages[0]=SystemMessage(content=self.prompt+suffix)
        return self.llm.invoke(messages)


def load_safety():
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if hashlib.sha256(DATASET.read_bytes()).hexdigest()!=manifest['sha256']:raise ValueError('safety dataset SHA mismatch')
    rows=[]
    for line in DATASET.read_text(encoding='utf-8').splitlines():
        raw=json.loads(line)
        RouteDecision(intent=raw['expected_intent'],selected_agents=raw['expected_agents'],reason=raw['reason'])
        row=dict(raw);query=row.pop('query');reason=row.pop('reason');category=row.pop('category')
        row.update(user_query=query,expected_tools=[AGENT_TO_TOOL[a] for a in raw['expected_agents']],expected_status='unsupported' if not raw['expected_agents'] else 'completed',tags=[category])
        row=Case.model_validate(row).model_dump();row.update(category=category,annotation_reason=reason)
        rows.append(row)
    if len(rows)!=manifest['cases'] or len({r['case_id'] for r in rows})!=len(rows):raise ValueError('safety case count mismatch')
    return rows,manifest


def safety_metrics(rows):
    supported=[r for r in rows if r['expected_intent']!='unsupported']
    rejected=sum(r.get('predicted_intent')=='unsupported' for r in supported)
    return dict(false_rejection_count=rejected,supported_denominator=len(supported),
                false_rejection_rate=rejected/len(supported) if supported else None,
                supported_model_failures=sum(not r.get('route_received') for r in supported),
                unsupported_tool_calls=sum(len(r['actual_tools']) for r in rows if r['expected_intent']=='unsupported'),
                unsupported_completed=sum(r['status']=='completed' for r in rows if r['expected_intent']=='unsupported'))
