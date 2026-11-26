"""Bounded stateless continuation and small response reuse for strategic screening.

No State/model/source graph is cached. Signed cursors carry only screened IDs and
bind to the current tenant, evidence identities, generation, and instructions.
"""
from collections import OrderedDict
import base64
import hashlib
import hmac
import json
import logging
import secrets
import sys
from threading import RLock
from time import monotonic

from .strategic_discovery import build_strategic_discovery
from .trade_intrinsic_evidence import published_horizons_match_runtime

MAX_TOTAL_SCREENS = 80
SHORTLIST_TARGET = 4
MAX_FINALIST_CONFIRMATIONS = 8
_GROUPS=("preliminary_fit","priority_tradeoff","priority_concern","needs_evidence")
_logger=logging.getLogger("fsffl.product.performance")


def _bytes(value):
    """Account a bounded plain response graph without serializing another copy."""
    seen = set()
    def size(x):
        if id(x) in seen:
            return 0
        seen.add(id(x))
        return sys.getsizeof(x) + (sum(size(k)+size(v) for k,v in x.items()) if isinstance(x,dict)
            else sum(size(v) for v in x) if isinstance(x,(tuple,list)) else 0)
    return size(value)


class ProgressiveDiscovery:
    def __init__(self, *, clock=monotonic, max_entries=4, max_bytes=4*1024*1024, finalist_evaluator=None):
        self.clock, self.max_entries, self.max_bytes = clock, max_entries, max_bytes
        self.secret = secrets.token_bytes(32)
        self.lock = RLock()
        self.cache = OrderedDict()
        self.cache_bytes = 0
        self.inflight = False
        self.finalist_evaluator = finalist_evaluator

    def _scope(self, runtime, request, read):
        inputs = request.model_dump(mode='json', exclude={'continuation_token'})
        source = dict(read.source) if read is not None else None
        coordinates = [runtime.user_id, runtime.selected_team_id, runtime.league_state.state_id,
            runtime.publication_generation_id, id(runtime.forecast_evidence), id(runtime.simulation_analytics),
            id(runtime.value_evidence), inputs, source]
        return hashlib.sha256(json.dumps(coordinates,sort_keys=True,default=str).encode()).hexdigest()

    def _encode(self, payload):
        encoded=base64.urlsafe_b64encode(json.dumps(payload,separators=(',',':')).encode()).decode()
        return encoded+'.'+hmac.new(self.secret,encoded.encode(),hashlib.sha256).hexdigest()

    def _decode(self, token, scope):
        try:
            encoded, signature = token.split('.')
            expected=hmac.new(self.secret,encoded.encode(),hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected,signature):
                raise ValueError()
            payload=json.loads(base64.urlsafe_b64decode(encoded))
            ids=payload['screened']
            if (payload.get('version') != 1 or payload['scope'] != scope or not 0 <= self.clock()-payload['started'] <= 600
                or not isinstance(ids,list) or len(ids)>MAX_TOTAL_SCREENS or len(ids)!=len(set(ids))
                or any(not isinstance(i,str) or not i or len(i)>1024 for i in ids)
                or not set(payload['fits']) <= set(ids)
                or not isinstance(payload.get('confirmations',0),int)
                or not 0<=payload.get('confirmations',0)<=MAX_FINALIST_CONFIRMATIONS
                or not isinstance(payload.get('confirmation_targets',[]),list)
                or len(payload.get('confirmation_targets',[]))>MAX_FINALIST_CONFIRMATIONS
                or not isinstance(payload.get('quality_receipts',[]),list)
                or len(payload.get('quality_receipts',[]))>MAX_TOTAL_SCREENS
                or any(not isinstance(r,dict) or r.get('point_id') not in ids for r in payload.get('quality_receipts',[]))):
                raise ValueError()
            return payload
        except (ValueError,TypeError,KeyError,UnicodeError,OverflowError):
            raise ValueError('Search expired or its evidence/settings changed. Start a new search.') from None

    def build(self, runtime, request, *, read=None):
        if read is not None and not published_horizons_match_runtime(runtime,read):
            read=None
        scope=self._scope(runtime,request,read)
        prior=self._decode(request.continuation_token,scope) if request.continuation_token else {
            'version':1,'scope':scope,'started':self.clock(),'screened':[],'fits':[],'repair':False,'batches':0}
        cache_key=(scope,request.continuation_token)
        now=self.clock()
        with self.lock:
            for key,(created,_,size) in list(self.cache.items()):
                if now-created>300:
                    self.cache_bytes-=size;del self.cache[key]
            if cache_key in self.cache:
                self.cache.move_to_end(cache_key)
                result=self.cache[cache_key][1]
                return {**result,'diagnostics':{**result['diagnostics'],'changed_state_simulation_calls':0,'finalist_confirmation_attempts':0},'search_progress':{**result['search_progress'],'cache_hit':True}}
        with self.lock:
            if self.inflight:
                raise ValueError('A discovery batch is already running. Retry shortly; completed results are preserved.')
            self.inflight=True
        try:
            return self._build_batch(runtime,request,read,scope,prior,cache_key,now)
        finally:
            with self.lock:
                self.inflight=False

    def _build_batch(self,runtime,request,read,scope,prior,cache_key,now):
        remaining=MAX_TOTAL_SCREENS-len(prior['screened'])
        if remaining<=0:
            raise ValueError('This search reached its screening limit. Start a new search with different constraints.')
        limited=request.model_copy(update={'evaluation_budget':min(request.evaluation_budget,remaining)})
        result=build_strategic_discovery(runtime,limited,read=read,
            previously_screened=prior['screened'],feedback_already_attempted=prior['repair'])
        rows=result['candidate_packages']
        from fsffl.opportunity.shortlist_quality import curate_shortlist,shortlist_receipt,inferred_timeline_choice
        prior_rows=prior.get('quality_receipts',[])
        combined=prior_rows+rows
        from fsffl.trade_decision import live_bounded_materiality_policy
        try:
            market_tolerance=live_bounded_materiality_policy(as_of=runtime.league_state.as_of).economic.mean_value_abs
        except (ValueError,AttributeError):
            market_tolerance=0.0
        curate_shortlist(combined,market_tolerance=market_tolerance)
        confirmations=prior.get('confirmations',0)
        confirmation_targets=list(prior.get('confirmation_targets',[]))
        confirmation_attempts=0
        new_simulations=0
        if self.finalist_evaluator is not None:
            from fsffl.opportunity.confirmation_quality import current_required_teams
            choices=sorted((r for r in combined if r['shortlist_quality']['status'] in ('shortlist','strategic_tradeoff')
                and current_required_teams(r) and (r.get('screen_confirmation') or {}).get('status') not in ('verified','not_worthwhile','review','unavailable')),
                key=lambda r:r['shortlist_quality'].get('rank',999))
            if choices and confirmations<MAX_FINALIST_CONFIRMATIONS:
                target=lambda r:sorted(a['asset_ref'] for a in r.get('receive',()))
                fresh=[r for r in choices if target(r) not in confirmation_targets]
                row=(fresh or choices)[0]
                confirmation_attempts=1
                try:
                    row['screen_confirmation']=self.finalist_evaluator(runtime,row,read,request.search_instructions)
                except Exception as exc:
                    _logger.warning('Discovery finalist unavailable error_type=%s',type(exc).__name__)
                    row['screen_confirmation']={'status':'unavailable','reason':'full_check_unavailable'}
                proof=row['screen_confirmation']
                if proof.get('status')!='deferred':
                    confirmations+=1;confirmation_targets.append(target(row))
                new_simulations=int(proof.get('simulation_count')==50_000 and not proof.get('cache_hit',False) and proof.get('execution_mode')!='reuse_competitive_simulation')
            curate_shortlist(combined,market_tolerance=market_tolerance,require_current_confirmation=True)
        quality_receipts=[shortlist_receipt(r) for r in combined if (r.get('display_context') or {}).get('group')=='preliminary_fit' or inferred_timeline_choice(r)]
        attempted=[r['point_id'] for r in rows if r.get('evaluation_kind') in ('root','repair')]
        screened=list(dict.fromkeys([*prior['screened'],*attempted]))
        fits=list(dict.fromkeys(r['point_id'] for r in combined if r['shortlist_quality']['status'] in ('shortlist','strategic_tradeoff')))
        comparison={label:{g:int((prior.get('priority_comparison',{}).get(label) or {}).get(g,0)) for g in _GROUPS}
            for label in ('before','after')}
        gates=dict(prior.get('limiting_gates',{}))
        prior_ids=set(prior['screened'])
        new_rows={r['point_id']:r for r in rows if r.get('evaluation_kind') in ('root','repair')
            and r['point_id'] not in prior_ids}
        for row in new_rows.values():
            display=row.get('display_context') or {}
            gate=display.get('limiting_gate','unspecified')
            gates[gate]=gates.get(gate,0)+1
            after=display.get('group','needs_evidence')
            before=display.get('legacy_group',after)
            comparison['before'][before if before in _GROUPS else 'needs_evidence']+=1
            comparison['after'][after if after in _GROUPS else 'needs_evidence']+=1
        _logger.info('FSFFL discovery priority comparison scope=%s screened=%s before=%s after=%s',
            scope[:12],len(screened),comparison['before'],comparison['after'])
        _logger.info('FSFFL discovery priority gates scope=%s gates=%s',scope[:12],gates)
        pending=result['diagnostics']['unexamined_pool_count']
        has_more=bool(attempted and pending and len(screened)<MAX_TOTAL_SCREENS)
        goals=(result.get('priority_context') or {}).get('objectives') or ()
        minimum_screens=min(24,8*max(1,len(goals)))
        reason=('screening_disabled' if request.evaluation_budget==0 else 'screening_limit' if len(screened)>=MAX_TOTAL_SCREENS
            else 'pool_exhausted' if not has_more else 'shortlist_ready' if len(fits)>=SHORTLIST_TARGET and len(screened)>=minimum_screens else 'continue')
        payload={**prior,'screened':screened,'fits':fits,'quality_receipts':quality_receipts,'priority_comparison':comparison,'limiting_gates':gates,
            'confirmations':confirmations,'confirmation_targets':confirmation_targets,'repair':prior['repair'] or result['diagnostics']['repair_sequence_attempted'], 'batches':prior['batches']+1}
        result={**result,'diagnostics':{**result['diagnostics'],
                'finalist_confirmation_attempts':confirmation_attempts,'changed_state_simulation_calls':new_simulations,
                'maximum_finalist_confirmations_per_batch':1},
            'confirmation_updates':{r['point_id']:r['screen_confirmation'] for r in combined if r.get('screen_confirmation')},
            'shortlist_updates':{r['point_id']:r['shortlist_quality'] for r in combined},'search_progress':{'screens_this_batch':len(attempted),'total_screened':len(screened),
            'priority_comparison':comparison,'limiting_gates':gates,
            'priority_tradeoff_count':comparison['after']['priority_tradeoff'],
            'max_total_screens':MAX_TOTAL_SCREENS,'finalist_confirmations':confirmations,'max_finalist_confirmations':MAX_FINALIST_CONFIRMATIONS,'minimum_direction_screens':minimum_screens,'preliminary_fit_count':sum(r['shortlist_quality']['status']=='shortlist' for r in combined),'shortlisted_choice_count':len(fits),'shortlist_target':SHORTLIST_TARGET,
            'model_version':'bounded-discovery-continuation-v5:goal-branch-coverage','batch_count':payload['batches'],'stop_reason':reason,'cache_hit':False,
            'next_token':self._encode(payload) if has_more else None,
            'interpretation':'Bounded preliminary discovery with at most one existing Trade Center confirmation per batch; future asset contribution is not franchise utility or owner acceptance.'}}
        size=_bytes(result)+_bytes(cache_key)
        if size<=self.max_bytes:
            with self.lock:
                previous=self.cache.pop(cache_key,None)
                if previous:self.cache_bytes-=previous[2]
                while self.cache and (len(self.cache)>=self.max_entries or self.cache_bytes+size>self.max_bytes):
                    _,(_,_,old_size)=self.cache.popitem(last=False);self.cache_bytes-=old_size
                self.cache[cache_key]=(now,result,size);self.cache_bytes+=size
        return result
