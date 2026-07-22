# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Gate-6 webapi bridge (PROMPT 8 Phase F1).

(a) ADR-008 malformed classes on the JSON input surface: undeclared fact,
    wrong type, malformed/boundary as_of, duplicate key, non-mapping payload,
    bad lang.
(b) Oracle parity: all 14 frozen golden scenarios evaluated THROUGH webapi
    match the oracle's expectations - the single-source-of-truth guarantee
    (the web path can never drift from the CLI/oracle path).
"""
import datetime as dt
import json
import pathlib

import pytest
import yaml

from engine import webapi

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "oracle" / "golden"


# --- (a) ADR-008 on the JSON input surface --------------------------------

def _eval(answers, as_of="2026-09-01", lang="it"):
    return json.loads(webapi.evaluate_answers(answers, as_of, lang))


def test_undeclared_fact_rejected():
    with pytest.raises(webapi.WebApiError):
        _eval({"ghost_fact": True})


def test_wrong_type_rejected():
    with pytest.raises(webapi.WebApiError):
        _eval({"is_ai_system": "yes"})


def test_malformed_as_of_rejected():
    with pytest.raises(webapi.WebApiError):
        _eval({"is_ai_system": True}, as_of="2026-13-40")


def test_non_iso_as_of_rejected():
    with pytest.raises(webapi.WebApiError):
        _eval({"is_ai_system": True}, as_of="01/09/2026")


def test_duplicate_json_key_rejected():
    with pytest.raises(webapi.WebApiError):
        _eval('{"is_ai_system": true, "is_ai_system": false}')


def test_non_mapping_payload_rejected():
    with pytest.raises(webapi.WebApiError):
        _eval("[1, 2, 3]")


def test_bad_lang_rejected():
    with pytest.raises(webapi.WebApiError):
        _eval({"is_ai_system": True}, lang="de")


def test_null_answer_is_unknown_not_error():
    out = _eval({"is_ai_system": True, "interacts_with_persons": None})
    assert out["structured"]["corpus_status"] in ("PROVISIONAL", "FINAL")


# --- boot_data shape ------------------------------------------------------

def test_boot_data_has_all_facts_and_langs():
    boot = json.loads(webapi.boot_data())
    assert len(boot["facts"]) == 19
    assert set(boot["i18n"]) == {"it", "en"}
    # header reordered Italian-first (owner-directed copy change, 2026-07-22)
    assert boot["disclaimer"].startswith("=== NON COSTITUISCE CONSULENZA LEGALE")


# --- (b) oracle parity 14/14 through webapi --------------------------------

def _matches(expected, verdict):
    def has_applicability(node):
        if node.get("op") == "applicability":
            return True
        return any(has_applicability(c) for c in node.get("children", []))
    if expected == "INACTIVE":
        return verdict["status"] == "UNDETERMINED" and has_applicability(verdict["explanation"])
    if expected == "NOT_APPLICABLE":
        return verdict["status"] == "NOT_APPLICABLE"
    if expected == "UNDETERMINED":
        return verdict["status"] == "UNDETERMINED" and bool(verdict["unknown_facts"])
    return verdict["status"] == expected


def _scenarios():
    out = []
    for f in sorted(GOLDEN.glob("*.yaml")):
        d = yaml.safe_load(f.read_text(encoding="utf-8"))
        out.append(d)
    return out


@pytest.mark.parametrize("scenario", _scenarios(), ids=lambda s: s["id"])
def test_webapi_matches_oracle_expectation(scenario):
    as_of = scenario["as_of"]
    if isinstance(as_of, dt.date):
        as_of = as_of.isoformat()
    out = _eval(scenario["facts"], as_of=as_of, lang="it")
    verdicts = out["structured"]["verdicts"]
    for entry in scenario["expect"]:
        group = entry["rule_group"]
        in_group = [v for v in verdicts
                    if v["rule_id"] == group or v["rule_id"].startswith(group + "-")]
        assert in_group, f"{scenario['id']}/{group}: no rule in group"
        assert all(_matches(entry["status"], v) for v in in_group), (
            f"{scenario['id']}/{group}: expected {entry['status']}, "
            f"got {[v['status'] for v in in_group]}"
        )


def test_exactly_14_scenarios():
    assert len(_scenarios()) == 14
