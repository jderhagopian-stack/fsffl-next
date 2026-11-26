"""Request-local focal package shapes; no equivalence of counterparty outcomes."""
import hashlib
import json


def focal_package_family(row, *, picks, read):
    def token(asset):
        ref = asset['asset_ref']
        if not ref.startswith('pick:') or read is None:
            return ref
        key = ref[5:]
        pick, source = picks.get(key), read.pick_sources.get(key)
        if pick is None or not source or source.get('probability_basis') != 'exchangeable_future_slot_prior':
            return ref
        values = tuple(read.pick_values[h].get(key) for h in ('three_year', 'career'))
        if None in values:
            return ref
        # Same year/round/native prior only. An actual projected slot, different
        # year or different reference distribution never borrows this identity.
        return json.dumps(['future_pick', pick.season, pick.round, values, {k:v for k,v in source.items() if k not in ('original_team_id','owner_team_id')}], sort_keys=True)
    package = [sorted(a['asset_ref'] for a in row['send']), sorted(token(a) for a in row['receive'])]
    return hashlib.sha256(json.dumps(package, sort_keys=True).encode()).hexdigest()
