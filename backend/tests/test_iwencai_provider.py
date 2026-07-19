from marketdesk.providers.iwencai import normalize_research_evidence


def test_normalize_research_evidence_accepts_common_payload_shapes() -> None:
    payload = {
        "summary": "近三十日有分红相关公告",
        "reports": [{"title": "研报关注现金流与渠道库存"}],
        "data": {"risks": ["食品安全风险仍需跟踪"]},
    }

    evidence = normalize_research_evidence(payload)

    assert evidence == ["近三十日有分红相关公告", "研报关注现金流与渠道库存", "食品安全风险仍需跟踪"]
