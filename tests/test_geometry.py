"""Geometry and quantity invariants for the cutting strategies.

These tests intentionally validate observable layouts rather than the internal
heuristics. They do not claim that a layout is globally optimal or prove that
the emitted cut list is a complete executable guillotine cut sequence.
"""

from collections import Counter

import pytest

from quercut.models import CutConfig, Part, StockSheet
from quercut.strategies.advanced import AdvancedGuillotineStrategy
from quercut.strategies.optimal import OptimalGuillotineStrategy
from quercut.strategies.simple_cross import SimpleCrossStrategy
from quercut.strategies.simple_rip import SimpleRipStrategy


STRATEGY_FACTORIES = [
    pytest.param(SimpleRipStrategy, id="simple-rip"),
    pytest.param(SimpleCrossStrategy, id="simple-cross"),
    pytest.param(OptimalGuillotineStrategy, id="optimal-rip-cross"),
    pytest.param(AdvancedGuillotineStrategy, id="advanced"),
]


def assert_layout_geometry(layouts, stock, config, parts):
    """Check bounds, orientation, identity and non-overlap for one stock size."""
    placed_by_part = Counter()

    for layout in layouts:
        assert layout.stock_length == stock.length
        assert layout.stock_width == stock.width

        for placement in layout.placements:
            assert placement.length > 0
            assert placement.width > 0

            # Coordinates are measured from the lower-left corner; trims
            # remove material from the corresponding stock edges.
            assert placement.x >= config.trim_left
            assert placement.y >= config.trim_bottom
            assert placement.x + placement.length <= stock.length - config.trim_right
            assert placement.y + placement.width <= stock.width - config.trim_top

            source = next(p for p in parts if p.global_index == placement.global_index)
            expected_size = (
                (source.width, source.length)
                if placement.rotated
                else (source.length, source.width)
            )
            assert (placement.length, placement.width) == expected_size
            assert not placement.rotated or source.rotatable

            placed_by_part[placement.global_index] += 1

        # Rectangles belonging to the same sheet must not overlap.
        placements = layout.placements
        for i, first in enumerate(placements):
            for second in placements[i + 1 :]:
                overlap_x = (
                    first.x < second.x + second.length
                    and second.x < first.x + first.length
                )
                overlap_y = (
                    first.y < second.y + second.width
                    and second.y < first.y + first.width
                )
                assert not (overlap_x and overlap_y), (
                    f"Overlapping placements: {first!r} and {second!r}"
                )

    return placed_by_part


@pytest.mark.parametrize("strategy_factory", STRATEGY_FACTORIES)
def test_layouts_respect_bounds_do_not_overlap_and_preserve_part_identity(strategy_factory):
    stock = StockSheet(length=180, width=120, is_unlimited=False)
    config = CutConfig(
        kerf=3,
        trim_left=5,
        trim_right=7,
        trim_top=4,
        trim_bottom=6,
    )
    parts = [
        Part(label="wide", length=70, width=35, quantity=2, global_index=10),
        Part(label="small", length=30, width=25, quantity=3, global_index=20),
    ]

    strategy = strategy_factory()
    layouts = strategy.layout([stock], parts, config)

    placed = assert_layout_geometry(layouts, stock, config, parts)

    assert placed == Counter({10: 2, 20: 3})
    assert strategy.unplaced_parts == []


@pytest.mark.parametrize("strategy_factory", STRATEGY_FACTORIES)
def test_kerf_prevents_two_parts_from_touching_across_an_insufficient_span(strategy_factory):
    stock = StockSheet(length=100, width=40, is_unlimited=False)
    parts = [
        Part(label="panel", length=50, width=40, quantity=2,
             rotatable=False, global_index=1)
    ]
    strategy = strategy_factory()

    layouts = strategy.layout([stock], parts, CutConfig(kerf=1))

    placed = assert_layout_geometry(layouts, stock, CutConfig(kerf=1), parts)

    # Two 50 mm parts plus a 1 mm saw kerf need 101 mm.
    assert placed == Counter({1: 1})
    assert sum(item["remaining"] for item in strategy.unplaced_parts) == 1


@pytest.mark.parametrize("strategy_factory", STRATEGY_FACTORIES)
def test_rotation_is_used_only_when_the_part_allows_it(strategy_factory):
    stock = StockSheet(length=30, width=40, is_unlimited=False)

    fixed_part = Part(
        label="fixed", length=40, width=30, quantity=1,
        rotatable=False, global_index=1
    )
    fixed_strategy = strategy_factory()
    fixed_layouts = fixed_strategy.layout([stock], [fixed_part], CutConfig())

    assert fixed_layouts == []
    assert sum(item["remaining"] for item in fixed_strategy.unplaced_parts) == 1

    rotatable_part = Part(
        label="rotatable", length=40, width=30, quantity=1,
        rotatable=True, global_index=2
    )
    rotatable_strategy = strategy_factory()
    rotatable_layouts = rotatable_strategy.layout(
        [stock], [rotatable_part], CutConfig()
    )

    placed = assert_layout_geometry(
        rotatable_layouts, stock, CutConfig(), [rotatable_part]
    )
    assert placed == Counter({2: 1})
    assert rotatable_layouts[0].placements[0].rotated is True


def test_empty_stock_list_is_rejected_by_each_strategy():
    part = Part(label="part", length=10, width=10, quantity=1)

    for strategy_factory in (factory.values[0] for factory in STRATEGY_FACTORIES):
        with pytest.raises(ValueError):
            strategy_factory().layout([], [part], CutConfig())
