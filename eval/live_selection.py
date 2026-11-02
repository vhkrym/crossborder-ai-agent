"""Frozen live-run selection and logical-call budget (no network at import)."""
import hashlib
import json
from pathlib import Path
from eval.common import load_cases, dataset_metadata


def load_selection(path, dataset_path):
    path=Path(path)
    expected=path.with_suffix('.sha256').read_text(encoding='utf-8').split()[0]
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=expected:raise ValueError('selection SHA-256 mismatch')
    selection=json.loads(path.read_text(encoding='utf-8'))
    version,data_hash=dataset_metadata(dataset_path)
    if (selection['dataset_version'],selection['dataset_sha256'])!=(version,data_hash):
        raise ValueError('selection dataset mismatch')
    ids=selection['selected_case_ids']
    if not 1<=len(ids)<=15 or len(set(ids))!=len(ids):raise ValueError('selection must contain 1..15 unique cases')
    cases={c['case_id']:c for c in load_cases(dataset_path,case_ids=ids)}
    return [cases[i] for i in ids],digest


class CallBudget:
    """Sequential hard ceiling on delegated invoke calls; not a token/cost cap."""
    def __init__(self,llm,limit):
        if not 1<=limit<=75:raise ValueError('logical call budget must be 1..75')
        self.llm=llm;self.limit=limit;self.calls=0

    def invoke(self,messages):
        if self.calls>=self.limit:raise RuntimeError('evaluation_call_budget_exhausted')
        self.calls+=1
        return self.llm.invoke(messages)
