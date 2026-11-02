import hashlib
import json
from pathlib import Path

import pytest
from eval.common import (DATASET, DATASET_V2, load_cases, dataset_metadata,
                         check_scope, run_case, ScriptedLLM, isolated_database)
from eval.metrics import summarize
from app.agents.supervisor_state import SupervisorState


def result(agents, tools, case_id='dual-01'):
    case=load_cases(DATASET_V2,case_ids=[case_id])[0]
    return dict(case,route_received=True,predicted_agents=agents,actual_tools=tools,
                predicted_intent='mixed' if len(agents)>1 else agents[0] if agents else 'unsupported',
                status='completed',errors=[],latency_seconds=1,evidence_valid=True)


def test_original_and_alternate_dual_routes():
    original=result(['advertising','profit'],['analyze_advertising','analyze_profit'])
    alternate=result(['profit'],['analyze_profit'])
    scores=summarize([original,alternate])
    assert scores['strict_agent_set_exact_match']==.5
    assert scores['acceptable_agent_set_match']==1
    assert scores['strict_tool_set_exact_match']==.5
    assert scores['acceptable_tool_set_match']==1
    assert scores['intent_exact_match']==.5
    assert scores['answer_completeness']['value'] is None


@pytest.mark.parametrize('agents,tools,case_id,accepted',[
    (['inventory'],['analyze_inventory'],'dual-09',1),
    (['inventory'],['analyze_inventory'],'dual-01',0),
    (['inventory'],['analyze_inventory'],'dual-12',0),
    (['inventory','advertising'],['analyze_inventory','analyze_advertising'],'dual-12',1),
])
def test_only_predefined_alternatives(agents,tools,case_id,accepted):
    m=summarize([result(agents,tools,case_id)])
    assert m['acceptable_agent_set_match']==accepted
    assert m['acceptable_tool_set_match']==accepted


def test_tools_are_independent_and_unsupported_requires_empty():
    r=result(['profit'],['analyze_inventory'])
    m=summarize([r]);assert m['acceptable_agent_set_match']==1 and m['acceptable_tool_set_match']==0
    r=result([],[],'unsupported-01');r['status']='unsupported'
    assert summarize([r])['acceptable_agent_set_match']==1
    r.update(predicted_agents=['profit'],actual_tools=['analyze_profit'],acceptable_agent_sets=[[],['profit']])
    assert summarize([r])['acceptable_agent_set_match']==0


def test_version_integrity_and_exact_diff():
    v1=load_cases();v2=load_cases(DATASET_V2)
    assert len(v1)==len(v2)==60
    assert [r['case_id'] for r in v1]==[r['case_id'] for r in v2]
    changes=[]
    for a,b in zip(v1,v2):
        if a['acceptable_agent_sets']!=b['acceptable_agent_sets']:changes.append(a['case_id'])
        assert {k:v for k,v in a.items() if k!='acceptable_agent_sets'}=={k:v for k,v in b.items() if k!='acceptable_agent_sets'}
    assert changes==['dual-01','dual-09']
    assert dataset_metadata(DATASET)[1]=='e2e8970bd1e245bf82fcfd431da08f6e2aaeae2b65ba493737481b6ee630375f'
    assert dataset_metadata(DATASET_V2)[0]=='supervisor-v2'


def test_sha_tampering_is_rejected(tmp_path,monkeypatch):
    import eval.common as common
    altered=tmp_path/'altered.jsonl';altered.write_bytes(DATASET_V2.read_bytes()+b'\n')
    monkeypatch.setattr(common,'DATASET_V2',altered)
    with pytest.raises(ValueError,match='dataset changed'):load_cases(altered)


def test_scope_uses_original_input_not_final_mutation():
    case=load_cases(case_ids=['profit-08'])[0]
    with isolated_database() as factory:
        row=run_case(case,ScriptedLLM(case),factory)
    assert row['scope_integrity'] is True
    state=SupervisorState(task_id='test',**{k:case[k] for k in ('store_id','user_query','start_date','end_date','selected_sku')})
    for key,value in [('store_id',2),('start_date','2026-04-01'),('end_date','2026-06-30'),('selected_sku','OTHER')]:
        assert check_scope(case,state.model_copy(update={key:value})) is False


def test_legacy_results_and_missing_scope_are_not_assumed_pass():
    r=result(['profit','advertising'],['analyze_profit','analyze_advertising'])
    r.pop('acceptable_agent_sets')
    m=summarize([r]);assert m['acceptable_agent_set_match']==m['agent_set_exact_match']==1
    assert m['scope_integrity']['unassessed']==1
    assert m['scope_integrity']['pass_rate']==0
    r['evidence_valid']=False;r['status']='completed'
    assert summarize([r])['evidence_grounding']['failed']==1
    assert summarize([r])['answer_completeness']['status']=='not_evaluated'
