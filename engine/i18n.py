"""L5 i18n catalog loader (ADR-012(4)).

The catalog i18n/messages.yaml carries status_labels, rationales and ui
strings, each with an 'it' and an 'en' value. Loading is STRICT: a missing
section, a missing status, or a missing/empty/whitespace it|en value is a
LOAD-TIME error - never a silent fallback to the other language. Completeness
against the loaded rules (every rationale_key present) is a separate gate.
"""
from engine.loader import RuleValidationError, load_yaml_strict

STATUSES = ("COMPLIANT", "NON_COMPLIANT", "UNDETERMINED", "NOT_APPLICABLE")
SECTIONS = ("status_labels", "rationales", "ui")
LANGS = ("it", "en")
# The ui.* keys cli.py / render.py dereference by direct index. Enumerated
# here so a catalog missing one fails at LOAD, never with a runtime KeyError
# that would leak exit 1 (hunt F1; ADR-012(4)+(5), ADR-008 missing-field class).
REQUIRED_UI = (
    "ai_disclosure", "intro", "hint_bool", "hint_enum", "invalid_answer",
    "unknown_forced", "interrupted", "deadlines_header", "deadlines_none",
    "token_yes", "token_no",
)


class I18nError(ValueError):
    """Malformed or incomplete i18n catalog (ADR-008 classes; ADR-012(4))."""


def _check_entry(value, where):
    if not isinstance(value, dict):
        raise I18nError(f"{where}: must be a mapping with it and en")
    extra = sorted(set(value) - set(LANGS), key=repr)
    missing = [lang for lang in LANGS if lang not in value]
    if missing or extra:
        raise I18nError(
            f"{where}: keys must be exactly it,en (missing {missing}, extra {extra})"
        )
    for lang in LANGS:
        text = value[lang]
        if not isinstance(text, str) or not text.strip():
            raise I18nError(f"{where}.{lang}: must be a non-empty string, got {text!r}")


def load_i18n(path):
    try:
        data = load_yaml_strict(path)
    except RuleValidationError as exc:
        raise I18nError(str(exc)) from exc
    if not isinstance(data, dict):
        raise I18nError(f"{path}: catalog must be a top-level mapping")
    for section in SECTIONS:
        if not isinstance(data.get(section), dict):
            raise I18nError(f"{path}: missing/invalid section {section!r}")
    for status in STATUSES:
        if status not in data["status_labels"]:
            raise I18nError(f"{path}: status_labels missing status {status!r}")
    for key in REQUIRED_UI:
        if key not in data["ui"]:
            raise I18nError(f"{path}: ui missing required key {key!r} (ADR-012(4))")
    for section in SECTIONS:
        for key, value in data[section].items():
            _check_entry(value, f"{section}.{key}")
    return data


def check_completeness(catalog, rationale_keys):
    """Every rule's rationale_key AND all four statuses must be labelled."""
    for status in STATUSES:
        if status not in catalog["status_labels"]:
            raise I18nError(f"status_labels missing status {status!r}")
    for key in rationale_keys:
        if key not in catalog["rationales"]:
            raise I18nError(f"rationales missing rationale_key {key!r} (ADR-012(4))")


def bundle(catalog, lang):
    """Flatten the catalog to one language (the shape render_report consumes)."""
    if lang not in LANGS:
        raise I18nError(f"unsupported lang {lang!r}; expected one of {LANGS}")
    return {
        section: {key: value[lang] for key, value in catalog[section].items()}
        for section in SECTIONS
    }
