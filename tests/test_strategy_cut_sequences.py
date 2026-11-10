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
    [SimpleRipStrategy, OptimalGuillotineStrategy],
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
    layouts = strategy_factory().layout([stock], [part], CutConfig(kerf=2))

    assert len(layouts) == 1
    assert validate_guillotine_layout(layouts[0], CutConfig(kerf=2))


def test_simple_cross_strategy_emits_cuts_in_non_executable_order():
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
    layouts = SimpleCrossStrategy().layout([stock], [part], config)

    assert len(layouts) == 1
    # SimpleCross emits the vertical cut before the horizontal cut that
    # creates the narrower region in which that vertical cut belongs.
    with pytest.raises(ValueError, match="currently available rectangle"):
        validate_guillotine_layout(layouts[0], config)


def test_advanced_strategy_cut_order_is_rejected_by_independent_checker():
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
    layouts = AdvancedGuillotineStrategy().layout([stock], [part], config)

    assert len(layouts) == 1
    # The advanced strategy also emits a cut that cannot be executed
    # from the currently available rectangular regions.
    with pytest.raises(ValueError, match="currently available rectangle"):
        validate_guillotine_layout(layouts[0], config)
