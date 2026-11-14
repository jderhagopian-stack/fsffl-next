"""Read-only chronological negative-control benchmark for normalized pick research.

Input cases carry exact rules and declared economic coordinates, plus selections
with draft_season, rank, player_id and raw_observed[horizon] annual labels. Rank
proxies remain proxies; this script neither fits a production model nor infers
missing seasons, Career termination, selection probabilities or predictive bands.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from math import fsum, isfinite, sqrt
from pathlib import Path


def _total(row, horizon, discount):
    if row is None or row.get('player_id') is None:
        return None
    values = row['raw_observed'].get(str(horizon))
    if values is None or len(values) != horizon:
        return None
    if any(v is None for v in values):
        return None
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) for v in values):
        raise ValueError('annual native labels must be finite numbers or missing')
    try:
        result = fsum(v * discount**i for i, v in enumerate(values))
    except OverflowError as exc:
        raise ValueError('annual native aggregate must remain finite') from exc
    if not isfinite(result):
        raise ValueError('annual native aggregate must remain finite')
    return result


def monotone_slot_means(means):
    """Exploratory PAVA prior: expected native outcome weakly decreases by rank.

    Fits only supplied complete training-slot means with equal class counts;
    never consumes validation outcomes or fills an unsupported slot.
    """
    blocks = []
    for slot, value in sorted(means.items()):
        blocks.append(([slot], value, 1))
        while len(blocks) > 1 and blocks[-2][1] < blocks[-1][1]:
            right = blocks.pop(); left = blocks.pop()
            count = left[2] + right[2]
            average = left[1] * (left[2] / count) + right[1] * (right[2] / count)
            blocks.append((left[0] + right[0], average, count))
    return {slot: average for slots, average, count in blocks for slot in slots}


def evaluate(document, *, horizon, discount, heldout_classes, max_slots, complete_through, estimator="slot_mean"):
    """Prior complete-class slot means; abstain on any missing past slot label.

    The caller declares the source's complete-season boundary. A class can train
    a fold only when its entire label window ended before the heldout season.
    No complete-case pooling, within-class split or future training label is used.
    This conservative comparator is not a recommendation for final model fitting.
    """
    if estimator not in ('slot_mean', 'isotonic_slot_mean'):
        raise ValueError('unsupported research estimator')
    if horizon not in (1, 2, 3, 7) or max_slots < 1:
        raise ValueError('supported observed horizon and positive slot count required')
    if not isfinite(discount) or not 0 < discount <= 1:
        raise ValueError('discount must be explicit and between zero and one')
    if len(heldout_classes) != len(set(heldout_classes)):
        raise ValueError('heldout classes must be unique')
    outputs = []
    for case in document['cases']:
        # Never combine cases or infer coordinate compatibility from format labels.
        coordinate = case['economic_coordinate']
        for key in ('rules', 'scoring_signature', 'native_model_version', 'panel_sha256'):
            if not coordinate.get(key):
                raise ValueError('each case requires explicit economic coordinate provenance')
        rows = {}; classes = set()
        for row in case['selections']:
            year, slot = row['draft_season'], row['rank']
            if isinstance(year, bool) or not isinstance(year, int) or isinstance(slot, bool) or not isinstance(slot, int) or slot < 1:
                raise ValueError('draft season and rank must be integer coordinates')
            if (year, slot) in rows:
                raise ValueError('duplicate selection coordinate')
            rows[year, slot] = row
            classes.add(year)
        folds = []
        for heldout in sorted(heldout_classes):
            train = sorted(y for y in classes if y + horizon - 1 < heldout and y + horizon - 1 <= complete_through)
            abstain = Counter(); predictions = []
            means = {}
            if train:
                for slot in range(1, max_slots + 1):
                    labels = [_total(rows.get((year, slot)), horizon, discount) for year in train]
                    if all(v is not None for v in labels):
                        means[slot] = fsum(labels) / len(labels)
            if estimator == 'isotonic_slot_mean':
                means = monotone_slot_means(means)
            for slot in range(1, max_slots + 1):
                if not train:
                    abstain['no_mature_training_classes'] += 1
                    continue
                if heldout + horizon - 1 > complete_through:
                    abstain['target_right_censored'] += 1
                    continue
                if slot not in means:
                    abstain['incomplete_training_slot'] += 1
                    continue
                observed = _total(rows.get((heldout, slot)), horizon, discount)
                if observed is None:
                    abstain['incomplete_target_slot'] += 1
                    continue
                prediction = means[slot]
                predictions.append(dict(rank=slot, estimate=prediction, observed=observed))
            errors = [r['estimate'] - r['observed'] for r in predictions]
            folds.append(dict(heldout_class=heldout, training_classes=train, sample_per_slot=len(train),
                covered=len(errors), requested_slots=max_slots, abstentions=dict(abstain),
                mae=fsum(abs(x) for x in errors)/len(errors) if errors else None,
                rmse=sqrt(fsum(x*x for x in errors)/len(errors)) if errors else None,
                predictive_intervals_available=False, predictions=predictions))
        outputs.append(dict(economic_coordinate=coordinate,
            selection_evidence_limitations=case.get('selection_evidence_limitations', []), folds=folds))
    digest = hashlib.sha256(json.dumps(document, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return dict(status='research_negative_control_not_archived_forecast_or_pick_valuation',
        production_eligible=False, input_sha256=digest, horizon=horizon, discount=discount,
        complete_through_season=complete_through, estimator=estimator, cases=outputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--horizon', type=int, choices=(1, 2, 3, 7), required=True)
    parser.add_argument('--discount', type=float, required=True)
    parser.add_argument('--heldout', type=int, action='append', required=True)
    parser.add_argument('--max-slots', type=int, required=True)
    parser.add_argument('--complete-through', type=int, required=True)
    parser.add_argument('--estimator',choices=('slot_mean','isotonic_slot_mean'),default='slot_mean')
    args = parser.parse_args()
    result = evaluate(json.loads(args.input.read_text()), horizon=args.horizon, discount=args.discount,
        heldout_classes=args.heldout, max_slots=args.max_slots, complete_through=args.complete_through, estimator=args.estimator)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps({'status': result['status'], 'production_eligible': False,
        'folds': [{k:v for k,v in fold.items() if k!='predictions'} for case in result['cases'] for fold in case['folds']]}))


if __name__ == '__main__':
    main()
