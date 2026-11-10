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
        ("horizontal", "vertical"),
        ("vertical", "horizontal"),
    ],
)
def test_advanced_strategy_emits_inner_cut_before_separating_first_strip(
    preferred_direction, expected_first_cut
):
    """Characterize the ordering defect for either initial strip direction."""
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

    # The first cut lies inside the initial strip, which has not yet
    # been separated from the original sheet.
    with pytest.raises(ValueError, match="currently available rectangle"):
        validate_guillotine_layout(layouts[0], config)


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
def test_advanced_strategy_recurse_into_strip_remnant_before_separating_it(
    preferred_direction, parts, expected_second_part_origin
):
    """Ensure a recursive remnant is actually populated before checking its cuts."""
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

    # A cut made inside the remnant is currently emitted before the cut
    # that separates that remnant from its parent region.
    with pytest.raises(ValueError, match="currently available rectangle"):
        validate_guillotine_layout(layouts[0], config)
