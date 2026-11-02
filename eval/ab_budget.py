"""Shared sequential A/B budget: returned usage soft stop, not a billing cap."""
from datetime import datetime,timezone


class BudgetStopped(RuntimeError):
    pass


class SharedBudget:
    def __init__(self,max_calls=120,token_threshold=400000):
        if not 1<=max_calls<=120 or not 1<=token_threshold<=400000:raise ValueError('invalid budget')
        self.max_calls=max_calls;self.token_threshold=token_threshold
        self.calls=0;self.input_tokens=0;self.output_tokens=0
        self.stop_reason=None;self.records=[]

    def snapshot(self):
        return dict(logical_calls=self.calls,input_tokens=self.input_tokens,output_tokens=self.output_tokens,
                    returned_tokens=self.input_tokens+self.output_tokens,usage_complete=all(r['usage_known'] for r in self.records),
                    stop_reason=self.stop_reason,max_calls=self.max_calls,token_soft_threshold=self.token_threshold)

    def invoke(self,llm,messages,case_id,variant):
        if self.stop_reason:raise BudgetStopped(self.stop_reason)
        if self.calls>=self.max_calls:
            self.stop_reason='call_limit';raise BudgetStopped(self.stop_reason)
        if self.input_tokens+self.output_tokens>=self.token_threshold:
            self.stop_reason='token_soft_threshold';raise BudgetStopped(self.stop_reason)
        self.calls+=1
        record=dict(call_index=self.calls,case_id=case_id,variant=variant,started_at=datetime.now(timezone.utc).isoformat(),
                    input_tokens=None,output_tokens=None,usage_known=False,error_code=None)
        self.records.append(record)
        try:
            response=llm.invoke(messages)
        except Exception as exc:
            code='api_rate_or_quota' if getattr(exc,'status_code',None)==429 else 'api_timeout' if isinstance(exc,TimeoutError) or type(exc).__name__=='APITimeoutError' else 'api_error'
            self.stop_reason=code;record['error_code']=code
            raise BudgetStopped(code) from None
        finally:record['finished_at']=datetime.now(timezone.utc).isoformat()
        usage=getattr(response,'usage_metadata',None) or {}
        metadata=getattr(response,'response_metadata',None) or {}
        if not isinstance(usage,dict):usage={}
        if not isinstance(metadata,dict):metadata={}
        legacy=metadata.get('token_usage') or {}
        if not isinstance(legacy,dict):legacy={}
        incoming=usage.get('input_tokens',legacy.get('prompt_tokens'))
        outgoing=usage.get('output_tokens',legacy.get('completion_tokens'))
        valid=lambda x:isinstance(x,int) and not isinstance(x,bool) and x>=0
        record.update(input_tokens=incoming if valid(incoming) else None,output_tokens=outgoing if valid(outgoing) else None)
        if not valid(incoming) or not valid(outgoing):
            self.stop_reason='usage_missing_or_invalid'
        else:
            record['usage_known']=True;self.input_tokens+=incoming;self.output_tokens+=outgoing
            if self.input_tokens+self.output_tokens>=self.token_threshold:self.stop_reason='token_soft_threshold'
        if self.calls>=self.max_calls and self.stop_reason is None:self.stop_reason='call_limit'
        return response


class BudgetedArm:
    def __init__(self,budget,llm,case_id,variant):self.budget=budget;self.llm=llm;self.case_id=case_id;self.variant=variant
    def invoke(self,messages):return self.budget.invoke(self.llm,messages,self.case_id,self.variant)
