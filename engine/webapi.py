# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""L5 web bridge (ADR-013): JSON-in / JSON-out over the SAME engine.

Pyodide calls boot_data() (schema + i18n + corpus status, so the wizard is
generated from the schema, never duplicated in JS) and evaluate_answers()
(-> render_structured dict + the render_report print text). No verdict logic
lives here or in JS: this is a thin, validated wrapper (ADR-012(2), ADR-013).
"""
import datetime as dt
import json
import re

from engine import core
from engine.facts import FactValidationError, load_facts_schema, validate_facts
from engine.i18n import bundle, check_completeness, load_i18n
from engine.loader import RuleValidationError, load_rules_dir, load_yaml_strict
from engine.render import DISCLAIMER, _corpus_status, render_report, render_structured

SCHEMA_PATH = "schema/facts.yaml"
RULES_DIR = "rules"
MESSAGES_PATH = "i18n/messages.yaml"
MANIFEST_PATH = "corpus/manifest.yaml"
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class WebApiError(ValueError):
    """Malformed web input (ADR-008 classes): undeclared fact, wrong type,
    malformed as_of, duplicate JSON key, non-mapping payload."""


def _load():
    schema = load_facts_schema(SCHEMA_PATH)
    rules = load_rules_dir(RULES_DIR)
    catalog = load_i18n(MESSAGES_PATH)
    check_completeness(catalog, [rule.rationale_key for rule in rules])
    manifest = load_yaml_strict(MANIFEST_PATH)
    version = manifest.get("corpus_version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or not version.strip():
        raise WebApiError(f"{MANIFEST_PATH}: missing corpus_version")
    return schema, rules, catalog, version


def _no_dupes(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise WebApiError(f"duplicate answer key {key!r}")
        seen[key] = value
    return seen


def _as_dict(answers):
    if isinstance(answers, str):
        try:
            answers = json.loads(answers, object_pairs_hook=_no_dupes)
        except json.JSONDecodeError as exc:
            raise WebApiError(f"answers is not valid JSON ({exc})") from exc
    if not isinstance(answers, dict):
        raise WebApiError("answers must be a mapping fact -> value")
    return answers


def _parse_as_of(as_of):
    if isinstance(as_of, dt.date) and not isinstance(as_of, dt.datetime):
        return as_of
    if not isinstance(as_of, str) or not _DATE_RE.match(as_of):
        raise WebApiError(f"as_of must be an ISO date YYYY-MM-DD, got {as_of!r}")
    try:
        return dt.date.fromisoformat(as_of)
    except ValueError as exc:
        raise WebApiError(f"as_of {as_of!r} is not a valid calendar date") from exc


def boot_data():
    """Everything the wizard + chrome need, both languages, as a JSON string."""
    schema, rules, catalog, version = _load()
    facts = [
        {
            "name": name,
            "type": entry["type"],
            "values": entry.get("values"),
            "prompt": {"it": entry["i18n"]["it"], "en": entry["i18n"]["en"]},
        }
        for name, entry in schema.items()
    ]
    return json.dumps({
        "facts": facts,
        "i18n": {lang: bundle(catalog, lang) for lang in ("it", "en")},
        "corpus_version": version,
        "corpus_status": _corpus_status(version),
        "disclaimer": DISCLAIMER,
    })


def evaluate_answers(answers, as_of, lang):
    """answers (dict/JSON), as_of (ISO), lang (it|en) -> JSON with the
    render_structured dict and the render_report print text."""
    if lang not in ("it", "en"):
        raise WebApiError(f"unsupported lang {lang!r}")
    payload = _as_dict(answers)
    when = _parse_as_of(as_of)
    schema, rules, catalog, version = _load()
    try:
        facts = validate_facts(schema, payload)
    except FactValidationError as exc:
        raise WebApiError(str(exc)) from exc
    verdicts = core.evaluate(rules, facts, when, version)
    localized = bundle(catalog, lang)
    return json.dumps({
        "structured": render_structured(verdicts, when, version, DISCLAIMER),
        "print_text": render_report(verdicts, when, version, DISCLAIMER, i18n=localized),
    })
