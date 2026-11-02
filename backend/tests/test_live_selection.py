import hashlib
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from eval.common import ROOT, DATASET_V2, isolated_database
from eval.live_selection import load_selection, CallBudget


def test_frozen_selection_distribution_and_previous_exclusion():
    path=ROOT/'eval/datasets/live_stratified_15.json'
    cases,digest=load_selection(path,DATASET_V2)
    assert len(cases)==15
    assert digest==hashlib.sha256(path.read_bytes()).hexdigest()
    selection=json.loads(path.read_text(encoding='utf-8'))
    assert not set(selection['selected_case_ids'])&set(selection['previously_evaluated_case_ids'])
    assert {c['store_id'] for c in cases}=={1,2}
    for name in ('profit','advertising','inventory'):
        assert sum(c['expected_intent']==name for c in cases)==2
    for pair in ({'profit','advertising'},{'profit','inventory'},{'advertising','inventory'}):
        assert sum(set(c['expected_agents'])==pair for c in cases)==2
    assert sum(len(c['expected_agents'])==3 for c in cases)==2
    assert sum(c['expected_intent']=='unsupported' for c in cases)==1
    assert {'dual-01','dual-09','dual-12','profit-08'}.issubset(selection['selected_case_ids'])


def test_selection_tamper_and_maximum(tmp_path):
    original=ROOT/'eval/datasets/live_stratified_15.json'
    p=tmp_path/'selection.json';p.write_bytes(original.read_bytes()+b' ')
    p.with_suffix('.sha256').write_bytes(original.with_suffix('.sha256').read_bytes())
    with pytest.raises(ValueError,match='SHA-256'):load_selection(p,DATASET_V2)
    data=json.loads(original.read_text(encoding='utf-8'))
    data['selected_case_ids'].append('profit-01')
    p.write_text(json.dumps(data),encoding='utf-8')
    p.with_suffix('.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest(),encoding='utf-8')
    with pytest.raises(ValueError,match='1..15'):load_selection(p,DATASET_V2)


def test_logical_call_ceiling_includes_failures_without_retry():
    attempts=[]
    def invoke(messages):
        attempts.append(messages)
        raise TimeoutError('do not persist')
    budget=CallBudget(SimpleNamespace(invoke=invoke),1)
    with pytest.raises(TimeoutError):budget.invoke([])
    with pytest.raises(RuntimeError,match='budget_exhausted'):budget.invoke([])
    assert len(attempts)==budget.calls==1
    with pytest.raises(ValueError):CallBudget(None,76)


def test_evaluation_database_rejects_write_sql():
    with isolated_database() as factory:
        with factory() as session:
            with pytest.raises(OperationalError,match='readonly'):
                session.execute(text('DELETE FROM stores WHERE 1=0'))
            session.rollback()
