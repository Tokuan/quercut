"""SVG cutting-map geometry tests."""

from quercut.models import (
    Cut,
    CutConfig,
    CutLayout,
    Direction,
    PlacedPart,
)
from quercut.visualization import (
    _find_free_segments_along_cut,
    _render_layout,
    generate_svg,
)


def test_svg_converts_lower_left_layout_coordinates_to_top_left_svg_coordinates():
    layout = CutLayout(
        layout_id=1,
        stock_length=100,
        stock_width=80,
        placements=[
            PlacedPart("panel", x=10, y=5, length=20, width=10, global_index=0)
        ],
        cuts=[
            Cut(30, 5, 30, 15, Direction.VERTICAL),
            Cut(10, 15, 30, 15, Direction.HORIZONTAL),
        ],
    )
    config = CutConfig(
        kerf=2,
        trim_left=3,
        trim_right=4,
        trim_top=6,
        trim_bottom=7,
    )

    svg = _render_layout(layout, config)

    # Physical y=5..15 maps to SVG y=65..75 on an 80 mm sheet.
    assert '<rect x="10" y="65" width="20" height="10"' in svg

    # The usable rectangle starts at SVG y=trim_top, not trim_bottom.
    assert '<rect x="3" y="6" width="93" height="67"' in svg

    # Kerf bands extend in the positive model axis, which is upward for H cuts.
    assert '<rect x="30" y="65" width="2.0" height="10"' in svg
    assert '<rect x="10" y="63.0" width="20" height="2.0"' in svg

    # Reference lines are transformed too.
    assert '<line x1="30" y1="65" x2="30" y2="75"' in svg
    assert '<line x1="10" y1="65" x2="30" y2="65"' in svg


def test_free_segments_use_continuous_geometry_and_actual_kerf_width():
    cut = Cut(20, 0, 20, 50, Direction.VERTICAL)
    placements = [
        PlacedPart("left", x=0, y=0, length=20, width=10),
        PlacedPart("right", x=22, y=20, length=20, width=10),
    ]

    assert _find_free_segments_along_cut(cut, placements, kerf=2) == [
        {"start": 10, "end": 20},
        {"start": 30, "end": 50},
    ]


def test_free_segments_support_fractional_coordinates():
    cut = Cut(100.5, 0.25, 100.5, 50.75, Direction.VERTICAL)
    placements = [
        PlacedPart("left", x=0, y=0.25, length=100.5, width=10.5),
        PlacedPart("right", x=101.75, y=20.5, length=20, width=10.25),
    ]

    assert _find_free_segments_along_cut(cut, placements, kerf=1.25) == [
        {"start": 10.75, "end": 20.5},
        {"start": 30.75, "end": 50.75},
    ]


def test_large_fractional_sheet_can_be_rendered_without_a_per_millimeter_grid():
    layout = CutLayout(
        layout_id=7,
        stock_length=3000.5,
        stock_width=2000.5,
        placements=[
            PlacedPart(
                "panel",
                x=10.25,
                y=20.5,
                length=100.5,
                width=50.25,
                global_index=0,
            )
        ],
    )

    svg = _render_layout(layout, CutConfig(kerf=3.2))

    assert 'width="100.5" height="50.25"' in svg
    assert 'y="1929.75"' in svg


def test_generate_svg_handles_empty_layouts():
    assert generate_svg([], CutConfig()) == (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1" width="1"></svg>'
    )



def test_horizontal_free_segments_use_the_positive_y_kerf_side():
    cut = Cut(0, 20, 50, 20, Direction.HORIZONTAL)
    placements = [
        PlacedPart("below", x=0, y=0, length=10, width=20),
        PlacedPart("above", x=20, y=22, length=10, width=20),
    ]

    assert _find_free_segments_along_cut(cut, placements, kerf=2) == [
        {"start": 10, "end": 20},
        {"start": 30, "end": 50},
    ]
