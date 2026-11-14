"""Research-only training-label sensitivity; validation targets stay observed.

An absent source-panel row may be *assumed* to contribute no production only in
this explicit scenario. It is never relabelled an observed zero or a retirement.
No source fetch, model publication, Shapley recomputation or production write.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
import hashlib
import json
from math import fsum
from pathlib import Path

try:
    from scripts.evaluate_native_pick_baseline import evaluate
except ModuleNotFoundError:  # direct CLI invocation outside an installed scripts package
    from evaluate_native_pick_baseline import evaluate


def compare(document, *, panel_keys, panel_sha256, assumption_ref, **settings):
    if not assumption_ref.strip():
        raise ValueError('research assumption requires an explicit evidence reference')
    strict = evaluate(document, **settings)
    horizon = settings['horizon']; through = settings['complete_through']; outputs = []
    for case, strict_case in zip(document['cases'], strict['cases']):
        if case['economic_coordinate']['panel_sha256'] != panel_sha256:
            raise ValueError('sensitivity panel does not match the economic coordinate')
        folds = []
        for strict_fold in strict_case['folds']:
            heldout = strict_fold['heldout_class']; adjusted = deepcopy(case); imputed = []
            for row in adjusted['selections']:
                if row['draft_season'] not in strict_fold['training_classes'] or row.get('player_id') is None:
                    continue
                values = row['raw_observed'].get(str(horizon))
                if values is None or len(values) != horizon:
                    continue
                for offset, value in enumerate(values):
                    season = row['draft_season'] + offset
                    if value is None and season <= through and (row['player_id'], season) not in panel_keys:
                        values[offset] = 0.0
                        imputed.append(dict(player_id=row['player_id'],season=season,rank=row['rank'],
                            basis='research_assumed_absent_panel_row_no_production'))
            options = {**settings, 'heldout_classes':[heldout]}
            scenario = evaluate({'cases':[adjusted]}, **options)['cases'][0]['folds'][0]
            old = {r['rank']:r for r in strict_fold['predictions']}
            new = {r['rank']:r for r in scenario['predictions']}
            common = sorted(set(old) & set(new))
            if any(old[s]['observed'] != new[s]['observed'] for s in common):
                raise ValueError('sensitivity must not change observed validation targets')
            def mae(rows):
                return fsum(abs(rows[s]['estimate']-rows[s]['observed']) for s in common)/len(common) if common else None
            folds.append(dict(heldout_class=heldout,training_classes=strict_fold['training_classes'],
                strict_covered=strict_fold['covered'],scenario_covered=scenario['covered'],
                strict_mae=strict_fold['mae'],scenario_mae=scenario['mae'],common_covered=len(common),
                common_strict_mae=mae(old),common_scenario_mae=mae(new),
                assumption_uses=imputed,assumed_training_seasons=len(imputed),
                scenario=scenario))
        outputs.append(dict(economic_coordinate=case['economic_coordinate'],folds=folds))
    return dict(status='research_training_missingness_sensitivity_not_verified_zero_or_pick_model',
        production_eligible=False,assumption_ref=assumption_ref,validation_targets='observed_only',
        source_panel_sha256=panel_sha256,strict_input_sha256=strict['input_sha256'],
        estimator=strict['estimator'],cases=outputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input','panel','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--assumption-ref',required=True)
    parser.add_argument('--heldout',type=int,action='append',required=True)
    parser.add_argument('--complete-through',type=int,required=True)
    parser.add_argument('--max-slots',type=int,required=True)
    parser.add_argument('--horizon',type=int,choices=(1,2,3,7),required=True)
    parser.add_argument('--discount',type=float,required=True)
    parser.add_argument('--estimator',choices=('slot_mean','isotonic_slot_mean'),default='slot_mean')
    args = parser.parse_args()
    keys = set()
    with args.panel.open(newline='') as handle:
        for row in csv.DictReader(handle):
            key = row['player_id'], int(row['season'])
            if key in keys:raise ValueError('duplicate source panel player-season')
            keys.add(key)
    result = compare(json.loads(args.input.read_text()), panel_keys=keys,
        panel_sha256=hashlib.sha256(args.panel.read_bytes()).hexdigest(),assumption_ref=args.assumption_ref,
        horizon=args.horizon,discount=args.discount,heldout_classes=args.heldout,
        max_slots=args.max_slots,complete_through=args.complete_through,estimator=args.estimator)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps([{'coordinate':c['economic_coordinate']['rules'],'folds':[
        {k:v for k,v in f.items() if k not in ('scenario','assumption_uses')} for f in c['folds']]} for c in result['cases']]))


if __name__ == '__main__':
    main()
