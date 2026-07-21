# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Gate-4 statute-anchor gates for the v1 rules (ADR-011).

(a) every loaded rule declares timeline_ref, and every date in the rule
    (scalar applies_from, X3 branch dates, applies_until) is covered by the
    applies_from of one of its referenced corpus/timeline.yaml entries
    (ADR-011(4): dates are anchored, never hand-typed);
(b) the '# opposite: [<RULE_ID>]' comments equal the loaded rule ids, both
    directions (ADR-011(3): consider-the-opposite is enforced);
(c) every rule's corpus_id exists in corpus/manifest.yaml sources.
"""
import datetime as dt
import pathlib
import re

import pytest

from engine.loader import load_rules_dir, load_yaml_strict

ROOT = pathlib.Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / "rules"
TIMELINE = ROOT / "corpus" / "timeline.yaml"
MANIFEST = ROOT / "corpus" / "manifest.yaml"

_OPPOSITE = re.compile(r"#\s*opposite:\s*\[([^\]]+)\]")


@pytest.fixture(scope="module")
def rules():
    return load_rules_dir(str(RULES_DIR))


def _rule_dates(rule):
    dates = set()
    af = rule.applies_from
    if isinstance(af, dt.date):
        dates.add(af)
    else:  # X3 branch list
        for branch in af:
            dates.add(branch.get("date") or branch.get("default"))
    if rule.applies_until is not None:
        dates.add(rule.applies_until)
    return dates


@pytest.fixture(scope="module")
def timeline_dates():
    data = load_yaml_strict(str(TIMELINE))
    out = {}
    for entry in data["entries"]:
        out[entry["obligation"]] = dt.date.fromisoformat(entry["applies_from"])
    return out


# --- (a) timeline anchoring -----------------------------------------------

def test_every_rule_declares_timeline_ref(rules):
    for rule in rules:
        assert rule.timeline_ref, f"{rule.id}: missing timeline_ref (ADR-011(4))"


def test_referenced_obligations_exist(rules, timeline_dates):
    for rule in rules:
        for ref in rule.timeline_ref:
            assert ref in timeline_dates, f"{rule.id}: timeline_ref {ref!r} not in timeline"


def test_every_rule_date_is_timeline_anchored(rules, timeline_dates):
    for rule in rules:
        covered = {timeline_dates[ref] for ref in rule.timeline_ref}
        for date in _rule_dates(rule):
            assert date in covered, (
                f"{rule.id}: date {date.isoformat()} not covered by "
                f"timeline_ref entries {rule.timeline_ref} (hand-typed?)"
            )


# --- (b) consider-the-opposite comments -----------------------------------

def test_opposite_comment_ids_equal_rule_ids(rules):
    comment_ids = set()
    for file in sorted(RULES_DIR.glob("*.yaml")):
        for match in _OPPOSITE.finditer(file.read_text(encoding="utf-8")):
            comment_ids.add(match.group(1).strip())
    rule_ids = {rule.id for rule in rules}
    missing = rule_ids - comment_ids
    extra = comment_ids - rule_ids
    assert not missing, f"rules without an opposite comment: {sorted(missing)}"
    assert not extra, f"opposite comments for unknown rule ids: {sorted(extra)}"


# --- (c) corpus id validity -----------------------------------------------

def test_every_corpus_id_in_manifest(rules):
    manifest = load_yaml_strict(str(MANIFEST))
    source_ids = {src["id"] for src in manifest["sources"]}
    for rule in rules:
        cid = rule.legal_source["corpus_id"]
        assert cid in source_ids, f"{rule.id}: corpus_id {cid!r} not a manifest source"


# --- sanity: exactly the seven Gate-4 groups load -------------------------

def test_seven_rule_groups_present(rules):
    assert {rule.id for rule in rules} == {
        "ART50_1", "ART50_2", "ART50_4", "ART5_SOCIAL_SCORING",
        "ART5_EMOTION_WORKPLACE", "ART5_NCII", "HR_ANNEX_III",
    }
