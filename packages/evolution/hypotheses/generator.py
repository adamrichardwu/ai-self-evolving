from dataclasses import dataclass


@dataclass(slots=True)
class HypothesisDraft:
    title: str
    description: str
    confidence_score: float
    risk_level: str


def generate_hypothesis_from_failure(cluster_signature: str) -> HypothesisDraft:
    return HypothesisDraft(
        title="Add explicit planning step",
        description=f"Generated from failure cluster: {cluster_signature}",
        confidence_score=0.5,
        risk_level="medium",
    )
