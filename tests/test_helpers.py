import pytest

from app.helpers import (
    has_enough_fabric,
    parse_non_negative_float,
    parse_quantity_to_cut,
    pattern_requires_lining,
)
from tests.factories import make_pattern


def test_pattern_requires_lining_when_yards_are_a_number():
    pattern = make_pattern(lining_yards_required=0.0)
    assert pattern.lining_yards_required == 0.0
    assert pattern_requires_lining(pattern) is True


def test_pattern_does_not_require_lining_when_yards_are_none():
    pattern = make_pattern(lining_yards_required=None)
    assert pattern.lining_yards_required is None
    assert pattern_requires_lining(pattern) is False


def test_parse_non_negative_float_empty_optional_returns_none():
    assert parse_non_negative_float("", "Lining yards required", required=False) is None
    assert parse_non_negative_float("  ", "Lining yards required", required=False) is None


def test_parse_non_negative_float_rejects_negative():
    with pytest.raises(ValueError, match="cannot be negative"):
        parse_non_negative_float("-1", "Estimated hours")


def test_parse_quantity_to_cut_requires_at_least_one():
    with pytest.raises(ValueError, match="at least 1"):
        parse_quantity_to_cut("0")
    assert parse_quantity_to_cut("2") == 2


def test_has_enough_fabric_comparison():
    assert has_enough_fabric(2.5, 1.0) is True
    assert has_enough_fabric(0.5, 1.0) is False
    assert has_enough_fabric(None, 1.0) is None
    assert has_enough_fabric(2.5, None) is None
