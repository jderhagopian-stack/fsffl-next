"""Stable coverage order for a SET of inferred goals, never utility weights."""
import hashlib


def exploration_goals(goals, *, inferred=False, team_id=''):
    values=tuple(dict.fromkeys(getattr(g,'value',g) for g in goals))
    if not inferred or len(values)<2:return values
    values=tuple(sorted(values))
    # A team-scoped rotation prevents tuple serialization or a universal Current
    # prefix deciding which direction gets the first bounded search slot.
    offset=int(hashlib.sha256(str(team_id).encode()).hexdigest()[:8],16)%len(values)
    return values[offset:]+values[:offset]
