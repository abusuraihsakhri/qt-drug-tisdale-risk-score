"""Integrity and API boundary regression tests."""
import pytest

from agents.base import AuditTrail, SecurityException
from agents.api import TisdaleAssessment, api_score
from fastapi import HTTPException


def test_hmac_recomputation_detects_forgery():
    audit = AuditTrail(secret_key="test-key-not-for-production")
    audit.log("tester", "unit", "TEST", {"event": 1})
    assert audit.verify_integrity()
    audit.logs[0]["payload_hash"] = "0" * 64
    assert audit.verify_integrity() is False


def test_audit_snapshot_cannot_mutate_original():
    audit = AuditTrail(secret_key="test-key-not-for-production")
    audit.log("tester", "unit", "TEST", {"status": "ok"})
    snapshot = audit.get_trail()
    snapshot[0]["current_hash"] = "forged"
    assert audit.verify_integrity() is True


def test_phi_is_screened_from_audit_metadata():
    audit = AuditTrail(secret_key="test-key-not-for-production")
    with pytest.raises(SecurityException):
        audit.log("MRN-994827", "unit", "TEST", {"status": "ok"})


def test_api_score_implements_validated_points():
    request = TisdaleAssessment(age=68, sex="female", loop_diuretic=False,
        potassium=3.5, qtc=450, acute_mi=False, heart_failure=True,
        num_qtdrugs=2, sepsis=False)
    result = api_score(request)
    assert result["score"] == 1 + 1 + 2 + 2 + 3 + 6
    assert result["risk_classification"] == "High Risk"


def test_api_rejects_impossible_values():
    request = TisdaleAssessment(age=30, sex="male", loop_diuretic=False,
        potassium=0, qtc=450, acute_mi=False, heart_failure=False,
        num_qtdrugs=0, sepsis=False)
    with pytest.raises(HTTPException) as exc:
        api_score(request)
    assert exc.value.status_code == 422
