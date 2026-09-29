from backend.core.suite.generator import (
    evaluate_custom_case,
    generate_synthetic_attack_cases,
)


def test_generate_synthetic_attack_cases() -> None:
    cases = generate_synthetic_attack_cases()
    assert len(cases) >= 4
    categories = {c.id.split("-")[2].lower() for c in cases}
    assert "pii" in categories or "pro" in categories or "too" in categories

    pii_cases = generate_synthetic_attack_cases(category="pii_extraction")
    assert len(pii_cases) >= 1
    assert all("pii" in c.id.lower() for c in pii_cases)


def test_evaluate_custom_case() -> None:
    cases = generate_synthetic_attack_cases(category="prompt_injection")
    assert len(cases) > 0
    test_case = cases[0]

    base_res, ctrl_res = evaluate_custom_case(test_case)
    assert base_res.variant == "baseline"
    assert ctrl_res.variant == "controlled"
    assert base_res.case_id == test_case.id
    assert ctrl_res.case_id == test_case.id
    assert base_res.verdict in ("pass", "fail", "error", "needs_review")
    assert ctrl_res.verdict in ("pass", "fail", "error", "needs_review")
