"""L5 CLI output path (ADR-012). Entry: ``python -m engine.cli``.

Two modes: non-interactive (--answers <file.yaml>) and interactive (a
schema-ordered questionnaire on stdin). Both route ALL verdict content
through render_report (ADR-012(2)); localized via i18n/messages.yaml with
no silent fallback (ADR-012(4)); exit codes are exactly {0, 2} and carry
NO compliance semantics (ADR-012(5)); the interactive banner declares the
AI-based interaction (ADR-012(6)). A mid-questionnaire EOF/interrupt
produces NO partial report - it fails closed to exit 2.
"""
import argparse
import datetime as dt
import re
import sys

from engine import core
from engine.facts import (
    UNKNOWN,
    FactValidationError,
    load_facts_schema,
    validate_facts,
)
from engine.i18n import I18nError, bundle, check_completeness, load_i18n
from engine.loader import RuleValidationError, load_rules_dir, load_yaml_strict
from engine.render import DISCLAIMER, render_report

SCHEMA_PATH = "schema/facts.yaml"
RULES_DIR = "rules"
MESSAGES_PATH = "i18n/messages.yaml"
MANIFEST_PATH = "corpus/manifest.yaml"

EXIT_OK = 0
EXIT_USAGE = 2
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MAX_RETRIES = 3


class CliError(Exception):
    """Input/usage error -> exit 2 (never encodes a verdict)."""


def _reconfigure_streams():
    # Windows consoles default to cp1252 and would mangle the Italian text.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (ValueError, OSError):
                pass


def _err(text):
    sys.stderr.write(text + "\n")
    sys.stderr.flush()


def _parse_as_of(value):
    if not _DATE_RE.match(value):
        raise CliError(f"--as-of must be an ISO date YYYY-MM-DD, got {value!r}")
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise CliError(f"--as-of {value!r} is not a valid calendar date") from exc


def _corpus_version(path):
    data = load_yaml_strict(path)
    version = data.get("corpus_version") if isinstance(data, dict) else None
    if not isinstance(version, str) or not version.strip():
        raise CliError(f"{path}: missing corpus_version")
    return version


def _load_answers(path, schema):
    try:
        data = load_yaml_strict(path)
    except RuleValidationError as exc:
        raise CliError(str(exc)) from exc
    if not isinstance(data, dict):
        raise CliError(f"{path}: answers must be a flat mapping fact -> value")
    try:
        return validate_facts(schema, data)
    except FactValidationError as exc:
        raise CliError(str(exc)) from exc


def _read_line():
    line = sys.stdin.readline()
    if line == "":            # EOF mid-questionnaire -> fail closed
        raise EOFError
    return line.strip()


def _ask_bool(entry, ui, lang):
    yes, no = ui["token_yes"].lower(), ui["token_no"].lower()
    _err(f"{entry['i18n'][lang]} {ui['hint_bool']}")
    for _ in range(_MAX_RETRIES):
        answer = _read_line().lower()
        if answer == "?":
            return UNKNOWN
        if answer == yes:
            return True
        if answer == no:
            return False
        _err(ui["invalid_answer"])
    _err(ui["unknown_forced"])
    return UNKNOWN


def _ask_enum(entry, ui, lang):
    values = entry["values"]
    _err(entry["i18n"][lang])
    for index, value in enumerate(values, 1):
        _err(f"  {index}. {value}")
    _err(ui["hint_enum"])
    for _ in range(_MAX_RETRIES):
        answer = _read_line()
        if answer == "?":
            return UNKNOWN
        if answer.isdigit() and 1 <= int(answer) <= len(values):
            return values[int(answer) - 1]
        _err(ui["invalid_answer"])
    _err(ui["unknown_forced"])
    return UNKNOWN


def _ask_date(entry, ui, lang):
    _err(f"{entry['i18n'][lang]} [YYYY-MM-DD / ?]")
    for _ in range(_MAX_RETRIES):
        answer = _read_line()
        if answer == "?":
            return UNKNOWN
        if _DATE_RE.match(answer):
            try:
                return dt.date.fromisoformat(answer)
            except ValueError:
                pass
        _err(ui["invalid_answer"])
    _err(ui["unknown_forced"])
    return UNKNOWN


def _interactive(schema, ui, lang):
    _err(ui["ai_disclosure"])
    _err(ui["intro"])
    _err("")
    answers = {}
    for name, entry in schema.items():
        ftype = entry["type"]
        if ftype == "bool":
            answers[name] = _ask_bool(entry, ui, lang)
        elif ftype == "enum":
            answers[name] = _ask_enum(entry, ui, lang)
        else:
            answers[name] = _ask_date(entry, ui, lang)
    return answers


def _run(args):
    schema = load_facts_schema(SCHEMA_PATH)
    rules = load_rules_dir(RULES_DIR)
    catalog = load_i18n(MESSAGES_PATH)
    check_completeness(catalog, [rule.rationale_key for rule in rules])
    localized = bundle(catalog, args.lang)
    corpus_version = _corpus_version(MANIFEST_PATH)
    as_of = _parse_as_of(args.as_of) if args.as_of else dt.date.today()

    if args.answers:
        facts = _load_answers(args.answers, schema)
    else:
        try:
            facts = _interactive(schema, localized["ui"], args.lang)
        except (EOFError, KeyboardInterrupt):
            _err(localized["ui"]["interrupted"])
            return EXIT_USAGE

    verdicts = core.evaluate(rules, facts, as_of, corpus_version)
    # ADR-012(2): the ONLY place verdict content is produced.
    report = render_report(verdicts, as_of, corpus_version, DISCLAIMER, i18n=localized)
    sys.stdout.write(report + "\n")
    sys.stdout.flush()
    return EXIT_OK


def main(argv=None):
    _reconfigure_streams()
    parser = argparse.ArgumentParser(
        prog="python -m engine.cli",
        description="AI Act SME self-check (NOT legal advice).",
    )
    parser.add_argument("--answers", help="YAML file: flat mapping fact -> value")
    parser.add_argument("--as-of", dest="as_of", help="evaluation date YYYY-MM-DD")
    parser.add_argument("--lang", choices=["it", "en"], default="it")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse already printed usage; normalize to our {0,2} codes.
        code = exc.code if isinstance(exc.code, int) else EXIT_USAGE
        return EXIT_OK if code == 0 else EXIT_USAGE
    try:
        return _run(args)
    except (CliError, FactValidationError, RuleValidationError, I18nError,
            core.EvaluationError) as exc:
        _err(str(exc))
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
