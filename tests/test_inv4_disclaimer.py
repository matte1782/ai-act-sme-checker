"""INV-4 disclaimer: rendering without the disclaimer block raises;
output always contains it. The disclaimer is a structural argument.
"""
import datetime as dt

import pytest

from engine.core import evaluate
from engine.loader import parse_rule
from engine.render import DISCLAIMER, MissingDisclaimerError, render_report

AS_OF = dt.date(2026, 7, 1)
CORPUS_V = "test-corpus-v1"


def verdicts():
    rule = parse_rule(
        {
            "id": "r-inv4",
            "legal_source": {
                "corpus_id": "TEST-ACT-1",
                "article": "Art. 4",
                "paragraph": "1",
            },
            "applies_from": "2026-01-01",
            "logic": {"fact": "f_true", "op": "eq", "value": True},
            "verdict": "COMPLIANT",
            "rationale_key": "test.inv4",
        }
    )
    return evaluate([rule], {"f_true": True}, AS_OF, CORPUS_V)


def test_output_contains_disclaimer_block():
    out = render_report(verdicts(), AS_OF, CORPUS_V, disclaimer=DISCLAIMER)
    assert DISCLAIMER in out
    assert "NOT LEGAL ADVICE" in out


def test_render_with_none_disclaimer_raises():
    with pytest.raises(MissingDisclaimerError):
        render_report(verdicts(), AS_OF, CORPUS_V, disclaimer=None)


@pytest.mark.parametrize(
    "tampered",
    [
        "",
        "some other text",
        DISCLAIMER.replace("NOT", "TOTALLY"),
        DISCLAIMER[:-10],
        DISCLAIMER.lower(),
    ],
)
def test_render_with_tampered_disclaimer_raises(tampered):
    with pytest.raises(MissingDisclaimerError):
        render_report(verdicts(), AS_OF, CORPUS_V, disclaimer=tampered)


def test_output_shows_citation_asof_corpus_version():
    out = render_report(verdicts(), AS_OF, CORPUS_V, disclaimer=DISCLAIMER)
    assert "TEST-ACT-1" in out
    assert "Art. 4" in out
    assert "2026-07-01" in out
    assert CORPUS_V in out
