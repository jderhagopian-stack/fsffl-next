"""Read-only annual cohort-prior coverage and class-sensitivity diagnostic.

Reuses observed native labels; never drops incomplete training classes, certifies
source-absent rows as zeros, fits Career tails or emits a production pick curve.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from math import fsum
from pathlib import Path

from scripts.evaluate_native_pick_baseline import _total, evaluate


def audit(document, *, release_season, complete_through, max_slots, discount=.85):
    # Existing validator enforces coordinate, duplicate and numeric contracts.
    evaluate(document,horizon=3,discount=discount,heldout_classes=[release_season],
             max_slots=max_slots,complete_through=complete_through)
    if complete_through >= release_season:
        raise ValueError('annual diagnostic requires completed seasons before release')
    outputs=[]
    for case in document['cases']:
        rows={(r['draft_season'],r['rank']):r for r in case['selections']}
        classes=sorted({y for y,s in rows if y+2 < release_season and y+2 <= complete_through})
        slots=[];gaps=[]
        for slot in range(1,max_slots+1):
            labels=[];slot_gaps=[]
            for year in classes:
                row=rows.get((year,slot));value=_total(row,3,discount)
                if value is not None:
                    labels.append((year,value));continue
                if row is None:reason='selection_rank_absent'
                elif row.get('player_id') is None:reason='identity_unresolved'
                else:reason='native_season_label_missing'
                gap=dict(draft_season=year,rank=slot,reason=reason,
                         player_id=row.get('player_id') if row else None)
                if row and reason=='native_season_label_missing':
                    values=row['raw_observed'].get('3')
                    gap['missing_seasons']=[year+i for i,v in enumerate(values) if v is None] if values and len(values)==3 else None
                slot_gaps.append(gap)
            gaps.extend(slot_gaps)
            mean=fsum(v/len(labels) for _,v in labels) if labels and not slot_gaps else None
            # Sensitivity to class choice, not a confidence/predictive interval.
            leave_one=[]
            if mean is not None and len(labels)>1:
                for dropped,_ in labels:
                    leave_one.append(fsum(v/(len(labels)-1) for year,v in labels if year!=dropped))
            offsets={}
            for offset in (0,1,2):
                values=[]
                for year in classes:
                    row=rows.get((year,slot))
                    annual=row['raw_observed'].get('3') if row and row.get('player_id') else None
                    prefix=annual[:3-offset] if annual and len(annual)==3 else None
                    if prefix is None or any(v is None for v in prefix):break
                    values.append(fsum(v*discount**(offset+i) for i,v in enumerate(prefix)))
                offsets[str(offset)]=fsum(v/len(values) for v in values) if classes and len(values)==len(classes) else None
            slots.append(dict(rank=slot,requested_classes=len(classes),observed_classes=len(labels),
                estimate_first_three_post_draft=mean,calendar_three_year_by_draft_offset=offsets,
                missing_training_classes=len(slot_gaps),leave_one_class_mean_min=min(leave_one) if leave_one else None,
                leave_one_class_mean_max=max(leave_one) if leave_one else None,
                sensitivity_kind='leave_one_class_not_confidence_or_prediction_interval'))
        outputs.append(dict(economic_coordinate=case['economic_coordinate'],
            source_limitations=case.get('selection_evidence_limitations',[]),training_classes=classes,
            supported_slots=sum(s['estimate_first_three_post_draft'] is not None for s in slots),
            requested_slots=max_slots,gap_counts=dict(Counter(g['reason'] for g in gaps)),
            gaps=gaps,slots=slots,career_available=False,production_eligible=False))
    digest=hashlib.sha256(json.dumps(document,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return dict(status='annual_cohort_prior_diagnostic_not_validated_pick_model',production_eligible=False,
        input_sha256=digest,release_season=release_season,complete_through=complete_through,discount=discount,
        class_policy='all_available_complete_window_classes_no_survivor_filter',
        calendar_policy='same_mature_training_classes_for_offsets_0_1_2_no_reclassification_as_Career',cases=outputs)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--release-season',type=int,required=True);p.add_argument('--complete-through',type=int,required=True)
    p.add_argument('--max-slots',type=int,required=True)
    args=p.parse_args();result=audit(json.loads(args.input.read_text()),release_season=args.release_season,
        complete_through=args.complete_through,max_slots=args.max_slots)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps([{k:c[k] for k in ('supported_slots','requested_slots','training_classes','gap_counts')} for c in result['cases']]))


if __name__=='__main__':main()
