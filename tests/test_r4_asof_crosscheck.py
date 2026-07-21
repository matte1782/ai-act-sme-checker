# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""R4 (Gate-2 residual): renderer as_of cross-check.

render_report(verdicts, as_of=..) must raise if any Verdict.as_of
differs from the argument: a report must never stamp a date its
verdicts were not evaluated at.

ADR-008 classes enumerated here (render-input validation surface):
- (4) wrong type: datetime (not date) as_of rejected even when the
  calendar day matches;
- (6) boundary: off-by-one-day mismatch rejected in both directions;
- (7) duplicate/aggregate: one stale verdict among fresh ones is
  enough to refuse;
- control: matching as_of renders and stamps the date.
"""
import datetime as dt

import pytest

from engine.core import evaluate
from engine.loader import parse_rule
from engine.render import DISCLAIMER, AsOfMismatchError, render_report

AS_OF = dt.date(2026, 7, 1)
CORPUS_V = "test-corpus-v1"


def make_verdicts(as_of=AS_OF, rid="r-r4"):
    rule = parse_rule(
        {
            "id": rid,
            "legal_source": {
                "corpus_id": "TEST-ACT-1",
                "article": "Art. 4",
                "paragraph": "1",
            },
            "applies_from": "2026-01-01",
            "logic": {"fact": "f_true", "op": "eq", "value": True},
            "verdict": "COMPLIANT",
            "rationale_key": "test.r4",
        }
    )
    return evaluate([rule], {"f_true": True}, as_of, CORPUS_V)


@pytest.mark.parametrize("delta", [-1, 1])
def test_off_by_one_day_mismatch_raises(delta):
    # ADR-008 (6)
    with pytest.raises(AsOfMismatchError):
        render_report(
            make_verdicts(),
            AS_OF + dt.timedelta(days=delta),
            CORPUS_V,
            disclaimer=DISCLAIMER,
        )


def test_single_stale_verdict_among_fresh_raises():
    # ADR-008 (7): aggregate check, not first-element check.
    stale = make_verdicts(as_of=AS_OF - dt.timedelta(days=30), rid="r-stale")
    fresh = make_verdicts(rid="r-fresh")
    with pytest.raises(AsOfMismatchError):
        render_report(fresh + stale, AS_OF, CORPUS_V, disclaimer=DISCLAIMER)


def test_datetime_as_of_rejected_even_when_day_matches():
    # ADR-008 (4): same strict gate the core applies (Gate-2 lesson).
    with pytest.raises(AsOfMismatchError):
        render_report(
            make_verdicts(),
            dt.datetime(2026, 7, 1, 0, 0),
            CORPUS_V,
            disclaimer=DISCLAIMER,
        )


def test_matching_as_of_renders():
    out = render_report(make_verdicts(), AS_OF, CORPUS_V, disclaimer=DISCLAIMER)
    assert "2026-07-01" in out
    assert "[COMPLIANT] r-r4" in out
