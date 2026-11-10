"""Deterministic randomized invariant tests for cutting strategies."""

from collections import Counter
from random import Random

import pytest

from quercut.models import CutConfig, Part, StockSheet
from quercut.strategies.advanced import AdvancedGuillotineStrategy
from quercut.strategies.optimal import OptimalGuillotineStrategy
from quercut.strategies.simple_cross import SimpleCrossStrategy
from quercut.strategies.simple_rip import SimpleRipStrategy
from quercut.validation.guillotine import validate_guillotine_layout


BASIC_STRATEGIES = [
    pytest.param(SimpleRipStrategy, id="simple-rip"),
    pytest.param(SimpleCrossStrategy, id="simple-cross"),
    pytest.param(OptimalGuillotineStrategy, id="optimal"),
]


def make_random_case(seed):
    """Build a small, reproducible finite-sheet cutting problem."""
    rng = Random(seed)
    stock = StockSheet(
        length=rng.randint(95, 175),
        width=rng.randint(75, 140),
    )
    trim_left = rng.randint(0, 4)
    trim_right = rng.randint(0, 4)
    trim_top = rng.randint(0, 4)
    trim_bottom = rng.randint(0, 4)
    config = CutConfig(
        kerf=rng.choice((0, 1, 2, 3)),
        trim_left=trim_left,
        trim_right=trim_right,
        trim_top=trim_top,
        trim_bottom=trim_bottom,
    )
    parts = [
        Part(
            label=f"part-{index}",
            length=rng.randint(8, 65),
            width=rng.randint(8, 55),
            quantity=rng.randint(1, 3),
            rotatable=rng.choice((True, False)),
            global_index=index,
        )
        for index in range(rng.randint(1, 4))
    ]
    return stock, parts, config


def assert_random_result_is_consistent(strategy, layouts, stock, parts, config):
    """Check identity, quantities, geometry and executable cuts."""
    parts_by_index = {part.global_index: part for part in parts}
    placed_counts = Counter()

    for layout in layouts:
        assert layout.stock_length == stock.length
        assert layout.stock_width == stock.width
        assert validate_guillotine_layout(layout, config)

        for placement in layout.placements:
            assert placement.global_index in parts_by_index
            source = parts_by_index[placement.global_index]
            expected_size = (
                (source.width, source.length)
                if placement.rotated
                else (source.length, source.width)
            )
            assert (placement.length, placement.width) == expected_size
            assert not placement.rotated or source.rotatable

            assert placement.x >= config.trim_left
            assert placement.y >= config.trim_bottom
            assert placement.x + placement.length <= stock.length - config.trim_right
            assert placement.y + placement.width <= stock.width - config.trim_top

            placed_counts[placement.global_index] += 1

        for index, first in enumerate(layout.placements):
            for second in layout.placements[index + 1:]:
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

    unplaced_by_label = {
        item["label"]: item["remaining"]
        for item in strategy.unplaced_parts
    }
    for part in parts:
        assert (
            placed_counts[part.global_index]
            + unplaced_by_label.get(part.label, 0)
            == part.quantity
        )


@pytest.mark.parametrize("strategy_factory", BASIC_STRATEGIES)
def test_basic_strategies_preserve_randomized_layout_invariants(strategy_factory):
    """Exercise basic strategies against a fixed corpus of generated inputs."""
    for seed in range(20):
        stock, parts, config = make_random_case(seed)
        strategy = strategy_factory()
        layouts = strategy.layout([stock], parts, config)

        assert_random_result_is_consistent(
            strategy, layouts, stock, parts, config
        )


@pytest.mark.parametrize("preferred_direction", ["horizontal", "vertical", "both"])
@pytest.mark.parametrize("strip_sorting", ["desc", "asc", "area"])
@pytest.mark.parametrize("use_remnants", [False, True])
def test_advanced_strategy_preserves_randomized_layout_invariants(
    preferred_direction, strip_sorting, use_remnants
):
    """Cover Advanced strategy modes with reproducible randomized inputs."""
    for seed in range(20):
        stock, parts, config = make_random_case(seed)
        strategy = AdvancedGuillotineStrategy(
            preferred_direction=preferred_direction,
            strip_sorting=strip_sorting,
            use_remnants=use_remnants,
        )
        layouts = strategy.layout([stock], parts, config)

        try:
            assert_random_result_is_consistent(
                strategy, layouts, stock, parts, config
            )
        except AssertionError as error:
            raise AssertionError(
                "Randomized case failed: "
                f"seed={seed}, direction={preferred_direction}, "
                f"sorting={strip_sorting}, use_remnants={use_remnants}, "
                f"stock={stock!r}, parts={parts!r}, config={config!r}"
            ) from error
