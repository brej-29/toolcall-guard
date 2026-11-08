from tcg.mcp_server import _record, check


def test_keyword_backend():
    r = _record("ops", "p", [], [], {"name": "delete_bucket", "arguments": {"name": "x"}})
    out = check(r, "keyword")
    assert out["verdict"] == "block" and out["source"] == "keyword" and out["escalated"] is False
    assert check(_record("ops", "p", [], [], {"name": "get_order", "arguments": {"id": "1"}}), "keyword")["verdict"] == "allow"
