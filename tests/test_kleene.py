"""Kleene K3 truth tables: all()=min, any()=max, not() swaps T/F and
preserves UNKNOWN. Exhaustive over {TRUE, FALSE, UNKNOWN}.
"""
import itertools

import pytest

from engine.facts import UNKNOWN, k3_all, k3_any, k3_not

V = [True, False, UNKNOWN]


def rank(value):
    if value is False:
        return 0
    if value is UNKNOWN:
        return 1
    return 2


def test_not_exhaustive():
    assert k3_not(True) is False
    assert k3_not(False) is True
    assert k3_not(UNKNOWN) is UNKNOWN


@pytest.mark.parametrize("a,b", list(itertools.product(V, V)))
def test_all_is_min(a, b):
    expected = a if rank(a) <= rank(b) else b
    assert k3_all([a, b]) is expected


@pytest.mark.parametrize("a,b", list(itertools.product(V, V)))
def test_any_is_max(a, b):
    expected = a if rank(a) >= rank(b) else b
    assert k3_any([a, b]) is expected


@pytest.mark.parametrize("a,b,c", list(itertools.product(V, V, V)))
def test_all_any_ternary_consistency(a, b, c):
    assert k3_all([a, b, c]) is k3_all([k3_all([a, b]), c])
    assert k3_any([a, b, c]) is k3_any([k3_any([a, b]), c])


@pytest.mark.parametrize("a,b", list(itertools.product(V, V)))
def test_de_morgan(a, b):
    assert k3_not(k3_all([a, b])) is k3_any([k3_not(a), k3_not(b)])
    assert k3_not(k3_any([a, b])) is k3_all([k3_not(a), k3_not(b)])


def test_empty_identities():
    assert k3_all([]) is True
    assert k3_any([]) is False
