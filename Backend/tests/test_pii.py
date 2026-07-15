"""Tests for app.services.pii — deterministic PII masking, no model calls."""

from __future__ import annotations

from app.services import pii


def test_mask_unmask_round_trips_exactly():
    text = (
        "Ravi Kumar called from +91 98765 43210 about his PAN ABCDE1234F "
        "and Aadhaar 2345 6789 0123. Email him at ravi.kumar@example.com."
    )
    masked, mask_map = pii.mask(text, names=["Ravi Kumar"])
    assert pii.unmask(masked, mask_map) == text


def test_masked_text_contains_no_original_phone_pan_email():
    text = "Call 9876543210 or email ravi@example.com. PAN is ABCDE1234F."
    masked, _ = pii.mask(text)
    assert "9876543210" not in masked
    assert "ravi@example.com" not in masked
    assert "ABCDE1234F" not in masked


def test_placeholders_are_stable_across_repeats():
    text = "Contact 9876543210 again, same number 9876543210."
    masked, mask_map = pii.mask(text)
    assert masked.count("[PHONE_1]") == 2
    assert "[PHONE_2]" not in masked
    assert mask_map["[PHONE_1]"] == "9876543210"


def test_names_are_masked_via_model_detected_spans():
    text = "Priya Sharma filed a complaint against her landlord."
    masked, mask_map = pii.mask(text, names=["Priya Sharma"])
    assert "Priya Sharma" not in masked
    assert "[PERSON_1]" in masked
    assert mask_map["[PERSON_1]"] == "Priya Sharma"


def test_mask_with_no_pii_is_unchanged():
    text = "What are my rights as a tenant?"
    masked, mask_map = pii.mask(text)
    assert masked == text
    assert mask_map == {}


def test_aadhaar_and_phone_do_not_cross_match():
    text = "Aadhaar 2345 6789 0123 and phone 9876543210 are different."
    masked, mask_map = pii.mask(text)
    assert mask_map["[AADHAAR_1]"] == "2345 6789 0123"
    assert mask_map["[PHONE_1]"] == "9876543210"
    assert pii.unmask(masked, mask_map) == text
