"""Read-only Career candidate sensitivity; never a pooled production estimator.

Source/profile and class changes can be confounded. Dispersion here is descriptive
sensitivity, not forecast uncertainty, a confidence interval or a promotion gate.
"""
from math import isfinite
from statistics import median

from fsffl.value.career_forward_intrinsic import CareerForwardModelAuthority


def audit(cases, *, max_slots):
    if type(max_slots) is not int or max_slots<1 or len(cases)<2:
        raise ValueError('at least two source cases and a positive integer slot count required')
    coordinate=cases[0]['economic_comparison_coordinate'];seen=set();lookups=[];classes=set();source_summary=[]
    for case in cases:
        name=case['source_case_id'];year=case['draft_class']
        if not isinstance(name,str) or not name.strip() or name in seen:
            raise ValueError('source case identities must be nonblank and unique')
        if type(year) is not int or year<1:raise ValueError('explicit integer draft class required')
        if case['economic_comparison_coordinate']!=coordinate:
            raise ValueError('economic coordinates differ')
        if not case.get('source_fingerprints') or any(not x.strip() for x in case['source_fingerprints']):
            raise ValueError('source fingerprints required')
        seen.add(name);classes.add(year);lookup={}
        for slot in case['slots']:
            rank=slot['rank']
            if type(rank) is not int or not 1<=rank<=max_slots or rank in lookup:
                raise ValueError('invalid or duplicate slot coordinate')
            authority=slot.get('authority')
            if authority is not None:
                authority=CareerForwardModelAuthority.model_validate(authority)
                if any(not isfinite(v) for v in authority.model_dump().values()):
                    raise ValueError('finite model authority required')
            lookup[rank]=authority
        increases=[r for r in range(1,max_slots) if lookup.get(r) is not None and lookup.get(r+1) is not None
            and lookup[r+1].reference_center>lookup[r].reference_center]
        source_summary.append({'source_case_id':name,'draft_class':year,'source_fingerprints':case['source_fingerprints'],
            'supported_slots':sum(v is not None for v in lookup.values()),'adjacent_increase_at_ranks':increases,
            'source_limitations':case.get('source_limitations',[])})
        lookups.append(lookup)
    rows=[]
    for rank in range(1,max_slots+1):
        values=[lookup.get(rank) for lookup in lookups]
        missing=[cases[i]['source_case_id'] for i,v in enumerate(values) if v is None]
        centers={cases[i]['source_case_id']:v.reference_center for i,v in enumerate(values) if v is not None}
        spread=relative=None
        if not missing:
            low=min(centers.values());high=max(centers.values());spread=high-low
            relative=2*spread/(abs(high)+abs(low)) if high or low else 0.
        rows.append({'rank':rank,'source_centers':centers,'missing_source_cases':missing,
            'center_spread':spread,'symmetric_relative_center_spread':relative})
    common=[r for r in rows if not r['missing_source_cases']]
    return {'production_eligible':False,'status':'descriptive_source_and_class_sensitivity_not_new_values',
        'independent_draft_class_count':len(classes),'source_case_count':len(cases),'draft_classes':sorted(classes),
        'economic_comparison_coordinate':coordinate,'source_cases':source_summary,'slots':rows,
        'common_slots':len(common),'missing_common_slots':max_slots-len(common),
        'median_symmetric_relative_center_spread':median(r['symmetric_relative_center_spread'] for r in common) if common else None,
        'interpretation':'class_and_source_effects_may_be_confounded_not_predictive_uncertainty',
        'new_curve_or_promotion_created':False}
