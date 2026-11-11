# Career single-source completion

Career Year-1 assembly accepts a complete single-provider ROS coordinate even
when the captured NFL depth order is missing or indicates a starter. Provider
completeness is evidence of a projection; backup status is not a scoring input.
This implements the existing universal single-source completion rule.

The older Career builder limited this route to `_active_backup_player_ids`.
That could reject a player whom Forecast had already scored on a card, leave
Career/3-Year coverage incomplete, and correctly prevent the downstream chart
from publishing league-wide positional ranks. The chart must retain its strict
all-team completeness requirement.

The correction admits a provider row only after the existing identity, period,
cutoff, standard-scoring and league-scoring checks. Missing fumbles lost uses the
accepted first-party supplement; an already complete provider fumbles coordinate
is retained. Other missing required metrics still fail. Approved unsigned and
nonparticipation precedence is unchanged. No missing player is silently zeroed.

The role-independent correction has its own effective timestamp and dependency
fingerprint. Pinned earlier captures retain the prior admission and artifact
identity; a new capture cannot reuse an old incomplete Career result. Historical
snapshots and preseason projections are preserved.

The existing acquired source rows and batch fumbles supplement are reused. There
is no new provider request, queue, cache, raw-data copy or persistence adapter.
Newly admitted players proceed through the existing future/Career calculations.
Regressions exercise the real Year-1/P0 producer for all four positions with
missing/starter depth, strict missing-metric rejection, provider/model fumbles,
unsigned precedence and historical dependency identity.
