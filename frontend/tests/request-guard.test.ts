import {test} from 'node:test'
import assert from 'node:assert/strict'
import {createRequestGuard,fetchDecisionBundle} from '../src/requestGuard.ts'
test('deep link only ID uses authoritative store returned by server',async()=>{let seen:number|undefined;const result=await fetchDecisionBundle('id',async()=>({proposal_id:'id',store_id:17}),async(id,store)=>{seen=store;return ['audit']});assert.equal(seen,17);assert.deepEqual(result.audit,['audit'])})
test('late result cannot overwrite newer selection or unmounted page',()=>{const guard=createRequestGuard();const old=guard.begin();const next=guard.begin();assert.equal(guard.current(old),false);assert.equal(guard.current(next),true);guard.invalidate();assert.equal(guard.current(next),false)})

test('out of order async results retain latest store selection',async()=>{const guard=createRequestGuard();let resolveOld!:(value:string)=>void;const oldResult=new Promise<string>(resolve=>{resolveOld=resolve});let visible='';const old=guard.begin();const pending=oldResult.then(value=>{if(guard.current(old))visible=value});const current=guard.begin();if(guard.current(current))visible='store-2';resolveOld('store-1');await pending;assert.equal(visible,'store-2')})
