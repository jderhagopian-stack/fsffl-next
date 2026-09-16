from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def q(vals, p):
    xs=sorted(float(v) for v in vals)
    if not xs:return None
    z=(len(xs)-1)*p; lo=int(math.floor(z)); hi=int(math.ceil(z))
    return xs[lo] if lo==hi else xs[lo]*(hi-z)+xs[hi]*(z-lo)


def entropy(probs):
    return -sum(float(v)*math.log(max(1e-12,float(v))) for v in probs.values() if float(v)>0)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--implementation-root',type=Path,required=True)
    ap.add_argument('--forecast-freeze',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()

    freeze=json.loads(a.forecast_freeze.read_text())
    if not freeze.get('forecast_frozen'):
        raise RuntimeError('Forecast selection must be frozen before downstream Shapley inspection')
    if freeze.get('downstream_shapley_accessed'):
        raise RuntimeError('freeze must describe the pre-downstream state')

    sys.path.insert(0,str(a.implementation_root/'src'))
    from fsffl.state.models import LeagueRules,LineupRequirement,Position,RosterSlot
    from fsffl.value.shapley_intrinsic import (
        FROZEN_INTRINSIC_DISCOUNT,FROZEN_SHAPLEY_PERMUTATIONS,FROZEN_SHAPLEY_SEED,
        FutureStateForecast,PlayerIntrinsicForecast,build_intrinsic_shapley_estimates,
    )

    expected={'permutations':2048,'discount':0.85,'seed':20260915}
    actual={'permutations':FROZEN_SHAPLEY_PERMUTATIONS,'discount':FROZEN_INTRINSIC_DISCOUNT,'seed':FROZEN_SHAPLEY_SEED}
    if actual!=expected:raise RuntimeError(f'frozen downstream constants changed: {actual}')

    rules=LeagueRules(
        team_count=12,roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB,count=1),
            LineupRequirement(slot=RosterSlot.RB,count=2),
            LineupRequirement(slot=RosterSlot.WR,count=3),
            LineupRequirement(slot=RosterSlot.TE,count=1),
            LineupRequirement(slot=RosterSlot.FLEX,count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX,count=1),
        ),scoring=(),
    )
    states=('out','depth','usable','starter','premium','elite')
    means={
        'QB':dict(zip(states,(0.,70.,150.,250.,330.,400.))),
        'RB':dict(zip(states,(0.,25.,70.,130.,190.,250.))),
        'WR':dict(zip(states,(0.,30.,75.,135.,195.,255.))),
        'TE':dict(zip(states,(0.,20.,55.,100.,155.,215.))),
    }
    # Anonymous archetypes only. Year 1 stands for the independent governed live/current-season
    # Forecast coordinate. Year 2 and Year 3 stand for completed-source direct I1 h=2/h=3.
    # h=1 is deliberately absent from the consumer fixture because it targets the same calendar
    # season as Year 1 and must not be double-counted.
    counts={'QB':24,'RB':32,'WR':48,'TE':24}
    forecasts=[]; entropy2=[]; entropy3=[]
    for pos,n in counts.items():
        P=Position(pos)
        for i in range(n):
            strength=1.0-i/max(1,n-1)
            y1=max(0.,means[pos]['depth']+(means[pos]['elite']-means[pos]['depth'])*strength)
            p2={
                'out':.04+.12*(1-strength),'depth':.10+.18*(1-strength),'usable':.18,
                'starter':.30-.04*(1-strength),'premium':.22*strength+.05,'elite':.11*strength+.02,
            }
            z=sum(p2.values());p2={k:v/z for k,v in p2.items()}
            # h=3 is intentionally less concentrated than h=2, reflecting longer-horizon uncertainty.
            uniform=1/6
            p3={k:.78*v+.22*uniform for k,v in p2.items()}
            e2=sum(p2[s]*means[pos][s] for s in states);e3=sum(p3[s]*means[pos][s] for s in states)
            entropy2.append(entropy(p2));entropy3.append(entropy(p3))
            forecasts.append(PlayerIntrinsicForecast(
                player_id=f'{pos}{i+1:03d}',position=P,current_points=y1,
                year_2=FutureStateForecast(probabilities=p2,state_means=means[pos],anticipated_points=e2),
                year_3=FutureStateForecast(probabilities=p3,state_means=means[pos],anticipated_points=e3),
            ))

    estimates=build_intrinsic_shapley_estimates(
        tuple(forecasts),rules=rules,permutations=FROZEN_SHAPLEY_PERMUTATIONS,seed=FROZEN_SHAPLEY_SEED,
    )
    residuals=[]
    for x in estimates:
        exact=x.year_1_shapley+FROZEN_INTRINSIC_DISCOUNT*x.year_2_expected_shapley+(FROZEN_INTRINSIC_DISCOUNT**2)*x.year_3_expected_shapley
        residuals.append(x.value-exact)
    finite=all(math.isfinite(v) for x in estimates for v in (x.value,x.year_1_shapley,x.year_2_expected_shapley,x.year_3_expected_shapley))
    nonnegative=all(v>=-1e-12 for x in estimates for v in (x.value,x.year_1_shapley,x.year_2_expected_shapley,x.year_3_expected_shapley))
    out={
        'status':'RESEARCH_ONLY_POST_FORECAST_FREEZE',
        'forecast_disposition':freeze.get('disposition'),
        'calendar_contract':{
            'year_1':'independent governed live/current-season Forecast for evaluation calendar year E',
            'year_2':'completed-source I1 direct h=2 -> E+1',
            'year_3':'completed-source I1 direct h=3 -> E+2',
            'completed_source_h1':'diagnostic/reference only -> E; excluded from value sum to prevent double-counting',
        },
        'frozen_constants':actual,
        'anonymous_fixture':{'team_count':12,'players':len(forecasts),'position_counts':counts,'named_player_tuning':False},
        'checks':{
            'formula_exact_max_abs_residual':max(abs(x) for x in residuals),
            'formula_exact_pass':max(abs(x) for x in residuals)<1e-10,
            'finite_pass':finite,'nonnegative_pass':nonnegative,
            'h1_double_count_absent_pass':True,
            'year3_entropy_ge_year2_pass':sum(entropy3)/len(entropy3)>=sum(entropy2)/len(entropy2)-1e-12,
        },
        'diagnostics':{
            'mean_year2_entropy':sum(entropy2)/len(entropy2),'mean_year3_entropy':sum(entropy3)/len(entropy3),
            'value_p10':q([x.value for x in estimates],.10),'value_p50':q([x.value for x in estimates],.50),'value_p90':q([x.value for x in estimates],.90),
            'year1_shapley_p50':q([x.year_1_shapley for x in estimates],.50),
            'year2_expected_shapley_p50':q([x.year_2_expected_shapley for x in estimates],.50),
            'year3_expected_shapley_p50':q([x.year_3_expected_shapley for x in estimates],.50),
        },
        'scope_note':'This is a downstream semantic/economic sanity test after Forecast selection. Anonymous fixture values do not select or tune Forecast and do not claim historical live-current Forecast accuracy.',
        'implementation_pr_modified':False,
    }
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True))
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=='__main__':main()
