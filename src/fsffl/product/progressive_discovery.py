"""Bounded stateless continuation and small response reuse for strategic screening.

No State/model/source graph is cached. Signed cursors carry only screened IDs and
bind to the current tenant, evidence identities, generation, and instructions.
"""
from collections import OrderedDict
import base64
import hashlib
import hmac
import json
import secrets
import sys
from threading import RLock
from time import monotonic

from .strategic_discovery import build_strategic_discovery
from .trade_intrinsic_evidence import published_horizons_match_runtime

MAX_TOTAL_SCREENS = 32
SHORTLIST_TARGET = 4


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
    def __init__(self, *, clock=monotonic, max_entries=4, max_bytes=4*1024*1024):
        self.clock, self.max_entries, self.max_bytes = clock, max_entries, max_bytes
        self.secret = secrets.token_bytes(32)
        self.lock = RLock()
        self.cache = OrderedDict()
        self.cache_bytes = 0
        self.inflight = False

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
                or not set(payload['fits']) <= set(ids)):
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
                return {**result,'search_progress':{**result['search_progress'],'cache_hit':True}}
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
        attempted=[r['point_id'] for r in rows if r.get('evaluation_kind') in ('root','repair')]
        screened=list(dict.fromkeys([*prior['screened'],*attempted]))
        fits=list(dict.fromkeys([*prior['fits'],*(r['point_id'] for r in rows
            if (r.get('display_context') or {}).get('group')=='preliminary_fit')]))
        pending=result['diagnostics']['unexamined_pool_count']
        has_more=bool(attempted and pending and len(screened)<MAX_TOTAL_SCREENS)
        reason=('screening_disabled' if request.evaluation_budget==0 else 'screening_limit' if len(screened)>=MAX_TOTAL_SCREENS
            else 'pool_exhausted' if not has_more else 'shortlist_ready' if len(fits)>=SHORTLIST_TARGET else 'continue')
        payload={**prior,'screened':screened,'fits':fits,
            'repair':prior['repair'] or result['diagnostics']['repair_sequence_attempted'], 'batches':prior['batches']+1}
        result={**result,'search_progress':{'screens_this_batch':len(attempted),'total_screened':len(screened),
            'max_total_screens':MAX_TOTAL_SCREENS,'preliminary_fit_count':len(fits),'shortlist_target':SHORTLIST_TARGET,
            'model_version':'bounded-discovery-continuation-v1','batch_count':payload['batches'],'stop_reason':reason,'cache_hit':False,
            'next_token':self._encode(payload) if has_more else None,
            'interpretation':'Bounded preliminary screening; fits are not confirmed mutual benefits. No Simulation is run.'}}
        size=_bytes(result)+_bytes(cache_key)
        if size<=self.max_bytes:
            with self.lock:
                previous=self.cache.pop(cache_key,None)
                if previous:self.cache_bytes-=previous[2]
                while self.cache and (len(self.cache)>=self.max_entries or self.cache_bytes+size>self.max_bytes):
                    _,(_,_,old_size)=self.cache.popitem(last=False);self.cache_bytes-=old_size
                self.cache[cache_key]=(now,result,size);self.cache_bytes+=size
        return result
