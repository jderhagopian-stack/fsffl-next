from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from fsffl.state.models import Position

ROLLING_FUMBLES_LOST_MODEL_VERSION = (
    "next2-fumbles-lost-first-party-v2:rolling-completed-week"
)
ROLLING_FUMBLES_LOST_SUPPLEMENT_VERSION = (
    "current-supplemental-coordinate-v5:first-party-fumbles-lost-rolling"
)
NON_MATERIAL_PARTIAL_AUTHORITY = "NON_MATERIAL_PARTIAL"
_NON_MATERIAL_Z90 = 1.645
_NON_MATERIAL_FRACTION = 0.10
_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)
_ROLLING_CUTOFFS = tuple(range(2, 18))
_MATERIALITY_CUTOFFS = tuple(range(0, 18))
_OBSERVED_FALLBACK_TIERS = (
    "history_plus_current",
    "history_only",
    "current_only",
    "cold_start",
)


def production_table_payload_fingerprint(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# Exact machine-readable Research freeze merged in PR #297. Keeping the payload
# embedded makes runtime authority independent of repository working-directory
# layout while preserving byte-stable table identity/provenance.
ROLLING_PRODUCTION_TABLE_JSON = "{\"contract_version\":\"next2-fumbles-lost-first-party-v2:rolling-completed-week\",\"target_season\":2026,\"supported_completed_through_weeks\":[2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17],\"target_semantics\":\"exact lost fumbles only\",\"opportunity_semantics\":{\"QB\":\"pass_attempts+sacks_suffered+carries\",\"RB_WR_TE\":\"carries+receptions\"},\"historical_position_rates_frozen_from\":\"accepted v1 2021-2025 first-party evidence\",\"role_prior_games\":4,\"target_games\":17,\"uncertainty_contract\":\"max(sqrt(mean), rolling_position_floor); cold/identity-light also max accepted cold-start floor\",\"cold_start_floor\":0.789918699230448,\"materiality_contract\":{\"contract_version\":\"fumbles-lost-non-material-partial-v2:all-population-maximum\",\"status_when_passed\":\"NON_MATERIAL_PARTIAL\",\"formula\":\"abs(scoring_points_per_event)*event_bound_90 <= 0.10*1.645*supported_fantasy_point_stddev\",\"fraction\":0.1,\"bound_basis\":\"max(position-wide historical maximum season-equivalent target from all completed prior seasons, legacy primary-population bound)\",\"observed_population_validation\":\"history_plus_current;history_only;current_only;cold_start\",\"identity_light_rule\":\"eligible only when canonical offensive position is known/non-conflicting and matching cold-start position/cutoff eligibility is true\",\"late_qb_restriction\":\"QB cold-start and identity-light fail closed at completed weeks 13-17\",\"unknown_or_conflicting_position\":\"FAIL_CLOSED\",\"silent_zero_forbidden\":true,\"full_authority_claim_forbidden\":true},\"cutoffs\":{\"2\":{\"calibration_scalar\":0.6158756078393594,\"uncertainty_floor\":{\"QB\":1.7266303753562966,\"RB\":0.7375205714435535,\"WR\":0.4424922528480551,\"TE\":0.4524060195836409},\"materiality_event_bound_90\":{\"QB\":10.2,\"RB\":4.533333333333333,\"WR\":3.4,\"TE\":3.4},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":62.01159685500044,\"RB\":27.56070971333353,\"WR\":20.670532285000146,\"TE\":20.670532285000146},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":6.663999999999994,\"RB\":3.4,\"WR\":2.2666666666666666,\"TE\":2.2666666666666666},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true}}},\"3\":{\"calibration_scalar\":0.6183406074632098,\"uncertainty_floor\":{\"QB\":1.7808254003128128,\"RB\":0.7375205714435535,\"WR\":0.4424922528480551,\"TE\":0.4613691857966682},\"materiality_event_bound_90\":{\"QB\":10.928571428571429,\"RB\":4.857142857142857,\"WR\":3.642857142857143,\"TE\":2.4285714285714284},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":66.44099663035762,\"RB\":29.529331835714494,\"WR\":22.146998876785872,\"TE\":14.764665917857247},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":7.285714285714286,\"RB\":3.642857142857143,\"WR\":1.9307142857143242,\"TE\":2.4285714285714284},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true}}},\"4\":{\"calibration_scalar\":0.6172703293651463,\"uncertainty_floor\":{\"QB\":1.8551205289672343,\"RB\":0.7782346382858547,\"WR\":0.45155580548660884,\"TE\":0.4864330640772961},\"materiality_event_bound_90\":{\"QB\":7.846153846153846,\"RB\":5.230769230769231,\"WR\":3.923076923076923,\"TE\":2.6153846153846154},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":47.70122835000034,\"RB\":31.800818900000227,\"WR\":23.85061417500017,\"TE\":15.900409450000113},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":7.623846153846133,\"RB\":3.923076923076923,\"WR\":1.3076923076923077,\"TE\":2.6153846153846154},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true}}},\"5\":{\"calibration_scalar\":0.604519447731542,\"uncertainty_floor\":{\"QB\":1.8847095337887982,\"RB\":0.7782346382858547,\"WR\":0.46904266074144135,\"TE\":0.49174439761965577},\"materiality_event_bound_90\":{\"QB\":8.412371134020619,\"RB\":5.608247422680412,\"WR\":4.25,\"TE\":2.8333333333333335},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":51.14358503505191,\"RB\":34.09572335670127,\"WR\":25.838165356250183,\"TE\":17.22544357083346},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":7.010309278350515,\"RB\":2.804123711340206,\"WR\":1.402061855670103,\"TE\":2.804123711340206},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true}}},\"6\":{\"calibration_scalar\":0.6104555874233654,\"uncertainty_floor\":{\"QB\":1.9284536197623492,\"RB\":0.808031028874324,\"WR\":0.473237659696539,\"TE\":0.5027178677659695},\"materiality_event_bound_90\":{\"QB\":9.11731843575419,\"RB\":6.078212290502793,\"WR\":4.584269662921348,\"TE\":3.056179775280899},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":55.429360317318825,\"RB\":36.95290687821255,\"WR\":27.87038060898896,\"TE\":18.580253739325975},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":7.589323401613904,\"RB\":3.039106145251397,\"WR\":1.5195530726256983,\"TE\":2.1506741154562623},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true}}},\"7\":{\"calibration_scalar\":0.6061597798524929,\"uncertainty_floor\":{\"QB\":1.9284536197623492,\"RB\":0.8635309815603445,\"WR\":0.4868903543110204,\"TE\":0.5339032761584541},\"materiality_event_bound_90\":{\"QB\":9.831325301204819,\"RB\":6.554216867469879,\"WR\":4.975609756097561,\"TE\":3.317073170731707},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":59.770213836145004,\"RB\":39.84680922409667,\"WR\":30.24955944146363,\"TE\":20.166372960975753},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":6.62489874353289,\"RB\":3.3118462675535847,\"WR\":1.6585365853658536,\"TE\":2.289779606229775},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true}}},\"8\":{\"calibration_scalar\":0.6121199419509471,\"uncertainty_floor\":{\"QB\":1.9284536197623492,\"RB\":0.8787212089020041,\"WR\":0.5115176383093462,\"TE\":0.5460810664632603},\"materiality_event_bound_90\":{\"QB\":9.12751677852349,\"RB\":5.476510067114094,\"WR\":5.476510067114094,\"TE\":3.651006711409396},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":55.491361838926565,\"RB\":33.294817103355946,\"WR\":33.294817103355946,\"TE\":22.19654473557063},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":7.253333333333333,\"RB\":3.651006711409396,\"WR\":1.825503355704698,\"TE\":1.825503355704698},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true}}},\"9\":{\"calibration_scalar\":0.6015754542030642,\"uncertainty_floor\":{\"QB\":2.0012189987749713,\"RB\":0.9476440285746461,\"WR\":0.5115176383093462,\"TE\":0.5564889287468825},\"materiality_event_bound_90\":{\"QB\":10,\"RB\":6,\"WR\":4,\"TE\":4.059701492537314},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":60.795683191176906,\"RB\":36.47740991470614,\"WR\":24.318273276470762,\"TE\":24.681232579104655},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":8,\"RB\":4.059701492537314,\"WR\":2.029850746268657,\"TE\":2.029850746268657},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true}}},\"10\":{\"calibration_scalar\":0.5917533888294115,\"uncertainty_floor\":{\"QB\":2.0642432029432674,\"RB\":0.9590373589181869,\"WR\":0.5345428270049662,\"TE\":0.5893832260536446},\"materiality_event_bound_90\":{\"QB\":9.066666666666666,\"RB\":6.688524590163935,\"WR\":4.459016393442623,\"TE\":4.459016393442623},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":55.12141942666706,\"RB\":40.663342200000294,\"WR\":27.108894800000193,\"TE\":27.108894800000193},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":8.918032786885245,\"RB\":4.533333333333333,\"WR\":2.2666666666666666,\"TE\":2.2666666666666666},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true}}},\"11\":{\"calibration_scalar\":0.6069244166889987,\"uncertainty_floor\":{\"QB\":2.160167486957536,\"RB\":1.0468295056690466,\"WR\":0.5859271501721536,\"TE\":0.5893832260536446},\"materiality_event_bound_90\":{\"QB\":10.264150943396226,\"RB\":7.555555555555555,\"WR\":5.08411214953271,\"TE\":5.08411214953271},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":62.40160689811365,\"RB\":45.93451618888922,\"WR\":30.909207155140408,\"TE\":30.909207155140408},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":7.69811320754717,\"RB\":5.132075471698113,\"WR\":2.5660377358490565,\"TE\":2.5660377358490565},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true}}},\"12\":{\"calibration_scalar\":0.5872500645855492,\"uncertainty_floor\":{\"QB\":2.2167612338374614,\"RB\":1.092438527791138,\"WR\":0.6294455374143777,\"TE\":0.597147544516167},\"materiality_event_bound_90\":{\"QB\":11.826086956521738,\"RB\":8.869565217391305,\"WR\":5.913043478260869,\"TE\":5.913043478260869},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":71.8975036000005,\"RB\":53.923127700000386,\"WR\":35.94875180000025,\"TE\":35.94875180000025},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":8.869565217391305,\"RB\":5.849462365591398,\"WR\":2.9565217391304346,\"TE\":2.924731182795699},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true}}},\"13\":{\"calibration_scalar\":0.586529094977081,\"uncertainty_floor\":{\"QB\":2.3197186227881454,\"RB\":1.171862279771632,\"WR\":0.7116245917092033,\"TE\":0.6747042850777093},\"materiality_event_bound_90\":{\"QB\":13.772151898734178,\"RB\":10.597402597402597,\"WR\":7.064935064935065,\"TE\":3.5324675324675323},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":83.72873836962086,\"RB\":64.42763309610436,\"WR\":42.951755397402906,\"TE\":21.475877698701453},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":10.329113924050633,\"RB\":6.886075949367088,\"WR\":3.5324675324675323,\"TE\":3.5324675324675323},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":false,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":false,\"RB\":true,\"WR\":true,\"TE\":true}}},\"14\":{\"calibration_scalar\":0.6044083686899153,\"uncertainty_floor\":{\"QB\":2.6066997018059954,\"RB\":1.3317734498011957,\"WR\":0.7230297092507666,\"TE\":0.7943030804858575},\"materiality_event_bound_90\":{\"QB\":12.75,\"RB\":8.5,\"WR\":8.5,\"TE\":4.25},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":77.51449606875056,\"RB\":51.676330712500366,\"WR\":51.676330712500366,\"TE\":25.838165356250183},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":11.347499999999947,\"RB\":6.800000000000097,\"WR\":4.25,\"TE\":4.25},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":false,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":false,\"RB\":true,\"WR\":true,\"TE\":true}}},\"15\":{\"calibration_scalar\":0.5810149917840733,\"uncertainty_floor\":{\"QB\":2.7161737786429434,\"RB\":1.4160941540667553,\"WR\":0.8422314111714341,\"TE\":1.0234310741611572},\"materiality_event_bound_90\":{\"QB\":17,\"RB\":11.333333333333334,\"WR\":11.333333333333334,\"TE\":5.666666666666667},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":103.35266142500073,\"RB\":68.90177428333384,\"WR\":68.90177428333384,\"TE\":34.45088714166692},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":9.406666666666647,\"RB\":5.666666666666667,\"WR\":5.666666666666667,\"TE\":5.666666666666667},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":false,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":false,\"RB\":true,\"WR\":true,\"TE\":true}}},\"16\":{\"calibration_scalar\":0.5582250141099839,\"uncertainty_floor\":{\"QB\":3.5401148844098547,\"RB\":1.6194492366624471,\"WR\":1.0947841455437883,\"TE\":1.2139596137589443},\"materiality_event_bound_90\":{\"QB\":25.5,\"RB\":17,\"WR\":17,\"TE\":8.5},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":155.02899213750112,\"RB\":103.35266142500073,\"WR\":103.35266142500073,\"TE\":51.676330712500366},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":8.5,\"RB\":8.5,\"WR\":8.5,\"TE\":8.5},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":false,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":false,\"RB\":true,\"WR\":true,\"TE\":true}}},\"17\":{\"calibration_scalar\":0.5774526977136193,\"uncertainty_floor\":{\"QB\":5.1732368798971375,\"RB\":2.116121827352283,\"WR\":1.4272189141433074,\"TE\":1.4895569667821091},\"materiality_event_bound_90\":{\"QB\":34,\"RB\":34,\"WR\":17,\"TE\":17},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":206.70532285000147,\"RB\":206.70532285000147,\"WR\":103.35266142500073,\"TE\":103.35266142500073},\"legacy_primary_population_materiality_event_bound_90\":{\"QB\":17,\"RB\":17,\"WR\":2.5032220614172163,\"TE\":2.575381693296983},\"fallback_eligibility\":{\"history_plus_current\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"history_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"current_only\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"cold_start\":{\"QB\":false,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light\":{\"QB\":false,\"RB\":true,\"WR\":true,\"TE\":true}}}},\"season_start\":{\"point_estimate_authority\":{\"0\":\"OMIT_EXPLICITLY\",\"1\":\"OMIT_EXPLICITLY\",\"2\":\"TRANSITION_TO_ROLLING_MODEL\"},\"cutoffs\":{\"0\":{\"materiality_event_bound_90\":{\"QB\":9,\"RB\":4,\"WR\":3,\"TE\":3},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":54.716114872059215,\"RB\":24.318273276470762,\"WR\":18.23870495735307,\"TE\":18.23870495735307},\"cold_start_fallback_eligible\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light_fallback_eligible\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true}},\"1\":{\"materiality_event_bound_90\":{\"QB\":9.5625,\"RB\":4.25,\"WR\":3.1875,\"TE\":3.1875},\"minimum_supported_fp_stddev_for_non_material_fsffl\":{\"QB\":58.13587205156291,\"RB\":25.838165356250183,\"WR\":19.37862401718764,\"TE\":19.37862401718764},\"cold_start_fallback_eligible\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true},\"identity_light_fallback_eligible\":{\"QB\":true,\"RB\":true,\"WR\":true,\"TE\":true}}}},\"annual_rollover\":{\"mode\":\"deterministic annual refresh plus minimal governed freeze\",\"required_before_season_point_authority\":true,\"position_rates\":\"recompute from completed governed exact weekly seasons through target_year-1\",\"player_role_priors\":\"recompute cumulative prior opportunity/game sufficient statistics through target_year-1\",\"calibration\":\"same global train-only ratio by cutoff 2-17 over pseudo-current seasons 2022..target_year-1\",\"uncertainty\":\"for each position/cutoff c: max(prior_floor[p,c], prefix max of newly completed held-out residual RMSE[p,k] for all k<=c); floors remain monotone across cutoff\",\"materiality\":\"carry prior bound; take max with newly available all-population position historical maximum at cutoffs 0-17\",\"failure_behavior\":\"no point authority; explicit omission plus materiality gate if eligible, otherwise fail closed\"}}"
ROLLING_PRODUCTION_TABLE_SHA256 = hashlib.sha256(
    ROLLING_PRODUCTION_TABLE_JSON.encode("utf-8")
).hexdigest()


@dataclass(frozen=True)
class FumblesLostProductionTable:
    payload: Mapping[str, object]
    fingerprint: str

    @property
    def target_season(self) -> int:
        return int(self.payload["target_season"])

    @property
    def contract_version(self) -> str:
        return str(self.payload["contract_version"])

    @property
    def role_prior_games(self) -> float:
        return float(self.payload["role_prior_games"])

    @property
    def target_games(self) -> int:
        return int(self.payload["target_games"])

    @property
    def cold_start_floor(self) -> float:
        return float(self.payload["cold_start_floor"])

    @property
    def uncertainty_contract(self) -> str:
        return str(self.payload["uncertainty_contract"])

    @property
    def target_semantics(self) -> str:
        return str(self.payload["target_semantics"])

    @property
    def supported_completed_through_weeks(self) -> tuple[int, ...]:
        return tuple(
            int(value)
            for value in self.payload["supported_completed_through_weeks"]  # type: ignore[index]
        )

    def rolling_cutoff(self, completed_through_week: int) -> Mapping[str, object]:
        if completed_through_week not in self.supported_completed_through_weeks:
            raise ValueError(
                "first-party FUMBLES_LOST point authority requires completed Week 2-17"
            )
        return self.payload["cutoffs"][str(completed_through_week)]  # type: ignore[index]

    def calibration_scalar(self, completed_through_week: int) -> float:
        return float(self.rolling_cutoff(completed_through_week)["calibration_scalar"])

    def uncertainty_floor(
        self,
        completed_through_week: int,
        position: Position,
    ) -> float:
        value = float(
            self.rolling_cutoff(completed_through_week)["uncertainty_floor"][  # type: ignore[index]
                position.value
            ]
        )
        if not math.isfinite(value) or value <= 0:
            raise ValueError("frozen FUMBLES_LOST uncertainty floor must be positive")
        return value

    def materiality_event_bound(
        self,
        completed_through_week: int,
        position: Position,
    ) -> float:
        if completed_through_week in {0, 1}:
            row = self.payload["season_start"]["cutoffs"][str(completed_through_week)]  # type: ignore[index]
        elif 2 <= completed_through_week <= 17:
            row = self.rolling_cutoff(completed_through_week)
        else:
            raise ValueError(
                "no governed FUMBLES_LOST materiality bound exists for this cutoff"
            )
        value = float(row["materiality_event_bound_90"][position.value])  # type: ignore[index]
        if not math.isfinite(value) or value < 0:
            raise ValueError("frozen FUMBLES_LOST materiality bound is invalid")
        return value

    def fallback_eligible(
        self,
        completed_through_week: int | None,
        position: Position,
        evidence_tier: str,
    ) -> bool:
        if position not in _POSITIONS or completed_through_week is None:
            return False
        if completed_through_week in {0, 1}:
            row = self.payload["season_start"]["cutoffs"][str(completed_through_week)]  # type: ignore[index]
            full_matrix = row.get("fallback_eligibility")  # type: ignore[union-attr]
            if isinstance(full_matrix, Mapping):
                tier_row = full_matrix.get(evidence_tier)
                if not isinstance(tier_row, Mapping):
                    return False
                return bool(tier_row.get(position.value, False))
            if evidence_tier == "identity_light":
                return bool(
                    row["identity_light_fallback_eligible"][position.value]  # type: ignore[index]
                )
            if evidence_tier == "cold_start":
                return bool(
                    row["cold_start_fallback_eligible"][position.value]  # type: ignore[index]
                )
            return evidence_tier in {
                "history_plus_current",
                "history_only",
                "current_only",
            }
        if 2 <= completed_through_week <= 17:
            row = self.rolling_cutoff(completed_through_week)
            eligibility = row.get("fallback_eligibility")
            if not isinstance(eligibility, Mapping):
                return False
            tier_row = eligibility.get(evidence_tier)
            if not isinstance(tier_row, Mapping):
                return False
            value = tier_row.get(position.value)
            return value if isinstance(value, bool) else False
        return False


_FROZEN_2026 = FumblesLostProductionTable(
    payload=json.loads(ROLLING_PRODUCTION_TABLE_JSON),
    fingerprint=ROLLING_PRODUCTION_TABLE_SHA256,
)


def frozen_fumbles_lost_production_table_2026() -> FumblesLostProductionTable:
    return _FROZEN_2026


def resolve_fumbles_lost_production_table(
    season: int,
    *,
    table: FumblesLostProductionTable | None = None,
) -> FumblesLostProductionTable:
    candidate = table
    if candidate is None:
        if season != _FROZEN_2026.target_season:
            raise ValueError(
                "first-party FUMBLES_LOST target-season annual governed freeze is unavailable"
            )
        candidate = _FROZEN_2026
    if candidate.target_season != season:
        raise ValueError("FUMBLES_LOST production table target season does not match State")
    if candidate.target_semantics != "exact lost fumbles only":
        raise ValueError("FUMBLES_LOST production table lost exact target semantics")
    if candidate.role_prior_games != 4.0:
        raise ValueError("FUMBLES_LOST production table changed the four-game role prior")
    if candidate.target_games != 17:
        raise ValueError("FUMBLES_LOST production table changed season-equivalent target games")
    return candidate


def non_material_partial_passes(
    *,
    scoring_points_per_event: float,
    event_bound_90: float,
    supported_fantasy_point_stddev: float,
) -> tuple[bool, float, float]:
    if not math.isfinite(scoring_points_per_event):
        return False, math.inf, 0.0
    if not math.isfinite(event_bound_90) or event_bound_90 < 0:
        return False, math.inf, 0.0
    if (
        not math.isfinite(supported_fantasy_point_stddev)
        or supported_fantasy_point_stddev <= 0
    ):
        return False, abs(scoring_points_per_event) * event_bound_90, 0.0
    impact = abs(scoring_points_per_event) * event_bound_90
    allowance = (
        _NON_MATERIAL_FRACTION
        * _NON_MATERIAL_Z90
        * supported_fantasy_point_stddev
    )
    return impact <= allowance, impact, allowance


def _validate_annual_candidate_table_shape(
    candidate: FumblesLostProductionTable,
) -> None:
    """Fail closed on malformed governed-freeze structure before semantic checks."""

    if candidate.fingerprint != production_table_payload_fingerprint(candidate.payload):
        raise ValueError("annual FUMBLES_LOST production-table fingerprint does not match payload")

    try:
        supported = candidate.supported_completed_through_weeks
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            "annual FUMBLES_LOST supported cutoff set is incomplete"
        ) from exc
    if supported != _ROLLING_CUTOFFS:
        raise ValueError("annual FUMBLES_LOST supported cutoff set is incomplete")

    cutoffs = candidate.payload.get("cutoffs")
    if not isinstance(cutoffs, Mapping):
        raise ValueError("annual FUMBLES_LOST rolling cutoff table is incomplete")

    for cutoff in _ROLLING_CUTOFFS:
        row = cutoffs.get(str(cutoff))
        if not isinstance(row, Mapping):
            raise ValueError("annual FUMBLES_LOST rolling cutoff table is incomplete")

        try:
            scalar = float(row["calibration_scalar"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "annual FUMBLES_LOST calibration scalar matrix is incomplete"
            ) from exc
        if not math.isfinite(scalar) or scalar <= 0:
            raise ValueError(
                "annual FUMBLES_LOST calibration scalar must be finite and positive"
            )

        for field, label, require_positive in (
            ("uncertainty_floor", "uncertainty floor", True),
            ("materiality_event_bound_90", "materiality bound", False),
        ):
            matrix = row.get(field)
            if not isinstance(matrix, Mapping):
                raise ValueError(f"annual FUMBLES_LOST {label} matrix is incomplete")
            for position in _POSITIONS:
                try:
                    value = float(matrix[position.value])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(
                        f"annual FUMBLES_LOST {label} matrix is incomplete"
                    ) from exc
                if not math.isfinite(value) or (
                    value <= 0 if require_positive else value < 0
                ):
                    raise ValueError(f"annual FUMBLES_LOST {label} is invalid")

        eligibility = row.get("fallback_eligibility")
        if not isinstance(eligibility, Mapping):
            raise ValueError(
                "annual FUMBLES_LOST fallback eligibility matrix is incomplete"
            )
        for tier in (*_OBSERVED_FALLBACK_TIERS, "identity_light"):
            tier_row = eligibility.get(tier)
            if not isinstance(tier_row, Mapping):
                raise ValueError(
                    "annual FUMBLES_LOST fallback eligibility matrix is incomplete"
                )
            for position in _POSITIONS:
                if not isinstance(tier_row.get(position.value), bool):
                    raise ValueError(
                        "annual FUMBLES_LOST fallback eligibility matrix is incomplete"
                    )

    season_start = candidate.payload.get("season_start")
    if not isinstance(season_start, Mapping):
        raise ValueError("annual FUMBLES_LOST season-start authority is missing")
    season_start_cutoffs = season_start.get("cutoffs")
    if not isinstance(season_start_cutoffs, Mapping):
        raise ValueError("annual FUMBLES_LOST season-start authority is missing")
    for cutoff in (0, 1):
        row = season_start_cutoffs.get(str(cutoff))
        if not isinstance(row, Mapping):
            raise ValueError("annual FUMBLES_LOST season-start authority is incomplete")
        bounds = row.get("materiality_event_bound_90")
        if not isinstance(bounds, Mapping):
            raise ValueError(
                "annual FUMBLES_LOST season-start materiality matrix is incomplete"
            )
        for position in _POSITIONS:
            try:
                bound = float(bounds[position.value])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    "annual FUMBLES_LOST season-start materiality matrix is incomplete"
                ) from exc
            if not math.isfinite(bound) or bound < 0:
                raise ValueError(
                    "annual FUMBLES_LOST season-start materiality bound is invalid"
                )

        eligibility = row.get("fallback_eligibility")
        if not isinstance(eligibility, Mapping):
            raise ValueError(
                "annual FUMBLES_LOST season-start eligibility matrix is incomplete"
            )
        for tier in (*_OBSERVED_FALLBACK_TIERS, "identity_light"):
            tier_row = eligibility.get(tier)
            if not isinstance(tier_row, Mapping):
                raise ValueError(
                    "annual FUMBLES_LOST season-start eligibility matrix is incomplete"
                )
            for position in _POSITIONS:
                if not isinstance(tier_row.get(position.value), bool):
                    raise ValueError(
                        "annual FUMBLES_LOST season-start eligibility matrix is incomplete"
                    )


def validate_annual_rollover_candidate(
    candidate: FumblesLostProductionTable,
    *,
    prior: FumblesLostProductionTable,
    newly_completed_heldout_rmse: Mapping[str, Mapping[int, float]],
    newly_completed_materiality_event_max: Mapping[str, Mapping[int, float]],
    observed_population_coverage: Mapping[
        str,
        Mapping[int, Mapping[str, float]],
    ],
) -> None:
    """Validate the frozen 2027+ minimal annual rollover invariants.

    This does not fit/search a model family. It only verifies a separately generated
    target-season freeze before point authority can be consumed.
    """

    if candidate.target_season != prior.target_season + 1:
        raise ValueError("annual FUMBLES_LOST freeze must advance exactly one target season")
    _validate_annual_candidate_table_shape(candidate)
    resolve_fumbles_lost_production_table(candidate.target_season, table=candidate)
    annual = candidate.payload.get("annual_freeze")
    if not isinstance(annual, Mapping):
        raise ValueError("annual FUMBLES_LOST freeze identity/source hashes are missing")
    hashes = annual.get("exact_source_hashes")
    urls = annual.get("exact_source_urls")
    captures = annual.get("source_captured_at")
    built_at = annual.get("built_at")
    seasons = annual.get("training_seasons")
    if not isinstance(hashes, Mapping) or not hashes:
        raise ValueError("annual FUMBLES_LOST freeze requires exact source hashes")
    if not isinstance(urls, Mapping) or set(urls) != set(hashes):
        raise ValueError("annual FUMBLES_LOST freeze requires exact source URLs")
    if not isinstance(captures, Mapping) or set(captures) != set(hashes):
        raise ValueError("annual FUMBLES_LOST freeze requires source capture timestamps")
    parsed_captures: list[datetime] = []
    for source_name, source_hash in hashes.items():
        text = str(source_hash)
        if (
            not str(source_name).strip()
            or len(text) != 64
            or any(char not in "0123456789abcdef" for char in text.lower())
        ):
            raise ValueError("annual FUMBLES_LOST freeze source hash is invalid")
        if not str(urls[source_name]).strip():
            raise ValueError("annual FUMBLES_LOST freeze source URL is invalid")
        try:
            captured = datetime.fromisoformat(str(captures[source_name]))
        except ValueError as exc:
            raise ValueError(
                "annual FUMBLES_LOST freeze source capture timestamp is invalid"
            ) from exc
        if captured.tzinfo is None:
            raise ValueError(
                "annual FUMBLES_LOST freeze source capture timestamp must be timezone-aware"
            )
        parsed_captures.append(captured)
    try:
        built = datetime.fromisoformat(str(built_at))
    except ValueError as exc:
        raise ValueError("annual FUMBLES_LOST freeze build timestamp is invalid") from exc
    if built.tzinfo is None:
        raise ValueError("annual FUMBLES_LOST freeze build timestamp must be timezone-aware")
    if parsed_captures and built < max(parsed_captures):
        raise ValueError("annual FUMBLES_LOST freeze cannot predate source capture")
    if not isinstance(seasons, list) or not seasons:
        raise ValueError("annual FUMBLES_LOST freeze requires completed training seasons")
    normalized_seasons = tuple(int(season) for season in seasons)
    if max(normalized_seasons) >= candidate.target_season:
        raise ValueError("annual FUMBLES_LOST freeze contains target/future-season outcomes")
    if prior.target_season not in normalized_seasons:
        raise ValueError("annual FUMBLES_LOST freeze omits the newly completed season")
    pseudo_current = annual.get("calibration_pseudo_current_seasons")
    expected_pseudo_current = list(range(2022, candidate.target_season))
    if list(pseudo_current or ()) != expected_pseudo_current:
        raise ValueError(
            "annual FUMBLES_LOST pseudo-current calibration seasons violate chronology"
        )
    if annual.get("chronology_validation_passed") is not True:
        raise ValueError(
            "annual FUMBLES_LOST freeze lacks chronology/no-future-leakage validation"
        )

    position_rates = annual.get("position_lost_fumble_per_opportunity")
    position_roles = annual.get("position_opportunity_per_game")
    player_priors = annual.get("player_role_priors")
    prior_fingerprint = str(
        annual.get("player_prior_sufficient_statistics_fingerprint") or ""
    )
    if not isinstance(position_rates, Mapping) or not isinstance(position_roles, Mapping):
        raise ValueError("annual FUMBLES_LOST freeze requires refreshed position rates")
    if not isinstance(player_priors, Mapping):
        raise ValueError("annual FUMBLES_LOST freeze requires refreshed player role priors")
    if prior_fingerprint != production_table_payload_fingerprint(
        {"player_role_priors": player_priors}
    ):
        raise ValueError("annual FUMBLES_LOST player-prior fingerprint does not match payload")

    for player_id, row in player_priors.items():
        if not str(player_id).strip() or not isinstance(row, Mapping):
            raise ValueError("annual FUMBLES_LOST player role prior is invalid")
        try:
            position = Position(str(row["position"]))
            history_games = int(row["history_games"])
            history_opportunities = float(row["history_opportunities"])
            identity_method = str(row["identity_method"]).strip()
            accepted_tier = str(row["accepted_tier"]).strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "annual FUMBLES_LOST player role prior is incomplete"
            ) from exc
        if position not in _POSITIONS:
            raise ValueError("annual FUMBLES_LOST player role prior position is invalid")
        if (
            history_games < 0
            or not math.isfinite(history_opportunities)
            or history_opportunities < 0
            or not identity_method
            or not accepted_tier
        ):
            raise ValueError("annual FUMBLES_LOST player role prior is invalid")

    for position in _POSITIONS:
        for label, mapping in (
            ("lost-fumble rate", position_rates),
            ("opportunity/game prior", position_roles),
        ):
            try:
                value = float(mapping[position.value])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"annual FUMBLES_LOST {label} is incomplete"
                ) from exc
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"annual FUMBLES_LOST {label} must be finite and positive")

    for cutoff in _ROLLING_CUTOFFS:
        scalar = candidate.calibration_scalar(cutoff)
        if not math.isfinite(scalar) or scalar <= 0:
            raise ValueError("annual FUMBLES_LOST calibration scalar must be finite and positive")

    for position in _POSITIONS:
        position_rmse = newly_completed_heldout_rmse.get(position.value)
        if not isinstance(position_rmse, Mapping):
            raise ValueError("annual held-out FUMBLES_LOST RMSE matrix is incomplete")
        missing_cutoffs = [
            cutoff for cutoff in _ROLLING_CUTOFFS if cutoff not in position_rmse
        ]
        if missing_cutoffs:
            raise ValueError("annual held-out FUMBLES_LOST RMSE matrix is incomplete")

        prefix_rmse = 0.0
        prior_candidate_floor = 0.0
        for cutoff in _ROLLING_CUTOFFS:
            prior_floor = prior.uncertainty_floor(cutoff, position)
            heldout = float(position_rmse[cutoff])
            if not math.isfinite(heldout) or heldout < 0:
                raise ValueError("annual held-out FUMBLES_LOST RMSE is invalid")
            prefix_rmse = max(prefix_rmse, heldout)
            candidate_floor = candidate.uncertainty_floor(cutoff, position)
            if (
                candidate_floor < prior_floor
                or candidate_floor < prefix_rmse
                or candidate_floor < prior_candidate_floor
            ):
                raise ValueError(
                    "annual FUMBLES_LOST uncertainty floor violates monotone prefix freeze"
                )
            prior_candidate_floor = candidate_floor

        position_maxima = newly_completed_materiality_event_max.get(position.value)
        if not isinstance(position_maxima, Mapping):
            raise ValueError("annual FUMBLES_LOST materiality maximum matrix is incomplete")
        position_coverage = observed_population_coverage.get(position.value)
        if not isinstance(position_coverage, Mapping):
            raise ValueError("annual FUMBLES_LOST population coverage matrix is incomplete")

        for cutoff in _MATERIALITY_CUTOFFS:
            if cutoff not in position_maxima:
                raise ValueError("annual FUMBLES_LOST materiality maximum matrix is incomplete")
            new_maximum = float(position_maxima[cutoff])
            if not math.isfinite(new_maximum) or new_maximum < 0:
                raise ValueError("annual FUMBLES_LOST materiality maximum is invalid")
            if candidate.materiality_event_bound(cutoff, position) < max(
                prior.materiality_event_bound(cutoff, position),
                new_maximum,
            ):
                raise ValueError(
                    "annual FUMBLES_LOST materiality bound omits newly completed maximum"
                )

            cutoff_coverage = position_coverage.get(cutoff)
            if not isinstance(cutoff_coverage, Mapping):
                raise ValueError(
                    "annual FUMBLES_LOST population coverage matrix is incomplete"
                )
            for tier in _OBSERVED_FALLBACK_TIERS:
                if tier not in cutoff_coverage:
                    raise ValueError(
                        "annual FUMBLES_LOST population coverage matrix is incomplete"
                    )
                coverage = float(cutoff_coverage[tier])
                if not math.isfinite(coverage) or not 0 <= coverage <= 1:
                    raise ValueError("annual FUMBLES_LOST population coverage is invalid")
                if candidate.fallback_eligible(cutoff, position, tier) and coverage < 0.90:
                    raise ValueError(
                        "annual FUMBLES_LOST fallback-eligible population misses 90% coverage gate"
                    )

            if candidate.fallback_eligible(
                cutoff,
                position,
                "identity_light",
            ) and not candidate.fallback_eligible(
                cutoff,
                position,
                "cold_start",
            ):
                raise ValueError(
                    "annual FUMBLES_LOST identity-light eligibility exceeds cold-start support"
                )

