import subprocess
import sys
from types import SimpleNamespace
from langchain_core.messages import SystemMessage,HumanMessage
import pytest
from eval.common import ROOT,ScriptedLLM,isolated_database,run_case,write_report
from eval.safety import load_safety,PromptVariant,production_prompt,prompt_config,safety_metrics,DATASET


def test_safety_labels_and_frozen_prompts():
    cases,manifest=load_safety()
    assert len(cases)==36 and len({c['user_query'] for c in cases})==36
    assert len(manifest['proposed_live_panel'])==12
    assert prompt_config('baseline')[0]==production_prompt()
    assert prompt_config('candidate')[1]!=prompt_config('baseline')[1]
    assert sum(c['expected_intent']=='unsupported' for c in cases)==20


def test_prompt_adapter_only_changes_supervisor():
    captured=[]
    llm=SimpleNamespace(invoke=lambda messages:captured.append(messages))
    prefix=production_prompt();suffix=' Return only valid JSON matching: {"schema":"unchanged"}'
    human=HumanMessage(content='untrusted query')
    PromptVariant(llm,'baseline').invoke([SystemMessage(content=prefix+suffix),human])
    assert captured[-1][0].content==prefix+suffix
    PromptVariant(llm,'candidate').invoke([SystemMessage(content=prefix+suffix),human])
    assert captured[-1][0].content==prompt_config('candidate')[0]+suffix
    assert captured[-1][1] is human
    expert=SystemMessage(content='You are advertising specialist. Return only valid JSON matching: {}')
    PromptVariant(llm,'candidate').invoke([expert,human])
    assert captured[-1][0] is expert


@pytest.mark.parametrize('variant',['baseline','candidate'])
def test_safety_oracle_graph_contracts(variant):
    cases,_=load_safety()
    with isolated_database() as factory:
        for case in cases:
            result=run_case(case,PromptVariant(ScriptedLLM(case),variant),factory)
            assert result['status']==case['expected_status']
            assert result['scope_integrity'] is True and result['tool_violations']==0
            if case['expected_intent']=='unsupported':assert result['actual_tools']==[] and result['status']!='completed'
            else:assert result['evidence_valid'] is True


def test_live_mode_requires_opt_in():
    result=subprocess.run([sys.executable,str(ROOT/'eval/run_safety.py'),'--mode','live'],capture_output=True,text=True)
    assert result.returncode!=0 and 'requires --allow-real-api' in result.stderr


def test_safety_failures_stay_in_denominator_and_do_not_leak(tmp_path):
    case=load_safety()[0][5]
    secret='sk-safety-test-secret-do-not-save'
    def broken(messages):raise RuntimeError(secret)
    with isolated_database() as factory:
        row=run_case(case,PromptVariant(SimpleNamespace(invoke=broken),'candidate'),factory)
    report=write_report([row],tmp_path,'offline',dataset_path=DATASET)
    assert row['status']=='failed' and report['metrics']['cases']==1
    assert report['dataset_version']=='safety-routing-v1'
    assert safety_metrics([row])['supported_model_failures']==1
    assert safety_metrics([row])['false_rejection_rate']==0
    assert all(secret not in p.read_text(encoding='utf-8') for p in tmp_path.iterdir())
