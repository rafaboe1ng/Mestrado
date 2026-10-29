import pytest

from framework.expert_validation import (APPROVABLE_WITHOUT_NEW_DATA, REASON_CODES, ExpertValidationStore)

pytestmark = pytest.mark.framework


def test_get_or_create_and_persistence(tmp_path):
    p = tmp_path / "evr.json"
    s = ExpertValidationStore(p)
    a = s.create_request(2, "ThinWall", "anomalous_operational_state", "x", operation="WallDepositionOp")
    b = s.create_request(2, "ThinWall", "anomalous_operational_state", "y", operation="WallDepositionOp")
    assert a is b and a.request_id == "evr_0001"
    c = s.create_request(2, "ThinWall", "parameter_adjustment_suggested", "z", operation="WallDepositionOp")
    assert c.request_id == "evr_0002"
    s.save()
    s2 = ExpertValidationStore(p)
    assert [r.request_id for r in s2.all_requests()] == ["evr_0001", "evr_0002"]
    d = s2.create_request(3, "Base", "missing_knowledge", "w")
    assert d.request_id == "evr_0003", "counter continues after reload"


def test_unknown_code_and_decision_rejected(tmp_path):
    s = ExpertValidationStore(tmp_path / "e.json")
    with pytest.raises(ValueError):
        s.create_request(1, "Base", "sensor_glitch", "x")
    r = s.create_request(1, "Base", "unsafe_value", "x")
    with pytest.raises(ValueError):
        s.apply_feedback(r.request_id, "approved")
    s.apply_feedback(r.request_id, "expert_approved", "checked")
    assert s.find_resolution(1, None, "unsafe_value").status == "expert_approved"


def test_new_codes_and_approvability_policy():
    assert "anomalous_operational_state" in REASON_CODES and "parameter_adjustment_suggested" in REASON_CODES
    assert "anomalous_operational_state" in APPROVABLE_WITHOUT_NEW_DATA
    assert "parameter_adjustment_suggested" not in APPROVABLE_WITHOUT_NEW_DATA, "adopting new values needs new data"
