# Participation-adjusted current-season Simulation

After completed NFL games exist, current competitive outcomes consume the existing
governed, participation-adjusted rest-of-season Forecast. Frozen preseason raw and
league-scored observations remain intact for comparison, valuation and history.
No injury-status override, source eligibility rule, fumbles model, volatility
calibration, Intrinsic formula or Shapley method is changed.

The existing season-comparison producer publishes typed forward observations and
season-outlook observations alongside its player display rows. The owned refresh
prepares that cohort under its existing Forecast heavy-work claim before building
Simulation. Compact forward observations are carried separately in Forecast
runtime evidence and participate in its existing artifact fingerprint. Current
Position & Depth reuses the same prepared season outlook (actuals plus ROS).
Late presentation retries cannot independently replace a cohort already used by
core Simulation. Readers and trade requests never fetch projections or rebuild
this producer.

Simulation consumes native `REST_OF_SEASON` observations. It preserves completed
matchup results and applies forward production only to remaining fantasy weeks,
including the configured postseason. Player means are spread equally over their
remaining eligible NFL games through Week 18, accounting for remaining byes and
exact canonical weekly unavailability. Weekly lineup choices use the resulting
per-active-game means, so different remaining schedules do not misorder starters.
The existing calibrated weekly-volatility model is unchanged. A zero ROS projection
has zero forward mean and variance; legal bench substitution remains available.
An IR flag alone does not establish a return date or season-ending absence. The
existing Forecast participation/source rules still decide whether a player gets a
current projection, a permitted fallback or a labeled zero-production assumption.
Uniform forward allocation remains a provisional weekly bridge; it does not model
an unobserved injury-return date.

The State capture timestamp and Forecast evaluation cutoff are separate, visible
coordinates. State identity and timestamps are never rewritten or forecasts
backdated. Analytics carries an optional explicit Forecast evaluation cutoff,
bounded between State capture and generation; without it the original strict
State-time evidence cutoff remains in force.

Baseline and post-trade calculations use identical forward evidence. Scenario
fingerprints include those observations; confirmation rejects an old-season or
otherwise incompatible baseline. Preliminary roster screens and strategic search
consume the same forward context when prepared, preserving separate future-horizon
and Market channels. A preliminary screen is still not a win/playoff forecast.
Existing full-season-only diagnostic compositions retain their legacy context;
they cannot confirm in-season competitive consequences.

Missing active-roster ROS coverage is not zero and is not repaired by silently
reintroducing preseason projections or positional-floor forecasts. A complete ROS
source outage that yields only a remaining-preseason prior withholds current
Simulation authority. Unsupported coverage stays explicit across league formats.
At the end of Week 18, the producer retains actuals and no forward Simulation is
requested. Preseason behavior remains unchanged.

Simulation versioning invalidates previous computed baselines. Old full-season
Forecast artifact fingerprints remain exact when optional forward fields are
absent. Deployment therefore requires a normal owned refresh before in-season
trade confirmation is available. Old display comparison artifacts lack typed
forward observations and cannot be reverse-engineered into authoritative Forecast
inputs. Validation must distinguish local synthetic end-to-end tests from a new
production publication and hosted authenticated confirmation.

The existing two-State comparison cache stays bounded. Typed forward and outlook
rows add linear retained/serialized bytes; there is no per-candidate cohort copy,
new cache/worker/queue or new persistence connection owner. Reusing the cohort
removes the formerly separate Current Position & Depth acquisition during
publication. Hosted peak memory and whole-refresh duration still require normal
run measurements; local fixtures do not establish those numbers.

Expected coverage gaps withhold only current Simulation authority. Their player
identities are exposed explicitly; the owned refresh can still publish coherent
Forecast, Value and Intrinsic evidence. Fast trade analysis retains Market
accounting while current roster consequences stay unavailable, and broad search
can retain structural/future hypotheses without inventing missing current points.
Confirmed season-ending facts distinguish full-season absence from absence after
a specified completed week, preserving earned actuals and the historical capture
fence.

From the November 12 policy admission, fresh, explicit NFL practice-squad evidence
supports a labeled low-confidence zero-ROS assumption when a healthy, nonempty
provider cohort has no raw projection row for the player. Any player row,
including an incomplete projection, vetoes this exception. This rule applies to
all offensive positions and does not require low prior production or a named
player exception. Fantasy TAXI placement alone is insufficient. Match canonical
identity, NFL club, position, season and evaluation cutoff; role evidence expires
after six hours, and a newer verified promotion revokes it. Acquisition reuses
the existing bounded producer-owned roster check; readers never fetch rosters.
Earned actuals, frozen preseason comparisons and accepted future-year forecasts
remain intact. Historical evaluations before policy admission retain their prior
policy identity and cannot acquire later role facts.
