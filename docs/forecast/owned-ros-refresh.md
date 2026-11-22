# Current ROS evidence during owned refresh

The owned Forecast preparation attempts current configured ROS providers even
when exact-window history already contains both provider slots. Previously,
supplementing only missing providers could keep the same saved pair indefinitely
within a window. Native current snapshots pass the existing Forecast normalizer;
research captures from other structural windows are not substituted or relabeled.

## Ownership and continuity

- The existing owned refresh forces its comparison preparation once, under its
  existing heavy-work claim. Later preparation/read calls reuse that result.
- Product GETs, startup restore and stored-only replay do not opt into refresh.
- `build_in_season_forecasts(refresh_sources=True)` tries configured providers.
  Accepted normalized current evidence replaces that provider's retained vote.
- Fetch/normalization failure retains admissible same-window history for that
  provider. Its original timestamps and source version remain intact, and the
  fresh-source error remains recorded. Wrong windows remain excluded.
- Independent-source requirements, scoring, participation exceptions, frozen
  preseason comparison/Y1, Simulation and Intrinsic formulas remain unchanged.

## Resource effect and acceptance

At most the two existing configured ROS fetchers are added to an owned
preparation that formerly fetched none when history was complete. Existing
provider concurrency/timeouts, history writer and deduplication are reused; no
new cache, queue, service, scheduler or credentials. New accepted revisions use
the existing persistence transport. This intentionally creates new receipts when
sources change; record request/write counts, bytes and preparation time during
hosted acceptance. It is not a claim of lower full-refresh memory or latency.

Tests cover replacement without duplicate votes, failed fetch/normalization,
retained source vintage, wrong-window rejection, unchanged stored-only replay,
and one owned preparation followed by reader reuse. Hosted acceptance requires
actual source receipts for the newly published exact State; successful tests do
not certify source freshness or physical mobile rendering. Partial-week lineup
locks and source-quality research remain separate; no new weekly Forecast
methodology or historical numerical authority is introduced here.
