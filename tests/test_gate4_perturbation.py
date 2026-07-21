# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Gate-4 blind perturbation hunt (ADR-007, PROMPT 6 Phase F).

For EVERY frozen golden scenario, perturb each referenced fact - (i) omit
it, (ii) flip it / pick another enum - and assert the engine stays
fail-closed-consistent:
  - omission never yields COMPLIANT or NOT_APPLICABLE via unknowns
    (both statuses must carry an EMPTY unknown_facts set - INV-1 and X5);
  - specific flips change verdicts only along statute-plausible lines;
  - generalization probes: the rules encode the PROVISION, not the 14 cases.

Attacker over the real rules + real golden facts (verification only).
"""
import datetime as dt
import pathlib

import pytest
import yaml

from engine import core
from engine.loader import load_rules_dir

ROOT = pathlib.Path(__file__).resolve().parent.parent
CV = "aia-omnibus-preOJ-9247-26"


@pytest.fixture(scope="module")
def rules():
    return load_rules_dir(str(ROOT / "rules"))


def _scenarios():
    out = []
    for file in sorted((ROOT / "oracle" / "golden").glob("*.yaml")):
        data = yaml.safe_load(file.read_text(encoding="utf-8"))
        out.append((data["id"], data["facts"], data["as_of"], data["expect"]))
    return out


def _group_verdict(verdicts, group):
    hits = [v for v in verdicts if v.rule_id == group or v.rule_id.startswith(group + "-")]
    return hits[0] if hits else None


def _perturbations(facts):
    for name in list(facts):
        omitted = dict(facts)
        del omitted[name]
        yield f"omit:{name}", omitted
        value = facts[name]
        if isinstance(value, bool):
            flipped = dict(facts)
            flipped[name] = not value
            yield f"flip:{name}={not value}", flipped
        elif name == "operator_role":
            other = "provider" if value == "deployer" else "deployer"
            flipped = dict(facts)
            flipped[name] = other
            yield f"flip:{name}={other}", flipped
        elif name == "annex_iii_use_case":
            for other in ("none", "law_enforcement", "credit_scoring"):
                if other != value:
                    flipped = dict(facts)
                    flipped[name] = other
                    yield f"flip:{name}={other}", flipped


# --- fail-closed invariant across ALL perturbations of ALL scenarios ------

def test_no_perturbation_ever_clears_on_unknowns(rules):
    """The core guarantee: a COMPLIANT or NOT_APPLICABLE verdict never rests
    on an unknown fact. If omitting/flipping any fact produced such a status
    with a named unknown, the engine would be clearing an SME on a guess."""
    checked = 0
    for sid, facts, as_of, _ in _scenarios():
        for label, perturbed in _perturbations(facts):
            verdicts = core.evaluate(rules, perturbed, as_of, CV)
            for v in verdicts:
                if v.status in (core.STATUS_COMPLIANT, core.STATUS_NOT_APPLICABLE):
                    assert v.unknown_facts == [], (
                        f"{sid} {label}: {v.rule_id} {v.status} rests on "
                        f"unknowns {v.unknown_facts} (fail-closed breach)"
                    )
            checked += 1
    assert checked > 100, f"hunt too small ({checked} perturbations)"


def test_omitting_a_referenced_fact_never_newly_clears_the_group(rules):
    """Scenario-directed: for the checked group, omitting a fact must not
    turn a non-cleared verdict INTO COMPLIANT/NOT_APPLICABLE."""
    for sid, facts, as_of, expect in _scenarios():
        base = {e["rule_group"]: e for e in expect}
        for group in base:
            baseline = _group_verdict(core.evaluate(rules, facts, as_of, CV), group)
            for name in facts:
                omitted = dict(facts)
                del omitted[name]
                v = _group_verdict(core.evaluate(rules, omitted, as_of, CV), group)
                if baseline.status not in (core.STATUS_COMPLIANT, core.STATUS_NOT_APPLICABLE):
                    assert v.status not in (
                        core.STATUS_COMPLIANT, core.STATUS_NOT_APPLICABLE
                    ), f"{sid}/{group} omit:{name} newly cleared to {v.status}"


# --- statute-plausible flips ----------------------------------------------

def _facts_of(sid):
    for cur, facts, as_of, _ in _scenarios():
        if cur == sid:
            return dict(facts), as_of
    raise KeyError(sid)


@pytest.mark.parametrize(
    "sid,flip,group,expected",
    [
        ("S01", ("interaction_disclosed", True), "ART50_1", "COMPLIANT"),
        ("S05", ("emotion_medical_safety_exception", True), "ART5_EMOTION_WORKPLACE", "COMPLIANT"),
        ("S11", ("deepfake_disclosed", True), "ART50_4", "COMPLIANT"),
        ("S04", ("practice_social_scoring", False), "ART5_SOCIAL_SCORING", "COMPLIANT"),
        ("S01", ("personal_nonprofessional_use", True), "ART50_1", "NOT_APPLICABLE"),
        ("S01", ("is_ai_system", False), "ART50_1", "NOT_APPLICABLE"),
    ],
)
def test_plausible_flip(rules, sid, flip, group, expected):
    facts, as_of = _facts_of(sid)
    facts[flip[0]] = flip[1]
    v = _group_verdict(core.evaluate(rules, facts, as_of, CV), group)
    assert v.status == expected


# --- generalization: rules encode the provision, not the 14 cases ---------

BASE = {"is_ai_system": True, "in_eu_market": True,
        "personal_nonprofessional_use": False}
POST = dt.date(2028, 1, 1)   # after every applies_from in v1


def _eval(rules, extra, as_of=POST):
    facts = dict(BASE)
    facts.update(extra)
    return core.evaluate(rules, facts, as_of, CV)


def test_art50_1_no_interaction_is_not_a_violation(rules):
    v = _group_verdict(_eval(rules, {"interacts_with_persons": False,
                                     "interaction_disclosed": False}), "ART50_1")
    assert v.status == "COMPLIANT"


def test_art5_ncii_with_safeguards_is_compliant(rules):
    # hunt F3: intended_purpose must be a known False for a clear COMPLIANT;
    # if it is unknown the engine fails closed to UNDETERMINED (Art. 5(1a)(a)(i)).
    v = _group_verdict(_eval(rules, {"ncii_intended_purpose": False,
                                     "ncii_generation_capability": True,
                                     "ncii_safeguards_state_of_art": True}), "ART5_NCII")
    assert v.status == "COMPLIANT"


def test_hr_annex_iii_never_noncompliant_from_use_case_alone(rules):
    # use case present, chapter-III fact UNANSWERED -> UNDETERMINED, never NON_COMPLIANT
    v = _group_verdict(_eval(rules, {"annex_iii_use_case": "employment_recruitment"}),
                       "HR_ANNEX_III")
    assert v.status == "UNDETERMINED"
    assert "chapter_iii_obligations_met" in v.unknown_facts


def test_hr_annex_iii_obligations_met_is_compliant(rules):
    v = _group_verdict(_eval(rules, {"annex_iii_use_case": "credit_scoring",
                                     "chapter_iii_obligations_met": True}),
                       "HR_ANNEX_III")
    assert v.status == "COMPLIANT"


def test_hr_annex_iii_obligations_unmet_is_noncompliant(rules):
    v = _group_verdict(_eval(rules, {"annex_iii_use_case": "credit_scoring",
                                     "chapter_iii_obligations_met": False}),
                       "HR_ANNEX_III")
    assert v.status == "NON_COMPLIANT"


def test_hr_annex_iii_non_annex_use_case_is_not_applicable(rules):
    v = _group_verdict(_eval(rules, {"annex_iii_use_case": "none",
                                     "chapter_iii_obligations_met": False}),
                       "HR_ANNEX_III")
    assert v.status == "NOT_APPLICABLE"


def test_art50_2_new_system_deadline_is_earlier(rules):
    # a NEW synthetic-content system (not legacy) is bound from 2026-08-02
    v = _group_verdict(_eval(rules, {"generates_synthetic_content": True,
                                     "content_marked_machine_readable": False,
                                     "system_on_market_before_2026_08_02": False},
                             as_of=dt.date(2026, 9, 1)), "ART50_2")
    assert v.status == "NON_COMPLIANT"
