import sys,json
from pathlib import Path
from types import SimpleNamespace
from decimal import Decimal
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from eval.metrics import summarize
from eval.common import load_cases,ScriptedLLM,ObservedLLM,isolated_database,run_case,write_report

def row(**kwargs):
    return dict(case_id='test',expected_intent='mixed',expected_agents=['profit','advertising'],expected_tools=['analyze_profit','analyze_advertising'],expected_status='completed',route_received=True,predicted_agents=['advertising','profit'],predicted_intent='mixed',actual_tools=['analyze_advertising','analyze_profit'],status='completed',errors=[],latency_seconds=1,evidence_valid=True,**kwargs)

def test_sets_order_and_partial_matching():
    r=row();assert summarize([r])['agent_set_exact_match']==1
    r['predicted_agents']=['profit'];scores=summarize([r]);assert scores['agent_micro']['precision']==1 and scores['agent_micro']['recall']==.5 and scores['agent_micro']['f1']==pytest.approx(2/3)

def test_unsupported_zero_and_failures_not_dropped():
    assert summarize([])['agent_set_exact_match'] is None
    r=row();r.update(expected_intent='unsupported',expected_agents=[],expected_tools=[],predicted_agents=[],predicted_intent='unsupported',actual_tools=[],status='unsupported')
    assert summarize([r])['unsupported']['precision']==1
    r.update(predicted_intent=None,route_received=False,status='failed',errors=['llm_timeout'],model_call_failures=1)
    m=summarize([r]);assert m['cases']==1 and m['agent_set_exact_match']==0 and m['unsupported']['recall']==0 and m['model_call_failures']==1

@pytest.mark.parametrize('fault',['timeout','api','json'])
def test_graph_model_errors(fault):
    case=load_cases(case_ids=['profit-02'])[0]
    with isolated_database() as f:r=run_case(case,ScriptedLLM(case,fault),f)
    assert r['status']=='failed' and 'model_error' in r['error_categories'] and 'SECRET' not in json.dumps(r)

def test_usage_and_absent_usage():
    observed=ObservedLLM(SimpleNamespace(invoke=lambda _:SimpleNamespace(content='{}')));observed.invoke([])
    assert observed.usage[0]['input_tokens'] is None
    observed=ObservedLLM(SimpleNamespace(invoke=lambda _:SimpleNamespace(usage_metadata={'input_tokens':12,'output_tokens':3})));observed.invoke([])
    r=row();r['usage']=observed.usage;assert summarize([r])['token_usage']['input_tokens']==12

def test_dataset_report_and_no_writes(tmp_path):
    cases=load_cases();assert len(cases)==60
    assert len({r['case_id'] for r in cases})==60
    with isolated_database() as f:r=run_case(cases[0],ScriptedLLM(cases[0]),f)
    report=write_report([r],tmp_path,'offline');assert (tmp_path/'report.json').is_file() and (tmp_path/'report.md').is_file()
    assert r['state_transitions']==['pending','running','completed']
    assert r['nodes'][0]=='supervisor' and r['nodes'][-1]=='validate'
    assert report['dataset_sha256']
    assert report['metrics']['token_usage']['input_tokens'] is None

def test_numeric_mutation_and_fault_contracts():
    from eval.run_offline import contract_checks
    with isolated_database() as f:checks=contract_checks(load_cases(case_ids=['profit-02'])[0],f)
    assert all(c['passed'] for c in checks)

def test_live_default_disabled_without_network():
    import subprocess
    script=Path(__file__).resolve().parents[2]/'eval/run_live.py'
    r=subprocess.run([sys.executable,str(script),'--limit','1'],capture_output=True,text=True)
    assert r.returncode!=0 and 'requires --allow-real-api' in r.stderr


def test_reports_do_not_store_provider_exception_secrets(tmp_path):
    secret='sk-evaluation-secret-never-save'
    class Broken:
        def invoke(self,messages):raise RuntimeError(secret)
    case=load_cases(case_ids=['profit-02'])[0]
    with isolated_database() as f:r=run_case(case,Broken(),f)
    write_report([r],tmp_path,'offline')
    assert all(secret not in p.read_text(encoding='utf-8') for p in tmp_path.iterdir())
    assert r['model_call_failures']==1
