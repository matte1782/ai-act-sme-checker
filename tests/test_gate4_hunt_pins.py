"""Gate-4 perturbation-hunt pins (ADR-007, Phase F).

Confirmed findings from the blind statute cross-read, pinned so they cannot
regress:
  F1 (Art. 5(1)(f)): the emotion prohibition covers workplace AND education
     institutions - the fact's questionnaire meaning must cover both (the
     frozen fact name is 'workplace'; S06's frozen COMPLIANT forbids adding
     an education leaf to the logic, so coverage lives in the fact meaning);
  F2 (Art. 50(4)): the deep-fake disclosure duty triggers on generation /
     dissemination, not publication alone - the fact must capture that;
  F3 (Art. 5(1a)(a)(i)): a system whose INTENDED PURPOSE is NCII is
     prohibited regardless of claimed safeguards - modelled explicitly so a
     purpose-built generator can no longer be cleared by asserting safeguards.
"""
import datetime as dt

import pytest

from engine import core
from engine.facts import load_facts_schema
from engine.loader import load_rules_dir

CV = "aia-omnibus-preOJ-9247-26"
BASE = {"is_ai_system": True, "in_eu_market": True,
        "personal_nonprofessional_use": False}
POST_NCII = dt.date(2027, 1, 15)   # after Art. 5 NCII applies_from 2026-12-02


@pytest.fixture(scope="module")
def rules():
    return load_rules_dir("rules")


@pytest.fixture(scope="module")
def schema():
    return load_facts_schema("schema/facts.yaml")


def _group(verdicts, gid):
    hits = [v for v in verdicts if v.rule_id == gid or v.rule_id.startswith(gid + "-")]
    return hits[0]


def _eval(rules, extra, as_of=POST_NCII):
    facts = dict(BASE)
    facts.update(extra)
    return core.evaluate(rules, facts, as_of, CV)


# --- F1: emotion covers workplace AND education (fact meaning) -------------

def test_f1_emotion_question_covers_education(schema):
    i18n = schema["emotion_recognition_workplace"]["i18n"]
    assert "istruzione" in i18n["it"].lower(), "IT question must name education institutions"
    assert "education" in i18n["en"].lower(), "EN question must name education institutions"


# --- F2: deep-fake fact captures the Art. 50(4) generation trigger --------

def test_f2_deepfake_question_covers_generation(schema):
    i18n = schema["deepfake_published"]["i18n"]
    assert "genera" in i18n["it"].lower(), "IT question must cover generating deep fakes"
    assert "generat" in i18n["en"].lower(), "EN question must cover generating deep fakes"


# --- F3: NCII intended-purpose is prohibited despite claimed safeguards ----

def test_f3_ncii_intended_purpose_prohibited_even_with_safeguards(rules):
    v = _group(_eval(rules, {
        "ncii_intended_purpose": True,
        "ncii_generation_capability": True,
        "ncii_safeguards_state_of_art": True,
    }), "ART5_NCII")
    assert v.status == "NON_COMPLIANT"


def test_f3_ncii_not_intended_with_safeguards_is_compliant(rules):
    # the (ii) fix must not over-break: not intended purpose + safeguards -> COMPLIANT
    v = _group(_eval(rules, {
        "ncii_intended_purpose": False,
        "ncii_generation_capability": True,
        "ncii_safeguards_state_of_art": True,
    }), "ART5_NCII")
    assert v.status == "COMPLIANT"


def test_f3_ncii_capable_without_safeguards_still_noncompliant(rules):
    # branch (ii) unchanged: capability + no safeguards -> NON_COMPLIANT (S08 class)
    v = _group(_eval(rules, {
        "ncii_generation_capability": True,
        "ncii_safeguards_state_of_art": False,
    }), "ART5_NCII")
    assert v.status == "NON_COMPLIANT"


def test_f3_ncii_intended_purpose_declared_in_schema(schema):
    assert "ncii_intended_purpose" in schema
    assert schema["ncii_intended_purpose"]["type"] == "bool"
