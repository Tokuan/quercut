"""Поведение простых стратегий: направление первого реза и порядок укладки."""

import pytest

from quercut.models import CutConfig, Part, StockSheet, Direction
from quercut.strategy_factory import create_strategy
from quercut.strategies.optimal import OptimalGuillotineStrategy
from quercut.strategies.simple_cross import SimpleCrossStrategy
from quercut.strategies.simple_rip import SimpleRipStrategy
from quercut.validation.guillotine import validate_guillotine_layout


def test_factory_maps_preferred_direction_to_simple_strategy():
    assert isinstance(create_strategy("simple", "horizontal"), SimpleRipStrategy)
    assert isinstance(create_strategy("simple", "vertical"), SimpleCrossStrategy)
    assert isinstance(create_strategy("simple", "both"), OptimalGuillotineStrategy)


def test_simple_rip_starts_with_cut_along_the_sheet():
    stock = StockSheet(length=100, width=80)
    parts = [
        Part("a", 40, 30, 2, False, 1),
        Part("b", 20, 20, 2, False, 2),
    ]
    config = CutConfig(kerf=2)

    layouts = SimpleRipStrategy().layout([stock], parts, config)

    assert layouts
    assert layouts[0].cuts[0].direction == Direction.HORIZONTAL
    for layout in layouts:
        assert validate_guillotine_layout(layout, config)


def test_simple_cross_starts_with_cut_across_the_sheet():
    stock = StockSheet(length=100, width=80)
    parts = [
        Part("a", 40, 30, 2, False, 1),
        Part("b", 20, 20, 2, False, 2),
    ]
    config = CutConfig(kerf=2)

    layouts = SimpleCrossStrategy().layout([stock], parts, config)

    assert layouts
    assert layouts[0].cuts[0].direction == Direction.VERTICAL
    for layout in layouts:
        assert validate_guillotine_layout(layout, config)


@pytest.mark.parametrize("strategy_factory", [SimpleRipStrategy, SimpleCrossStrategy])
def test_longest_part_is_placed_before_the_larger_area_one(strategy_factory):
    """Порядок подбора: сначала длина, потом ширина — не площадь.

    60x20 длиннее 50x50, хотя уступает ей по площади, и должна укладываться
    первой.
    """
    stock = StockSheet(length=100, width=80)
    parts = [
        Part("bar", 60, 20, 1, False, 1),
        Part("square", 50, 50, 1, False, 2),
    ]

    layouts = strategy_factory().layout([stock], parts, CutConfig())

    assert layouts
    assert layouts[0].placements[0].length == 60
    for layout in layouts:
        assert validate_guillotine_layout(layout, CutConfig())


def test_equal_length_parts_continue_the_same_column():
    """Равные по длине детали заполняют одну колонку, а не открывают новую."""
    stock = StockSheet(length=100, width=100)
    parts = [
        Part("a", 40, 30, 2, False, 1),
        Part("b", 40, 25, 1, False, 2),
    ]

    layouts = SimpleCrossStrategy().layout([stock], parts, CutConfig())

    assert len(layouts) == 1
    assert len(layouts[0].placements) == 3
    assert {placement.x for placement in layouts[0].placements} == {0}
    assert validate_guillotine_layout(layouts[0], CutConfig())
