from fsffl.product.career_coverage import (
    BoundedCareerEvidenceCache,
    build_career_position_depth_refresh,
    evidence_fingerprint,
    resolve_career_coverage,
    select_career_coverage,
    select_explore_career_cohort,
)


def test_roster_waiver_and_newly_rostered_out_of_pool_share_one_batch():
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
