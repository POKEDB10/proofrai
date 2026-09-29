from backend.core.intake.explain import get_explainability_catalogue


def test_get_explainability_catalogue() -> None:
    catalogue = get_explainability_catalogue()
    assert len(catalogue) >= 6
    ids = {item.id for item in catalogue}
    assert "pii_leakage" in ids
    assert "prompt_injection" in ids
    assert "proxy_discrimination" in ids
    assert "tool_abuse" in ids
    assert "job_rationale" in ids
    assert "human_oversight" in ids

    for item in catalogue:
        assert item.title
        assert len(item.what_is_this) > 20
        assert len(item.why_it_matters) > 20
        assert len(item.example) > 20
        assert item.related_risk
