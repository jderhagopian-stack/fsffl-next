from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else math.nan


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        r = (i + j - 1) / 2.0
        for k in range(i, j):
            out[order[k]] = r
        i = j
    return out


def pearson(a, b):
    if len(a) < 2 or len(a) != len(b):
        return math.nan
    ma, mb = mean(a), mean(b)
    da = [x - ma for x in a]
    db = [x - mb for x in b]
    denom = math.sqrt(sum(x*x for x in da) * sum(x*x for x in db))
    return sum(x*y for x, y in zip(da, db)) / denom if denom else math.nan


def spearman(a, b):
    return pearson(ranks(a), ranks(b))


def fold_year(fold_id: str) -> int:
    return int(fold_id.rsplit('-', 1)[-1])


def aggregate(rows):
    grouped = defaultdict(lambda: [0.0, 0.0, None])
    for row in rows:
        key = (row['fold_id'], row['asset_id'])
        pred = max(0.0, float(row['player_forecast_mean']) - float(row['replacement_forecast_mean'])) * float(row['annual_weight'])
        actual = max(0.0, float(row['realized_player_points']) - float(row['realized_replacement_points'])) * float(row['annual_weight'])
        grouped[key][0] += pred
        grouped[key][1] += actual
        grouped[key][2] = row['position']
    return [
        {'fold_id': k[0], 'asset_id': k[1], 'pred': v[0], 'actual': v[1], 'position': v[2]}
        for k, v in grouped.items()
    ]


def summarize(rows):
    return {
        'n': len(rows),
        'mae': mean(abs(r['pred'] - r['actual']) for r in rows),
        'spearman': spearman([r['pred'] for r in rows], [r['actual'] for r in rows]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-a-rows', type=Path, required=True)
    parser.add_argument('--qb-results', type=Path, required=True)
    parser.add_argument('--model-a-results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    with args.model_a_results.open(encoding='utf-8') as handle:
        model_a_results = json.load(handle)
    with args.qb_results.open(encoding='utf-8') as handle:
        qb_results = json.load(handle)
    with args.model_a_rows.open(newline='', encoding='utf-8') as handle:
        original = list(csv.DictReader(handle))

    probabilities = {}
    for record in qb_results['records']:
        fold = f"preseason-{record['source_season']}"
        probabilities[(fold, record['player_id'], 1)] = float(record['prob_y2'])
        probabilities[(fold, record['player_id'], 2)] = float(record['prob_y3'])

    y1 = {
        (row['fold_id'], row['asset_id']): float(row['player_forecast_mean'])
        for row in original if int(row['season_offset']) == 0
    }
    integrated = [dict(row) for row in original]
    changed = 0
    for row in integrated:
        offset = int(row['season_offset'])
        key = (row['fold_id'], row['asset_id'], offset)
        if row['position'] == 'QB' and offset in (1, 2) and key in probabilities:
            row['player_forecast_mean'] = probabilities[key] * y1[(row['fold_id'], row['asset_id'])]
            changed += 1

    old = aggregate(original)
    new = aggregate(integrated)
    old_by_key = {(r['fold_id'], r['asset_id']): r for r in old}
    new_by_key = {(r['fold_id'], r['asset_id']): r for r in new}
    eligible_keys = [k for k in old_by_key if fold_year(k[0]) >= 2006]
    old_eligible = [old_by_key[k] for k in eligible_keys]
    new_eligible = [new_by_key[k] for k in eligible_keys]

    affine_mae = float(model_a_results['best_candidate']['aggregate']['affine_mae'])
    prior = summarize(old_eligible)
    candidate = summarize(new_eligible)
    positions = {}
    for pos in ('QB', 'RB', 'WR', 'TE'):
        positions[pos] = {
            'prior': summarize([r for r in old_eligible if r['position'] == pos]),
            'candidate': summarize([r for r in new_eligible if r['position'] == pos]),
        }

    validation_qb_keys = [
        k for k in eligible_keys
        if old_by_key[k]['position'] == 'QB' and 2017 <= fold_year(k[0]) <= 2022
    ]
    validation_qb_old = [old_by_key[k] for k in validation_qb_keys]
    validation_qb_new = [new_by_key[k] for k in validation_qb_keys]

    folds = []
    for season in range(2017, 2023):
        fid = f'preseason-{season}'
        old_fold = [r for r in old_eligible if r['fold_id'] == fid]
        new_fold = [r for r in new_eligible if r['fold_id'] == fid]
        before = summarize(old_fold)['mae']
        after = summarize(new_fold)['mae']
        folds.append({'season': season, 'prior_mae': before, 'candidate_mae': after, 'improvement': (before-after)/before})

    payload = {
        'status': 'PASS' if candidate['mae'] < prior['mae'] and all(f['candidate_mae'] <= f['prior_mae'] for f in folds) else 'FAIL',
        'method': 'replace only QB Y2/Y3 player forecast mean in the governed Model-A point-in-time panel with validated career-state probability × the same fold/player Y1 Forecast mean; all replacement forecasts, annual weights, realized outcomes and non-QB rows unchanged',
        'changed_qb_horizon_rows': changed,
        'overall': {
            'n': candidate['n'],
            'affine_mae': affine_mae,
            'prior_intrinsic_v1_mae': prior['mae'],
            'qb_integrated_intrinsic_v1_mae': candidate['mae'],
            'improvement_vs_affine': (affine_mae-candidate['mae'])/affine_mae,
            'improvement_vs_prior_v1': (prior['mae']-candidate['mae'])/prior['mae'],
        },
        'positions': positions,
        'qb_2017_2022': {
            'prior': summarize(validation_qb_old),
            'candidate': summarize(validation_qb_new),
        },
        'folds_2017_2022': folds,
        'non_qb_unchanged': all(abs(positions[p]['prior']['mae']-positions[p]['candidate']['mae']) < 1e-12 for p in ('RB','WR','TE')),
        'qb_challenger_status': qb_results['status'],
        'qb_calibration': qb_results['state'],
        'qb_prediction_metrics': {'all_qb': qb_results['overall'], 'elite_qb': qb_results['elite']},
        'qb_fold_win_rate': qb_results['fold_win_rate'],
        'qb_trajectory': qb_results['trajectory'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload['status'] != 'PASS' or not payload['non_qb_unchanged']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
