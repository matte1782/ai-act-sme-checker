"""L5 minimal text renderer.

The disclaimer block is a STRUCTURAL argument (INV-4): the renderer
refuses to emit any user-facing output unless the caller passes the
exact block. Every verdict is rendered with citation, as_of stamp,
corpus version, and its explanation tree.

R4: the as_of stamp is cross-checked against every Verdict.as_of; a
report must never stamp a date its verdicts were not evaluated at.
"""
import datetime as dt

DISCLAIMER = (
    "=== NOT LEGAL ADVICE / NON COSTITUISCE CONSULENZA LEGALE ===\n"
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
        return [
            f"{pad}- fact {_safe(node['fact'])} -> {node['value']} "
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


def render_report(verdicts, as_of, corpus_version, disclaimer):
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
    lines = [
        DISCLAIMER,
        "",
        f"as_of: {as_of.isoformat()}",
        f"corpus_version: {corpus_version}",
        "",
    ]
    for verdict in verdicts:
        cite = verdict.citation
        lines.append(
            f"[{verdict.status}] {_safe(verdict.rule_id)} "
            f"({_safe(cite['corpus_id'])} {_safe(cite['article'])}({_safe(cite['paragraph'])}))"
        )
        if verdict.unknown_facts:
            lines.append(
                "  unknown facts: "
                + ", ".join(_safe(name) for name in verdict.unknown_facts)
            )
        lines.extend(_render_node(verdict.explanation, depth=1))
        lines.append("")
    return "\n".join(lines)
