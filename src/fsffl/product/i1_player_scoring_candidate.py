"""Compatibility surface for the completed league-agnostic scoring gate.

The authoritative production implementation now lives in
:mod:`fsffl.product.i1_player_scoring`. This module remains only so the prior
gate evidence and tests retain a stable import path.
"""

from .i1_player_scoring import (
    FUTURE_I1_PLAYER_SCORING_VERSION,
    build_future_i1_player_scoring_multipliers,
    player_scoring_multipliers,
    translate_future_i1_result,
    translate_future_i1_result_for_player,
)

FUTURE_I1_PLAYER_SCORING_CANDIDATE_VERSION = FUTURE_I1_PLAYER_SCORING_VERSION

__all__ = (
    "FUTURE_I1_PLAYER_SCORING_CANDIDATE_VERSION",
    "FUTURE_I1_PLAYER_SCORING_VERSION",
    "build_future_i1_player_scoring_multipliers",
    "player_scoring_multipliers",
    "translate_future_i1_result",
    "translate_future_i1_result_for_player",
)
