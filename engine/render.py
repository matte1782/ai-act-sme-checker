# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""L5 minimal text renderer.

The disclaimer block is a STRUCTURAL argument (INV-4): the renderer
refuses to emit any user-facing output unless the caller passes the
exact block. Every verdict is rendered with citation, as_of stamp,
corpus version, and its explanation tree.

R4: the as_of stamp is cross-checked against every Verdict.as_of; a
report must never stamp a date its verdicts were not evaluated at.
"""
import copy
import datetime as dt

DISCLAIMER = (
    "=== NON COSTITUISCE CONSULENZA LEGALE / NOT LEGAL ADVICE ===\n"
    "Questa è un'autovalutazione automatica e informativa. NON è\n"
    "una consulenza legale e non crea alcun rapporto professionale.\n"
    "I verdetti possono essere incompleti o errati; gli obblighi\n"
    "dipendono da circostanze che solo un professionista\n"
    "qualificato può valutare. NON DETERMINABILE significa: è\n"
    "necessaria una revisione umana/legale.\n"
    "\n"
    "This is an automated, informational self-check. It is NOT legal\n"
    "advice and creates no professional-client relationship. Verdicts\n"
    "may be incomplete or wrong; obligations depend on circumstances\n"
    "only a qualified professional can assess. UNDETERMINED means:\n"
    "seek human/legal review.\n"
    "============================================================"
)


class MissingDisclaimerError(ValueError):
    """Refusal to render user-facing output without the disclaimer (INV-4)."""


class AsOfMismatchError(ValueError):
    """Refusal to stamp a report with an as_of its verdicts were not
    evaluated at (R4)."""


def _safe(text):
    """Neutralize newlines in author-controlled strings so no fact name or
    reason can inject a forged report line (Gate-2 bypass-hunt finding)."""
    return str(text).replace("\r", "\\r").replace("\n", "\\n")


def _render_node(node, depth):
    pad = "  " * depth
    if node.get("op") == "fact":
        # Render the CONDITION (fact op value), not the bare fact name: the
        # leaf's value is the truth of the TEST, so "interaction_disclosed ->
        # TRUE" read as if the fact were true when the user had answered No.
        test = node.get("test") or {}
        op = "in" if test.get("op") == "in" else "="
        expected = test.get("value")
        expected = (
            "[" + ", ".join(str(v) for v in expected) + "]"
            if isinstance(expected, list) else str(expected)
        )
        return [
            f"{pad}- {_safe(node['fact'])} {op} {_safe(expected)} -> {node['value']} "
            f"[{_safe(node['citation']['corpus_id'])} {_safe(node['citation']['article'])}]"
        ]
    if node.get("op") == "scope":
        # X1: a NOT_APPLICABLE / scope-undetermined leaf carries its own
        # citation (INV-5 non-vacuous), rendered like a fact leaf's.
        cite = node.get("citation", {})
        header = f"{pad}- scope -> {node.get('value', '?')}"
        if node.get("reason"):
            header += f" ({_safe(node['reason'])})"
        header += (
            f" [{_safe(cite.get('corpus_id', ''))} {_safe(cite.get('article', ''))}]"
        )
        lines = [header]
        for child in node.get("children", []):
            lines.extend(_render_node(child, depth + 1))
        return lines
    header = f"{pad}- {_safe(node.get('op', '?'))} -> {node.get('value', '?')}"
    if node.get("reason"):
        header += f" ({_safe(node['reason'])})"
    lines = [header]
    for child in node.get("children", []):
        lines.extend(_render_node(child, depth + 1))
    return lines


def _cite_text(cite):
    """"Art. 50(1)" + paragraph "1" must not render as "Art. 50(1)(1)": our
    rules already carry the paragraph inside the article string. Append the
    paragraph only when it adds information."""
    article = str(cite.get("article", ""))
    paragraph = str(cite.get("paragraph", "")).strip()
    if not paragraph or paragraph in article:
        return f"{cite.get('corpus_id', '')} {article}"
    return f"{cite.get('corpus_id', '')} {article}({paragraph})"


def _iter_nodes(node):
    yield node
    for child in node.get("children", []):
        yield from _iter_nodes(child)


def _deadline_of(verdict):
    """The upcoming deadline of an INACTIVE verdict (UNDETERMINED + an
    op=='applicability' leaf), read from the C1 structured 'applies_from'
    field - never parsed from a reason string (ADR-012, Gate-5 C2).
    Only a FUTURE window counts (verdict.as_of < applies_from): core emits
    the same leaf for a rule past its applies_until, which is expired, not
    upcoming (verify 2026-09-02 B1; ADR-017)."""
    if verdict.status != "UNDETERMINED":
        return None
    for node in _iter_nodes(verdict.explanation):
        if node.get("op") == "applicability" and "applies_from" in node:
            if dt.date.fromisoformat(node["applies_from"]) <= verdict.as_of:
                return None
            return node["applies_from"], node.get("citation", {})
    return None


def _deadlines_section(verdicts, i18n):
    # Known limitation (hunt F2, disclosed): because X4 precedence is
    # temporal-before-scope, a rule that is out of material scope still shows
    # a future deadline while temporally inactive (it over-warns, never
    # under-warns). Fixing it would evaluate scope during the inactive window,
    # changing the owner-fixed precedence - out of scope for Gate 5.
    ui = i18n["ui"]
    lines = ["", f"{ui['deadlines_header']}:"]
    found = False
    for verdict in verdicts:
        deadline = _deadline_of(verdict)
        if deadline is None:
            continue
        found = True
        applies_from, cite = deadline
        lines.append(
            f"  - {_safe(verdict.rule_id)}: {_safe(applies_from)} "
            f"[{_safe(cite.get('corpus_id', ''))} {_safe(cite.get('article', ''))}]"
        )
    if not found:
        lines.append(f"  {ui['deadlines_none']}")
    lines.append("")
    return lines


def render_report(verdicts, as_of, corpus_version, disclaimer, i18n=None):
    """Render the report. i18n=None keeps the raw English shape (existing
    callers unchanged); an i18n bundle localizes status labels, adds a
    rationale line per verdict, and appends the deadlines section - all
    verdict content stays inside this one function (ADR-012(2))."""
    if disclaimer != DISCLAIMER:
        raise MissingDisclaimerError(
            "refusing to render: output lacks the exact NOT-LEGAL-ADVICE block"
        )
    if isinstance(as_of, dt.datetime) or not isinstance(as_of, dt.date):
        raise AsOfMismatchError(f"as_of must be a datetime.date, got {as_of!r}")
    stale = [verdict.rule_id for verdict in verdicts if verdict.as_of != as_of]
    if stale:
        raise AsOfMismatchError(
            f"verdicts evaluated at a different as_of than the report stamp "
            f"{as_of.isoformat()}: {stale}"
        )
    lines = [DISCLAIMER, ""]
    # ADR-012(6): the engine's own Art. 50(1)-style AI-based-interaction
    # disclosure, carried on the report artifact (both CLI modes).
    if i18n and i18n["ui"].get("ai_disclosure"):
        lines.append(i18n["ui"]["ai_disclosure"])
        lines.append("")
    lines += [
        f"as_of: {as_of.isoformat()}",
        f"corpus_version: {corpus_version}",
        "",
    ]
    for verdict in verdicts:
        cite = verdict.citation
        status_label = (
            i18n["status_labels"][verdict.status] if i18n else verdict.status
        )
        lines.append(
            f"[{_safe(status_label)}] {_safe(verdict.rule_id)} "
            f"({_safe(_cite_text(cite))})"
        )
        if i18n:
            rationale = i18n["rationales"].get(verdict.rationale_key)
            if rationale:
                lines.append(f"  -> {_safe(rationale)}")
        if verdict.unknown_facts:
            lines.append(
                "  unknown facts: "
                + ", ".join(_safe(name) for name in verdict.unknown_facts)
            )
        lines.extend(_render_node(verdict.explanation, depth=1))
        lines.append("")
    if i18n:
        lines.extend(_deadlines_section(verdicts, i18n))
    return "\n".join(lines)


def _corpus_status(corpus_version):
    """FINAL | PROVISIONAL. PROVISIONAL while on a preOJ corpus branch: the
    manifest's omnibus source is PROVISIONAL until OJ publication bumps
    corpus_version (dropping 'preOJ'). Derived from the version string so the
    renderer stays pure (no manifest I/O), tracking the manifest by design."""
    return "PROVISIONAL" if "preoj" in corpus_version.lower() else "FINAL"


def render_structured(verdicts, as_of, corpus_version, disclaimer):
    """ADR-012(2) successor to render_report with the SAME structural refusal:
    identical exact-disclaimer and R4 as_of gates, but returns a plain-data
    dict for the web path (all verdict content originates here, never in JS)."""
    if disclaimer != DISCLAIMER:
        raise MissingDisclaimerError(
            "refusing to render: output lacks the exact NOT-LEGAL-ADVICE block"
        )
    if isinstance(as_of, dt.datetime) or not isinstance(as_of, dt.date):
        raise AsOfMismatchError(f"as_of must be a datetime.date, got {as_of!r}")
    stale = [verdict.rule_id for verdict in verdicts if verdict.as_of != as_of]
    if stale:
        raise AsOfMismatchError(
            f"verdicts evaluated at a different as_of than the report stamp "
            f"{as_of.isoformat()}: {stale}"
        )
    deadlines = []
    for verdict in verdicts:
        deadline = _deadline_of(verdict)
        if deadline is not None:
            applies_from, cite = deadline
            deadlines.append({
                "rule_id": verdict.rule_id,
                "applies_from": applies_from,
                "citation": copy.deepcopy(cite),
            })
    return {
        "disclaimer": DISCLAIMER,
        "as_of": as_of.isoformat(),
        "corpus_version": corpus_version,
        "corpus_status": _corpus_status(corpus_version),
        "deadlines": deadlines,
        "verdicts": [_structured_verdict(verdict) for verdict in verdicts],
    }


def _structured_verdict(verdict):
    # Tier B1 (2026-09-02): expose the temporally-INACTIVE sub-state as
    # structured fields (read from the applicability leaf via _deadline_of,
    # never from a reason string - ADR-012 C2) so the web can label
    # "not yet applicable (from <date>)" instead of a generic UNDETERMINED.
    # The status itself is untouched (oracle frozen).
    deadline = _deadline_of(verdict)
    return {
        "rule_id": verdict.rule_id,
        "status": verdict.status,
        "inactive": deadline is not None,
        "applies_from": deadline[0] if deadline is not None else None,
        "citation": dict(verdict.citation),
        "rationale_key": verdict.rationale_key,
        "unknown_facts": list(verdict.unknown_facts),
        "explanation": copy.deepcopy(verdict.explanation),
    }
