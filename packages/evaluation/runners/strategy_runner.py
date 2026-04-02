from packages.domain.models.variant import Variant


def evaluate_strategy_variant(variant: Variant) -> dict[str, float | str]:
    return {
        "variant_id": variant.id,
        "benchmark_score": 0.0,
        "utility_score": 0.0,
        "verdict": "needs_review",
    }
