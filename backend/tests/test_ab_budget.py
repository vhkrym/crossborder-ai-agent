import hashlib
import json
from types import SimpleNamespace
import pytest
from eval.ab_budget import SharedBudget,BudgetStopped,BudgetedArm
from eval.safety_ab import load_ab_selection,SELECTION,run_ab
from eval.common import ROOT


def response(incoming=3,outgoing=2):
    return SimpleNamespace(content='{}',usage_metadata={'input_tokens':incoming,'output_tokens':outgoing})


def test_shared_arms_stop_exact_threshold():
    calls=[]
    llm=SimpleNamespace(invoke=lambda m:(calls.append(m),response())[1])
    budget=SharedBudget(token_threshold=10)
    BudgetedArm(budget,llm,'case','baseline').invoke([])
    BudgetedArm(budget,llm,'case','candidate').invoke([])
    with pytest.raises(BudgetStopped):BudgetedArm(budget,llm,'next','baseline').invoke([])
    assert len(calls)==budget.calls==2
    assert budget.snapshot()['returned_tokens']==10 and budget.stop_reason=='token_soft_threshold'
    assert [r['variant'] for r in budget.records]==['baseline','candidate']


def test_real_default_soft_threshold_allows_last_response_overshoot():
    budget=SharedBudget();llm=SimpleNamespace(invoke=lambda _:response(399999,2))
    budget.invoke(llm,[],'case','baseline')
    assert budget.snapshot()['returned_tokens']==400001
    with pytest.raises(BudgetStopped):budget.invoke(llm,[],'case','candidate')
    assert budget.calls==1


@pytest.mark.parametrize('usage',[None,['invalid'],{'input_tokens':1}, {'input_tokens':-1,'output_tokens':2}, {'input_tokens':True,'output_tokens':2}])
def test_unknown_usage_stops_instead_of_assuming_zero(usage):
    budget=SharedBudget()
    llm=SimpleNamespace(invoke=lambda _:SimpleNamespace(content='{}',usage_metadata=usage))
    budget.invoke(llm,[],'case','baseline')
    assert budget.stop_reason=='usage_missing_or_invalid'
    assert budget.snapshot()['usage_complete'] is False
    with pytest.raises(BudgetStopped):budget.invoke(llm,[],'case','candidate')
    assert budget.calls==1


def test_legacy_usage_and_total_120_call_limit():
    budget=SharedBudget()
    llm=SimpleNamespace(invoke=lambda _:SimpleNamespace(content='{}',response_metadata={'token_usage':{'prompt_tokens':1,'completion_tokens':1}}))
    for i in range(120):budget.invoke(llm,[],str(i),'baseline' if i%2 else 'candidate')
    with pytest.raises(BudgetStopped):budget.invoke(llm,[],'extra','candidate')
    assert budget.calls==120 and budget.snapshot()['returned_tokens']==240
    assert budget.stop_reason=='call_limit'


@pytest.mark.parametrize('error',[TimeoutError('secret'),RuntimeError('secret')])
def test_api_failure_stops_without_retry_or_secret(error):
    attempts=[]
    def fail(_):attempts.append(1);raise error
    budget=SharedBudget();llm=SimpleNamespace(invoke=fail)
    for _ in range(2):
        with pytest.raises(BudgetStopped):budget.invoke(llm,[],'case','baseline')
    assert len(attempts)==1 and budget.calls==1
    assert 'secret' not in json.dumps(budget.records)


def test_quota_error_stops_all_later_arms():
    class QuotaError(Exception):status_code=429
    def fail(_):raise QuotaError('do not store')
    budget=SharedBudget()
    with pytest.raises(BudgetStopped):budget.invoke(SimpleNamespace(invoke=fail),[],'case','baseline')
    assert budget.stop_reason=='api_rate_or_quota'
    with pytest.raises(BudgetStopped):budget.invoke(None,[],'case','candidate')
    assert budget.calls==1


def test_selection_resolves_11_plus_1_without_changes():
    cases,selection,digest=load_ab_selection()
    assert len(cases)==12 and hashlib.sha256(SELECTION.read_bytes()).hexdigest()==digest
    assert sum(c['source_provenance']['source_version']=='safety-routing-v1' for c in cases)==11
    known=[c for c in cases if c['source_provenance']['known_regression_case']]
    assert len(known)==1 and known[0]['case_id']=='unsupported-05'
    assert all(c['source_provenance']['independent_holdout'] is False for c in cases)


def test_selection_snapshot_tamper_even_with_new_checksum(tmp_path):
    data=json.loads(SELECTION.read_text(encoding='utf-8'))
    data['samples'][0]['trusted_input']['store_id']=999
    p=tmp_path/'selection.json';p.write_text(json.dumps(data),encoding='utf-8')
    p.with_suffix('.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest(),encoding='utf-8')
    with pytest.raises(ValueError,match='trusted input'):load_ab_selection(p)


def test_offline_paired_orchestration_never_builds_provider(tmp_path,monkeypatch):
    import app.agents.llm
    def forbidden(*a,**k):raise AssertionError('real provider constructed')
    monkeypatch.setattr(app.agents.llm,'create_llm',forbidden)
    results,budget=run_ab(tmp_path/'results','offline')
    assert len(results['baseline'])==len(results['candidate'])==12
    assert budget.calls==50 and budget.snapshot()['returned_tokens']==0
    data=json.loads((tmp_path/'results/paired_results.json').read_text(encoding='utf-8'))
    assert data['config']['fake'] is True
    assert all(p['baseline'] and p['candidate'] for p in data['pairs'])
    for a,b in zip(results['baseline'],results['candidate']):
        assert a['case_id']==b['case_id'] and a['source_provenance']['trusted_input']==b['source_provenance']['trusted_input']


def test_budget_stop_preserves_unexecuted_pair_slots(tmp_path,monkeypatch):
    import eval.safety_ab as ab
    monkeypatch.setattr(ab,'SharedBudget',lambda:SharedBudget(max_calls=1))
    results,budget=ab.run_ab(tmp_path/'results','offline')
    data=json.loads((tmp_path/'results/paired_results.json').read_text(encoding='utf-8'))
    assert len(results['baseline'])==1 and not results['candidate']
    assert len(data['pairs'])==12 and data['pairs'][0]['candidate'] is None
    assert data['budget']['stop_reason']=='call_limit'
    assert all(p['baseline'] is None and p['candidate'] is None for p in data['pairs'][1:])


def test_live_preflight_requires_model_and_blocks_drift_before_provider(tmp_path,monkeypatch):
    import app.agents.llm as provider
    def forbidden(*a,**k):raise AssertionError('provider must not be constructed')
    monkeypatch.setattr(provider,'create_llm',forbidden)
    with pytest.raises(ValueError,match='explicitly approved'):run_ab(tmp_path/'missing','live')
    settings=SimpleNamespace(llm_model='different-model')
    settings.model_copy=lambda **kwargs:settings
    monkeypatch.setattr(provider,'LLMSettings',lambda:settings)
    with pytest.raises(ValueError,match='differs from approved'):run_ab(tmp_path/'drift','live',expected_model='approved-model')
    assert not (tmp_path/'missing').exists() and not (tmp_path/'drift').exists()
