from tcg.cascade import decide, p_block


def test_routing():
    h = lambda: {"verdict": "block", "category": "data_exfiltration", "reason": "h"}
    allow = {"verdict": "allow", "category": "benign", "reason": ""}
    assert decide(allow, 0.99, h, 0.2, 0.8)[1] == "local"      # P(block)=0.01 -> confident allow
    assert decide(allow, 0.6, h, 0.2, 0.8)[1] == "hosted"      # P(block)=0.4 -> uncertain
    assert decide(None, None, h, 0.2, 0.8)[1] == "hosted"      # unparseable -> escalate
    blk = {"verdict": "block", "category": "data_exfiltration", "reason": ""}
    assert decide(blk, 0.95, h, 0.2, 0.8) == (blk, "local")
    assert p_block("allow", 0.7) == 0.30000000000000004 or abs(p_block("allow", 0.7) - 0.3) < 1e-9
