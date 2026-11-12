"""Apply the independent cut-sequence checker to real strategy output."""

import pytest

from quercut.models import CutConfig, Part, StockSheet
from quercut.strategies.advanced import AdvancedGuillotineStrategy
from quercut.strategies.optimal import OptimalGuillotineStrategy
from quercut.strategies.simple_cross import SimpleCrossStrategy
from quercut.strategies.simple_rip import SimpleRipStrategy
from quercut.validation.guillotine import validate_guillotine_layout


@pytest.mark.parametrize(
    "strategy_factory",
    [SimpleRipStrategy, OptimalGuillotineStrategy, SimpleCrossStrategy],
)
def test_basic_strategies_emit_executable_cut_sequences(strategy_factory):
    stock = StockSheet(length=100, width=80)
    part = Part(
        label="panel",
        length=40,
        width=30,
        quantity=1,
        rotatable=False,
        global_index=1,
    )
    config = CutConfig(kerf=2)
    layouts = strategy_factory().layout([stock], [part], config)

    assert len(layouts) == 1
    assert validate_guillotine_layout(layouts[0], config)


@pytest.mark.parametrize(
    ("preferred_direction", "expected_first_cut"),
    [
        ("horizontal", "horizontal"),
        ("vertical", "vertical"),
    ],
)
def test_advanced_strategy_separates_first_strip_before_inner_cuts(
    preferred_direction, expected_first_cut
):
    """The parent strip-separating cut must be emitted before inner cuts."""
    stock = StockSheet(length=100, width=80)
    part = Part(
        label="panel",
        length=40,
        width=30,
        quantity=1,
        rotatable=False,
        global_index=1,
    )
    config = CutConfig(kerf=2)
    strategy = AdvancedGuillotineStrategy(
        preferred_direction=preferred_direction,
        use_remnants=False,
    )

    layouts = strategy.layout([stock], [part], config)

    assert len(layouts) == 1
    assert layouts[0].cuts
    assert layouts[0].cuts[0].direction.name.lower() == expected_first_cut

    assert validate_guillotine_layout(layouts[0], config)


@pytest.mark.parametrize(
    ("preferred_direction", "parts", "expected_second_part_origin"),
    [
        (
            "horizontal",
            [
                Part("wide", 40, 30, 1, False, 1),
                Part("small", 20, 20, 1, False, 2),
            ],
            (42, 0),
        ),
        (
            "vertical",
            [
                Part("tall", 30, 40, 1, False, 1),
                Part("small", 20, 20, 1, False, 2),
            ],
            (0, 42),
        ),
    ],
)
def test_advanced_strategy_separates_strip_remnant_before_recursive_cuts(
    preferred_direction, parts, expected_second_part_origin
):
    """A strip remnant must be separated before its recursive cuts are emitted."""
    stock = StockSheet(length=100, width=80)
    config = CutConfig(kerf=2)
    strategy = AdvancedGuillotineStrategy(
        preferred_direction=preferred_direction,
        use_remnants=True,
    )

    layouts = strategy.layout([stock], parts, config)

    assert len(layouts) == 1
    assert len(layouts[0].placements) == 2
    origins = {(placement.x, placement.y) for placement in layouts[0].placements}
    assert expected_second_part_origin in origins

    assert validate_guillotine_layout(layouts[0], config)



@pytest.mark.parametrize(
    "strategy_factory",
    [
        SimpleRipStrategy,
        SimpleCrossStrategy,
        OptimalGuillotineStrategy,
        AdvancedGuillotineStrategy,
    ],
)
@pytest.mark.parametrize(
    ("remaining", "expected_placed"),
    [(0, True), (1, False), (2, False), (3, True)],
)
def test_strategies_only_place_parts_with_kerf_safe_remainders(
    strategy_factory, remaining, expected_placed
):
    """A trailing region must be empty or wider than the kerf."""
    stock = StockSheet(length=100, width=50)
    part = Part(
        label="panel",
        length=100 - remaining,
        width=50,
        quantity=1,
        rotatable=False,
        global_index=1,
    )
    config = CutConfig(kerf=2)
    strategy = strategy_factory()

    layouts = strategy.layout([stock], [part], config)
    placements = [
        placement
        for layout in layouts
        for placement in layout.placements
    ]

    assert bool(placements) is expected_placed
    for layout in layouts:
        assert validate_guillotine_layout(layout, config)
