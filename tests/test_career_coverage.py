from fsffl.product.career_coverage import (
    BoundedCareerEvidenceCache,
    build_career_position_depth_refresh,
    evidence_fingerprint,
    resolve_career_coverage,
    select_career_coverage,
    select_explore_career_cohort,
)


def test_roster_bounded_explore_and_newly_rostered_out_of_pool_share_one_batch():
    state = [
        {"player_id": "sleeper:player:ref", "position": "QB", "nfl_team": "KC"},
        {"player_id": "sleeper:player:pool", "position": "WR", "nfl_team": "SF"},
        {"player_id": "sleeper:player:deep", "position": "TE", "nfl_team": "BUF"},
    ]
    original_roster = [{"player_id": "sleeper:player:ref", "position": "QB", "team_id": "t1",
                        "roster_slot": "STARTER", "state_hash": "state-1"}]
    # This candidate is absent from the precomputed set. A subsequent State
    # shows it newly acquired on IR; exact-State roster selection must include it.
    acquired_roster = [{**original_roster[0], "state_hash": "state-2"}, {"player_id": "sleeper:player:deep", "position": "TE",
        "team_id": "t1", "roster_slot": "IR", "state_hash": "state-2"}]
    calls = []

    def accepted_materializer(subjects, packets):
        calls.append((tuple(s.player_id for s in subjects), dict(packets)))
        # Test contract: supplied accepted-model packet yields one authority;
        # this fixture tests selection/batching, not valuation math.
        return {s.player_id: {"evidence": packets[s.player_id]} for s in subjects}

    result = resolve_career_coverage(
        state_players=state, roster_rows=acquired_roster, state_hash="state-2",
        precomputed_player_ids={"sleeper:player:pool"},
        evidence_by_player={p["player_id"]: {"source": "approved", "value": 1}
                            for p in state},
        materialize_batch=accepted_materializer,
    )
    assert len(calls) == 1
    assert {s.player_id for s in result.subjects} == {
        "sleeper:player:ref", "sleeper:player:pool", "sleeper:player:deep"
    }
    deep = next(s for s in result.subjects if s.player_id.endswith(":deep"))
    assert (deep.source, deep.team_id, deep.roster_slot) == ("exact_state_roster", "t1", "IR")
    assert "sleeper:player:deep" in result.authority
    refresh = build_career_position_depth_refresh(
        state_hash="state-2", roster_rows=acquired_roster, subjects=result.subjects,
        authority={"sleeper:player:ref": {"estimate": "preserved"}},
        partial_authority={"sleeper:player:deep": {"y4_y7": "available"}},
        failures={"sleeper:player:deep": "current_shapley_contract_missing"},
    )
    assert len(refresh) == 2
    assert next(x for x in refresh if x["player_id"].endswith(":deep"))["career_coverage_status"] == "career_authority_partial"


def test_nfl_attached_unrostered_pool_is_not_selected_by_default():
    state = [
        {"player_id": f"waiver:{i}", "position": "WR", "nfl_team": "SF"}
        for i in range(500)
    ]
    selected = select_career_coverage(
        state_players=state,
        roster_rows=[],
        state_hash="state-bounded",
        precomputed_player_ids={"waiver:12", "waiver:37"},
    )
    assert [row.player_id for row in selected] == ["waiver:12", "waiver:37"]
    assert all(row.source == "waiver_pool" for row in selected)


def test_missing_evidence_is_explicit_and_never_sent_as_zero():
    state = [{"player_id": "sleeper:player:rookie", "position": "RB", "nfl_team": "CHI"}]
    calls = []
    result = resolve_career_coverage(
        state_players=state, roster_rows=[{"player_id": "sleeper:player:rookie", "position": "RB",
            "team_id": "t", "roster_slot": "TAXI", "state_hash": "s"}], state_hash="s",
        evidence_by_player={}, materialize_batch=lambda subjects, evidence: calls.append(evidence) or {},
    )
    assert result.missing == {"sleeper:player:rookie": "governed_player_evidence_packet_unavailable"}
    assert calls == []


def test_unknown_on_demand_identity_is_explicit_without_fabricated_subject():
    called = []
    result = resolve_career_coverage(
        state_players=[], roster_rows=[], state_hash="s", evidence_by_player={},
        on_demand_player_ids=iter(["sleeper:player:outside"]),
        materialize_batch=lambda subjects, evidence: called.append(subjects) or {},
    )
    assert result.missing == {
        "sleeper:player:outside": "canonical_player_absent_from_exact_state_identity_universe"
    }
    assert called == []


def test_cache_fingerprint_is_dependency_scoped_and_bounded():
    packet = {"source": "approved", "as_of": "2026-10-08", "stats": [1, 2]}
    key = evidence_fingerprint(model_digest="m", scoring_digest="s", evidence_packet=packet)
    assert key == evidence_fingerprint(model_digest="m", scoring_digest="s", evidence_packet=packet)
    assert key != evidence_fingerprint(model_digest="other", scoring_digest="s", evidence_packet=packet)
    cache = BoundedCareerEvidenceCache(max_entries=2)
    cache.put("1", 1); cache.put("2", 2); cache.get("1"); cache.put("3", 3)
    assert len(cache) == 2 and cache.get("2") is None and cache.get("1") == 1


def test_explore_career_cohort_is_bounded_supported_and_deterministic():
    candidates = [
        {"player_id": "waiver:c", "source": "waiver_pool", "career_supported": True, "opportunity_score": 8},
        {"player_id": "waiver:a", "source": "waiver_pool", "career_supported": True, "opportunity_score": 8},
        {"player_id": "waiver:b", "source": "waiver_pool", "career_supported": True, "opportunity_score": 5},
        {"player_id": "waiver:unsupported", "source": "waiver_pool", "career_supported": False, "opportunity_score": 100},
        {"player_id": "rostered", "source": "exact_state_roster", "career_supported": True, "opportunity_score": 200},
    ]
    selected = select_explore_career_cohort(candidate_rows=candidates, max_candidates=2)
    assert [row["player_id"] for row in selected] == ["waiver:a", "waiver:c"]
    assert len(selected) <= 2
    assert all(row["source"] == "waiver_pool" and row["career_supported"] for row in selected)


def test_explore_career_cohort_fails_closed_on_missing_or_invalid_signal():
    import pytest

    base = {"player_id": "waiver:x", "source": "waiver_pool", "career_supported": True}
    with pytest.raises(ValueError, match="requires governed opportunity_score"):
        select_explore_career_cohort(candidate_rows=[base])
    with pytest.raises(ValueError, match="invalid opportunity_score"):
        select_explore_career_cohort(candidate_rows=[{**base, "opportunity_score": float("nan")}])
    with pytest.raises(ValueError, match="between 1 and 100"):
        select_explore_career_cohort(candidate_rows=[], max_candidates=101)



def test_position_depth_publication_fails_closed_on_state_mismatch():
    import pytest

    subjects = select_career_coverage(
        state_players=[{"player_id": "p1", "position": "WR"}],
        roster_rows=[{"player_id": "p1", "position": "WR", "team_id": "t1",
                      "roster_slot": "IR", "state_hash": "state-2"}],
        state_hash="state-2",
    )
    with pytest.raises(ValueError, match="another State"):
        build_career_position_depth_refresh(
            state_hash="state-2",
            roster_rows=[{"player_id": "p1", "position": "WR", "team_id": "t1",
                          "roster_slot": "IR", "state_hash": "state-1"}],
            subjects=subjects,
            authority={"p1": {"career": 42.0}},
            failures={},
        )


def test_newly_rostered_outside_precomputed_resolves_identity_and_provider_fixture():
    """Exercise canonical identity -> provider packet -> Career batch without I/O."""
    canonical_id = "sleeper:player:outside-9002"
    provider_identity = "nfl:gsis:00-0039002"
    state_hash = "exact-state-new"
    state_players = [
        {"player_id": canonical_id, "position": "TE", "nfl_team": "BUF"},
    ]
    roster_rows = [
        {"player_id": canonical_id, "position": "TE", "team_id": "team-2",
         "roster_slot": "IR", "state_hash": state_hash},
    ]

    # Fixture identity map and provider response stand in for the existing
    # governed acquisition boundary. No network/provider call is made.
    identity_map = {provider_identity: canonical_id}
    identity_requests = []
    provider_requests = []

    def resolve_identity(external_id):
        identity_requests.append(external_id)
        return identity_map.get(external_id)

    resolved_id = resolve_identity(provider_identity)
    assert resolved_id == canonical_id
    packet = {"player_id": resolved_id, "source": "approved-provider-fixture",
              "as_of": "2026-10-11T14:00:00Z", "projection": {"Y1": 42.0}}
    provider_requests.append(resolved_id)
    assert packet["player_id"] == canonical_id

    materialized = []
    result = resolve_career_coverage(
        state_players=state_players,
        roster_rows=roster_rows,
        state_hash=state_hash,
        precomputed_player_ids=(),
        evidence_by_player={resolved_id: packet},
        materialize_batch=lambda subjects, packets: (
            materialized.append((subjects, packets))
            or {subject.player_id: {"career": 42.0} for subject in subjects}
        ),
    )

    assert identity_requests == [provider_identity]
    assert provider_requests == [canonical_id]
    assert len(materialized) == 1
    assert [subject.player_id for subject in materialized[0][0]] == [canonical_id]
    assert materialized[0][1][canonical_id] == packet
    assert result.authority[canonical_id] == {"career": 42.0}
    assert result.missing == {}
    assert result.subjects[0].source == "exact_state_roster"


def test_matching_state_publication_accounts_for_all_roster_rows_and_failures():
    state_hash = "exact-state-3"
    state_players = [
        {"player_id": "p1", "position": "QB"},
        {"player_id": "p2", "position": "WR"},
    ]
    roster_rows = [
        {"player_id": "p1", "position": "QB", "team_id": "t1",
         "roster_slot": "STARTER", "state_hash": state_hash},
        {"player_id": "p2", "position": "WR", "team_id": "t2",
         "roster_slot": "BENCH", "state_hash": state_hash},
    ]
    subjects = select_career_coverage(
        state_players=state_players, roster_rows=roster_rows, state_hash=state_hash,
    )
    refresh = build_career_position_depth_refresh(
        state_hash=state_hash,
        roster_rows=roster_rows,
        subjects=subjects,
        authority={"p1": {"raw_career_forward_reference": 120.0}},
        partial_authority={"p2": {"y4_y7": 10.0}},
        failures={"p2": "p0_year1_evidence_incomplete"},
    )

    assert [row["player_id"] for row in refresh] == ["p1", "p2"]
    assert all(row["state_hash"] == state_hash for row in refresh)
    published = {row["player_id"]: row for row in refresh}
    assert published["p1"]["career_coverage_status"] == "career_authority_available"
    assert published["p1"]["team_id"] == "t1"
    assert published["p1"]["roster_slot"] == "STARTER"
    assert published["p2"]["career_coverage_status"] == "career_authority_partial"
    assert published["p2"]["career_failure_reason"] == "p0_year1_evidence_incomplete"
    assert published["p2"]["team_id"] == "t2"
    assert published["p2"]["roster_slot"] == "BENCH"


def test_missing_canonical_roster_identity_does_not_blank_position_depth_payload():
    state_hash = "exact-state-with-unknown-roster-id"
    roster_rows = [
        {"player_id": "p1", "position": "QB", "team_id": "t1",
         "roster_slot": "STARTER", "state_hash": state_hash},
        {"player_id": "p-outside", "position": "WR", "team_id": "t2",
         "roster_slot": "IR", "state_hash": state_hash},
    ]
    batch = resolve_career_coverage(
        state_players=[{"player_id": "p1", "position": "QB"}],
        roster_rows=roster_rows,
        state_hash=state_hash,
        evidence_by_player={"p1": {"source": "accepted", "packet": "fixture"}},
        materialize_batch=lambda subjects, packets: {"p1": {"career": 10.0}},
    )

    refresh = build_career_position_depth_refresh(
        state_hash=state_hash,
        roster_rows=roster_rows,
        subjects=batch.subjects,
        authority=batch.authority,
        failures=batch.missing,
    )

    assert [row["player_id"] for row in refresh] == ["p-outside", "p1"]
    unknown = next(row for row in refresh if row["player_id"] == "p-outside")
    assert unknown == {
        "state_hash": state_hash,
        "player_id": "p-outside",
        "position": "WR",
        "team_id": "t2",
        "roster_slot": "IR",
        "career_coverage_status": "career_authority_failure",
        "career_failure_reason": "canonical_player_absent_from_exact_state_identity_universe",
    }
