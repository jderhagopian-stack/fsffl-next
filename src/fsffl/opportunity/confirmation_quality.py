"""Search consumes existing confirmation evidence; it never calculates outcomes."""

def current_required_teams(row):
    if '_current_required_teams' in row:return tuple(row['_current_required_teams'])
    required=[]
    for side in ('side_a','side_b'):
        owner=((row.get('objective_assessment') or {}).get(side) or {})
        context=owner.get('context') or {};goals=context.get('objectives',())
        if 'current_competitiveness' not in goals:continue
        future_gain=any(m.get('objective') in goals and m.get('objective') in ('three_year_contribution','career_contribution')
            and m.get('authoritative') and isinstance(m.get('delta'),(int,float)) and m['delta']>1e-9 for m in owner.get('metrics',()))
        if not future_gain:required.append(context.get('team_id') or 'unresolved:'+side)
    return tuple(required)


def apply_confirmation_status(rows, *, require_confirmation):
    for row in rows:
        if row['shortlist_quality']['status'] not in ('shortlist','strategic_tradeoff'):continue
        if not current_required_teams(row):continue
        proof=row.get('screen_confirmation') or {}
        if proof.get('status')=='verified':continue
        if not require_confirmation and proof.get('status') not in ('not_worthwhile','review','unavailable'):continue
        row['shortlist_quality'].update(status='review',reason=proof.get('reason','current_case_awaits_confirmation'))
