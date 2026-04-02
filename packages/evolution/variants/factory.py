from packages.domain.models.variant import Variant
from packages.evolution.hypotheses.generator import HypothesisDraft


def build_variant(hypothesis: HypothesisDraft) -> Variant:
    return Variant(
        mutation_type="workflow",
        expected_gain=hypothesis.confidence_score,
        budget_limit=25.0,
        risk_level=hypothesis.risk_level,
    )
