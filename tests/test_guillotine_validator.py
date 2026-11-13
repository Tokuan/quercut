"""Tests for the independent ordered guillotine-cut simulator."""

import pytest

from quercut.models import Cut, CutConfig, CutLayout, Direction, PlacedPart
from quercut.validation.guillotine import validate_guillotine_layout


def placement(x, y, length, width):
    return PlacedPart(
        part_label="part", x=x, y=y, length=length, width=width,
        global_index=1,
    )


def test_accepts_two_parts_from_a_real_ordered_cut_sequence():
    layout = CutLayout(
        layout_id=1,
        stock_length=100,
        stock_width=50,
        placements=[
            placement(0, 0, 40, 50),
            placement(42, 0, 30, 50),
        ],
        cuts=[
            Cut(40, 0, 40, 50, Direction.VERTICAL),
            Cut(72, 0, 72, 50, Direction.VERTICAL),
        ],
    )

    assert validate_guillotine_layout(layout, CutConfig(kerf=2)) is True


def test_rejects_cut_that_is_not_full_span_of_a_current_region():
    layout = CutLayout(
        layout_id=1,
        stock_length=100,
        stock_width=50,
        placements=[placement(0, 0, 40, 50)],
        cuts=[Cut(40, 5, 40, 45, Direction.VERTICAL)],
    )

    with pytest.raises(ValueError, match="currently available rectangle"):
        validate_guillotine_layout(layout, CutConfig())


def test_rejects_a_cut_sequence_that_uses_a_region_before_it_exists():
    # The first cut spans the whole sheet. It splits the sheet into two
    # regions, so the following full-height cut can no longer be executed.
    layout = CutLayout(
        layout_id=1,
        stock_length=100,
        stock_width=80,
        placements=[placement(0, 0, 40, 30)],
        cuts=[
            Cut(0, 30, 100, 30, Direction.HORIZONTAL),
            Cut(40, 0, 40, 80, Direction.VERTICAL),
        ],
    )

    with pytest.raises(ValueError, match="currently available rectangle"):
        validate_guillotine_layout(layout, CutConfig())


def test_rejects_placement_without_cuts_separating_it_from_waste():
    layout = CutLayout(
        layout_id=1,
        stock_length=100,
        stock_width=50,
        placements=[placement(0, 0, 40, 50)],
        cuts=[],
    )

    with pytest.raises(ValueError, match="terminal rectangle"):
        validate_guillotine_layout(layout, CutConfig())


def test_accounts_for_trim_offsets():
    layout = CutLayout(
        layout_id=1,
        stock_length=110,
        stock_width=60,
        placements=[placement(5, 3, 40, 50)],
        cuts=[Cut(45, 3, 45, 53, Direction.VERTICAL)],
    )
    config = CutConfig(
        kerf=2,
        trim_left=5,
        trim_right=5,
        trim_top=7,
        trim_bottom=3,
    )

    assert validate_guillotine_layout(layout, config) is True


@pytest.mark.parametrize("remaining", [1, 2])
def test_rejects_cut_when_far_side_material_does_not_exceed_kerf(remaining):
    kerf = 2
    cut_x = 100 - remaining
    layout = CutLayout(
        layout_id=1,
        stock_length=100,
        stock_width=50,
        placements=[placement(0, 0, cut_x, 50)],
        cuts=[Cut(cut_x, 0, cut_x, 50, Direction.VERTICAL)],
    )

    with pytest.raises(ValueError, match="material beyond the kerf"):
        validate_guillotine_layout(layout, CutConfig(kerf=kerf))


def test_accepts_cut_when_material_after_kerf_is_positive():
    kerf = 2
    cut_x = 97  # 3 mm remain before the kerf; 1 mm remains after it.
    layout = CutLayout(
        layout_id=1,
        stock_length=100,
        stock_width=50,
        placements=[placement(0, 0, cut_x, 50)],
        cuts=[Cut(cut_x, 0, cut_x, 50, Direction.VERTICAL)],
    )

    assert validate_guillotine_layout(layout, CutConfig(kerf=kerf)) is True


def test_accepts_part_flush_with_sheet_edge_without_an_extra_cut():
    layout = CutLayout(
        layout_id=1,
        stock_length=100,
        stock_width=50,
        placements=[placement(0, 0, 100, 50)],
        cuts=[],
    )

    assert validate_guillotine_layout(layout, CutConfig(kerf=2)) is True


def test_rejects_redundant_cut_exactly_on_region_edge():
    layout = CutLayout(
        layout_id=1,
        stock_length=100,
        stock_width=50,
        placements=[placement(0, 0, 100, 50)],
        cuts=[Cut(100, 0, 100, 50, Direction.VERTICAL)],
    )

    with pytest.raises(ValueError, match="material beyond the kerf"):
        validate_guillotine_layout(layout, CutConfig(kerf=2))
