"""Metrics do not infer model quality from prescribed offline routes."""
from statistics import mean
from app.agents.supervisor_graph import AGENT_TO_TOOL

def acceptable_sets(row):
    candidates=row.get('acceptable_agent_sets') or [row['expected_agents']]
    result=[]
    for agents in candidates:
        if len(agents)!=len(set(agents)) or any(a not in AGENT_TO_TOOL for a in agents):continue
        if (not agents)!=(row['expected_intent']=='unsupported'):continue
        result.append(set(agents))
    return result

def independent_score(rows,key):
    passed=sum(r.get(key) is True for r in rows)
    return dict(passed=passed,failed=sum(r.get(key) is False for r in rows),unassessed=sum(r.get(key) is None for r in rows),denominator=len(rows),pass_rate=divide(passed,len(rows)))


def divide(a,b):return a/b if b else None

def percentile(values,p):
    if not values:return None
    values=sorted(values);position=(len(values)-1)*p;lo=int(position);hi=min(lo+1,len(values)-1)
    return values[lo]+(values[hi]-values[lo])*(position-lo)

def prf(tp,fp,fn):
    return dict(precision=divide(tp,tp+fp),recall=divide(tp,tp+fn),f1=divide(2*tp,2*tp+fp+fn))

def summarize(rows):
    n=len(rows);tp=fp=fn=0;per_agent={a:[0,0,0] for a in ('profit','advertising','inventory')}
    utp=ufp=ufn=0
    for row in rows:
        expected=set(row['expected_agents']);pred=set(row.get('predicted_agents',[]))
        tp+=len(expected&pred);fp+=len(pred-expected);fn+=len(expected-pred)
        for a,counts in per_agent.items():
            counts[0]+=int(a in expected and a in pred);counts[1]+=int(a not in expected and a in pred);counts[2]+=int(a in expected and a not in pred)
        expected_u=row['expected_intent']=='unsupported';pred_u=row.get('predicted_intent')=='unsupported'
        utp+=int(expected_u and pred_u);ufp+=int(not expected_u and pred_u);ufn+=int(expected_u and not pred_u)
    evidence_rows=[r for r in rows if r['expected_intent']!='unsupported']
    known=[call for r in rows for call in r.get('usage',[]) if call.get('input_tokens') is not None and call.get('output_tokens') is not None]
    calls=sum(len(r.get('usage',[])) for r in rows)
    agent_scores={a:prf(*counts) for a,counts in per_agent.items()}
    extra=dict(strict_agent_set_exact_match=divide(sum(bool(r.get('route_received')) and set(r.get('predicted_agents',[]))==set(r['expected_agents']) for r in rows),n),acceptable_agent_set_match=divide(sum(bool(r.get('route_received')) and set(r.get('predicted_agents',[])) in acceptable_sets(r) for r in rows),n),strict_tool_set_exact_match=divide(sum(set(r.get('actual_tools',[]))==set(r['expected_tools']) for r in rows),n),acceptable_tool_set_match=divide(sum(set(r.get('actual_tools',[])) in [{AGENT_TO_TOOL[a] for a in agents} for agents in acceptable_sets(r)] for r in rows),n),scope_integrity=independent_score(rows,'scope_integrity'),evidence_grounding=independent_score(evidence_rows,'evidence_valid'),answer_completeness=dict(status='not_evaluated',value=None,denominator=n,reason='No reliable automatic completeness assessment; routing and completed are insufficient.'))
    return dict(**extra,error_categories={name:sum(name in r.get('error_categories',[]) for r in rows) for name in ('routing_error','tool_error','model_error','evidence_error')},cases=n,agent_set_exact_match=divide(sum(bool(r.get('route_received')) and set(r.get('predicted_agents',[]))==set(r['expected_agents']) for r in rows),n),intent_exact_match=divide(sum(r.get('predicted_intent')==r['expected_intent'] for r in rows),n),agent_micro=prf(tp,fp,fn),agent_macro_f1=mean([s['f1'] for s in agent_scores.values() if s['f1'] is not None]) if any(s['f1'] is not None for s in agent_scores.values()) else None,per_agent=agent_scores,tool_set_exact_match=divide(sum(set(r.get('actual_tools',[]))==set(r['expected_tools']) for r in rows),n),unsupported=prf(utp,ufp,ufn),workflow_success_rate=divide(sum(r.get('status') in ('completed','unsupported') and not r.get('errors') for r in rows),n),expected_status_match_rate=divide(sum(r.get('status')==r['expected_status'] for r in rows),n),evidence_validation_pass_rate=divide(sum(r.get('evidence_valid') is True for r in evidence_rows),len(evidence_rows)),evidence_validation_failures=sum(r.get('evidence_valid') is False for r in rows),unsupported_numeric_assertions=sum(r.get('unsupported_numeric_assertions',0) for r in rows),tool_violations=sum(r.get('tool_violations',0) for r in rows),state_errors=sum(r.get('state_errors',0) for r in rows),model_call_failures=sum(r.get('model_call_failures',0) for r in rows),p50_seconds=percentile([r['latency_seconds'] for r in rows],.5),p95_seconds=percentile([r['latency_seconds'] for r in rows],.95),token_usage=dict(input_tokens=sum(x['input_tokens'] for x in known) if known else None,output_tokens=sum(x['output_tokens'] for x in known) if known else None,calls=calls,calls_with_usage=len(known),complete=(calls>0 and len(known)==calls)))
