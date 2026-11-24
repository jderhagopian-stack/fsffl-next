"""Present the Decision-owned preliminary priority interpretation."""
from fsffl.trade_decision.discovery_priorities import assess_discovery_priorities


def discovery_display_context(row):
    return assess_discovery_priorities(row)
