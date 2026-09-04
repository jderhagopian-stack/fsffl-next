# Canonical Domain Model

This document defines the initial NEXT-0 domain vocabulary. These are conceptual contracts first; implementation types may evolve after review.

## Identity and configuration

### User
A platform user. User identity must not be embedded in model logic.

### League
Persistent league identity plus platform/provider references.

### LeagueRules
Scoring, roster slots, taxi/IR rules, draft structure, keeper/dynasty settings, transaction rules, playoff structure, and other rule-defined constraints.

### Team
Persistent franchise identity within a league.

## Point-in-time state

### LeagueState
Canonical snapshot at `as_of` time. References exact rule, data, provider, and model-context versions needed for reproducibility.

### TeamState
Roster, picks, record, standings context, lineup eligibility, taxi/IR, transaction assets, calculated competitive state, and explicit owner strategic posture if supplied.

### PlayerState
What was known about a player at `as_of`: identity, age, NFL context, availability/injury status, role evidence, contract/draft metadata, and source provenance.

### PickState
Season, round, original owner, current owner, known draft-order information, uncertainty, and point-in-time provenance. Historical pick value may not use future realized slot information unless it was already known.

### MarketState
Point-in-time external market observations, with source, timestamp, licensing/provenance metadata, and uncertainty/coverage notes.

## Forecast objects

### ProjectionDistribution
A probabilistic forecast over a defined horizon and metric family, with ensemble components, uncertainty, evidence date, and model version.

### AssetOutcomeDistribution
Longer-horizon outcome distribution for a player, pick, or other dynasty asset.

### CompetitiveOutcomeDistribution
Team/league simulation output such as expected wins, playoff probability, title probability, points, or finish distribution.

## Value objects

### MarketPrice
Observed/estimated exchange value in the current market.

### IntrinsicAssetValue
Model-derived dynasty value before team-specific fit.

### TeamSpecificAssetValue
Marginal value of an asset to a specific TeamState.

### TransactionPriceEstimate
Estimated price required to transact, distinct from intrinsic value.

### FranchiseUtility
Multi-horizon utility representation for a TeamState.

## Decision objects

### Transaction
A proposed state transition involving one or more teams and assets.

### DecisionEvaluation
Before/after franchise utility, uncertainty, competitive impact, roster impact, market context, and explanation for each affected team.

### NegotiationFrontier
Set of feasible packages and bilateral utility/acceptance estimates around a transaction target.

### Opportunity
A candidate action that survives generation, evaluation, plausibility, and ranking requirements.

## Governance objects

### EvidenceRecord
Source, observation date, effective date, rights/provenance, quality, scope, and reproducibility metadata.

### ParameterEstimate
Definition, update mode, estimate/distribution, uncertainty, evidence set, dependencies, model version, and lifecycle status.

### ModelVersion
Immutable identifier for a coherent set of logic, parameters, provider versions, and schema contracts.

## Design rule

Objects that represent materially different concepts must remain separately typed even when they can be projected onto a common numeric scale. In particular, market price, intrinsic value, team-specific value, and transaction price are not aliases.
