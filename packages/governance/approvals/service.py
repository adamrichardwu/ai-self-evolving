def can_promote_variant(utility_score: float, safety_passed: bool) -> bool:
    return safety_passed and utility_score > 0.0
