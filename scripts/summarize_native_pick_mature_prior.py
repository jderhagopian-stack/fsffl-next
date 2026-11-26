"""Aggregate same-class selection examples without hiding incomplete evidence.

This is a selection-frequency summary, not additional independent draft classes
or calibrated uncertainty. Different training classes require an explicit
class-weighting policy and are deliberately rejected by this helper.
"""
from math import fsum

from fsffl.value.career_forward_intrinsic import CareerForwardModelAuthority


def summarize(fitted):
    cases=fitted['cases']
    if not cases:raise ValueError('at least one source draft required')
    first=cases[0];classes=first['training_classes'];coordinate=first['economic_coordinate']
    if len(classes)!=1:raise ValueError('summary requires one explicit independent draft class')
    ranks=[s['rank'] for s in first['slots']]
    if ranks!=list(range(1,len(ranks)+1)):raise ValueError('complete ordered slot coordinate required')
    for case in cases:
        if case['training_classes']!=classes or case['economic_coordinate']!=coordinate:
            raise ValueError('mixed class or economic coordinate requires a separate policy')
        if [s['rank'] for s in case['slots']]!=ranks:raise ValueError('source draft slot coordinates differ')
    slots=[]
    for i,rank in enumerate(ranks):
        samples=[case['slots'][i] for case in cases];available=[s for s in samples if s['authority'] is not None]
        authority=None
        if len(available)==len(samples):
            means={k:fsum(s['authority'][k]/len(samples) for s in samples) for k in ('low','reference_center','high')}
            authority=CareerForwardModelAuthority(**means,width=means['high']-means['low']).model_dump(mode='json')
        slots.append({'rank':rank,'authority':authority,'supported_source_drafts':len(available),
            'requested_source_drafts':len(samples),'missing_source_drafts':[j for j,s in enumerate(samples) if s['authority'] is None]})
    return {'production_eligible':False,'status':'single_class_selection_frequency_career_reference_research',
        'training_classes':classes,'independent_draft_classes':1,'source_draft_count':len(cases),
        'economic_coordinate':coordinate,'slots':slots,'assumption_ref':fitted.get('assumption_ref'),
        'uncertainty':'model_authority_only_not_class_dispersion_or_predictive_confidence',
        'weighting':'equal_observed_draft_frequency_within_one_class'}
