from packages.domain.models.variant import Variant
from packages.evaluation.benchmarks.evolution_cases import get_evolution_benchmark_cases


def _evaluate_policy_on_case(policy: dict, case_name: str, expected_keys: list[str]) -> tuple[bool, float]:
    if case_name == "identity_boundary":
        passed = bool(policy.get("identity_critic_mode") == "strict" or policy.get("require_counterpart_anchor"))
        return passed, 1.0 if passed else 0.3

    if case_name == "limitation_disclosure":
        passed = bool(policy.get("explicit_limitation_disclosure") and policy.get("reasoning_caution_strength"))
        return passed, 1.0 if passed else 0.3

    passed = any(bool(policy.get(key)) for key in expected_keys)
    fallback_score = {
        "identity_grounding": 0.25,
        "goal_refresh": 0.35,
        "limitation_disclosure": 0.3,
        "identity_boundary": 0.3,
    }.get(case_name, 0.25)
    return passed, 1.0 if passed else fallback_score


def evaluate_strategy_variant(
    variant: Variant,
    candidate_policy: dict | None = None,
    baseline_policy: dict | None = None,
) -> dict[str, float | str | list[dict]]:
    candidate_policy = candidate_policy or {}
    baseline_policy = baseline_policy or {}
    benchmark_cases = []
    for case in get_evolution_benchmark_cases():
        baseline_passed, baseline_score = _evaluate_policy_on_case(
            baseline_policy,
            case.name,
            case.expected_policy_keys,
        )
        candidate_passed, candidate_score = _evaluate_policy_on_case(
            candidate_policy,
            case.name,
            case.expected_policy_keys,
        )
        benchmark_cases.append(
            {
                "name": case.name,
                "prompt": case.prompt,
                "baseline_passed": baseline_passed,
                "baseline_score": baseline_score,
                "candidate_passed": candidate_passed,
                "candidate_score": candidate_score,
                "rationale": case.rationale,
            }
        )

    baseline_benchmark_score = sum(case["baseline_score"] for case in benchmark_cases) / len(benchmark_cases)
    benchmark_score = sum(case["candidate_score"] for case in benchmark_cases) / len(benchmark_cases)
    risk_penalty = {"low": 0.05, "medium": 0.12, "high": 0.2}.get(variant.risk_level, 0.1)
    utility_score = max(0.0, min(1.0, variant.expected_gain + (benchmark_score - baseline_benchmark_score) + benchmark_score * 0.2 - risk_penalty))
    verdict = "promote" if benchmark_score > baseline_benchmark_score and benchmark_score >= 0.72 and utility_score >= 0.45 else "needs_review"
    return {
        "variant_id": variant.id,
        "baseline_benchmark_score": baseline_benchmark_score,
        "benchmark_score": benchmark_score,
        "utility_score": utility_score,
        "verdict": verdict,
        "benchmark_results": benchmark_cases,
    }
