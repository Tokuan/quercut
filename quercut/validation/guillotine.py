"""Independent simulator for executable guillotine cut sequences.

Cut coordinates use the convention emitted by the current strategies: the
coordinate is the near edge of the kerf, and the kerf extends in the positive
X direction for vertical cuts or positive Y direction for horizontal cuts.
"""

from dataclasses import dataclass
from math import isclose, isfinite

from ..models import CutConfig, CutLayout, Direction


@dataclass(frozen=True)
class _Region:
    x: float
    y: float
    length: float
    width: float


def validate_guillotine_layout(
    layout: CutLayout,
    config: CutConfig,
    *,
    tolerance: float = 1e-6,
) -> bool:
    """Return True if placements can be obtained by the ordered cuts.

    Raises ValueError at the first impossible cut or placement. The simulation
    starts from the usable sheet after trims, applies cuts in list order, and
    then requires every placement to equal one of the resulting terminal
    rectangles. Unused terminal rectangles are treated as waste/remnants.

    This deliberately does not inspect a strategy's internal tree.
    """
    values = (
        layout.stock_length,
        layout.stock_width,
        config.trim_left,
        config.trim_right,
        config.trim_top,
        config.trim_bottom,
        config.kerf,
    )
    if not all(isfinite(float(value)) for value in values):
        raise ValueError("Sheet dimensions, trims and kerf must be finite")
    if layout.stock_length <= 0 or layout.stock_width <= 0:
        raise ValueError("Stock dimensions must be positive")
    if config.kerf < 0:
        raise ValueError("Kerf cannot be negative")
    if min(config.trim_left, config.trim_right, config.trim_top, config.trim_bottom) < 0:
        raise ValueError("Trim values cannot be negative")

    x0 = float(config.trim_left)
    y0 = float(config.trim_bottom)
    usable_length = float(layout.stock_length - config.trim_left - config.trim_right)
    usable_width = float(layout.stock_width - config.trim_top - config.trim_bottom)
    if usable_length <= 0 or usable_width <= 0:
        raise ValueError("Trims leave no usable sheet area")

    regions = [_Region(x0, y0, usable_length, usable_width)]
    kerf = float(config.kerf)

    def eq(a: float, b: float) -> bool:
        return isclose(a, b, rel_tol=0.0, abs_tol=tolerance)

    for cut_number, cut in enumerate(layout.cuts, start=1):
        coordinates = (cut.x1, cut.y1, cut.x2, cut.y2)
        if not all(isfinite(float(value)) for value in coordinates):
            raise ValueError(f"Cut {cut_number} has non-finite coordinates")

        if cut.direction == Direction.VERTICAL:
            if not eq(cut.x1, cut.x2) or cut.y2 <= cut.y1:
                raise ValueError(f"Cut {cut_number} is not a valid vertical segment")
            candidates = [
                (i, region)
                for i, region in enumerate(regions)
                if eq(cut.y1, region.y)
                and eq(cut.y2, region.y + region.width)
                and cut.x1 >= region.x - tolerance
                and cut.x1 <= region.x + region.length + tolerance
            ]
            axis = "x"
        elif cut.direction == Direction.HORIZONTAL:
            if not eq(cut.y1, cut.y2) or cut.x2 <= cut.x1:
                raise ValueError(f"Cut {cut_number} is not a valid horizontal segment")
            candidates = [
                (i, region)
                for i, region in enumerate(regions)
                if eq(cut.x1, region.x)
                and eq(cut.x2, region.x + region.length)
                and cut.y1 >= region.y - tolerance
                and cut.y1 <= region.y + region.width + tolerance
            ]
            axis = "y"
        else:
            raise ValueError(f"Cut {cut_number} has an unknown direction")

        if len(candidates) != 1:
            raise ValueError(
                f"Cut {cut_number} does not span exactly one currently available "
                f"rectangle (found {len(candidates)}); cut order or geometry is invalid"
            )

        region_index, region = candidates[0]
        coordinate = float(cut.x1 if axis == "x" else cut.y1)
        start = region.x if axis == "x" else region.y
        extent = region.length if axis == "x" else region.width
        offset = coordinate - start

        # A line exactly on the far edge is redundant: no material remains
        # beyond it for a kerf. Strategies currently emit such edge cuts.
        if eq(offset, extent):
            continue
        if offset <= tolerance:
            raise ValueError(f"Cut {cut_number} starts at the near edge of its region")
        if offset + kerf > extent + tolerance:
            raise ValueError(f"Cut {cut_number} kerf extends beyond its available region")

        regions.pop(region_index)
        if axis == "x":
            left_length = offset
            right_x = coordinate + kerf
            right_length = region.x + region.length - right_x
            if left_length > tolerance:
                regions.append(_Region(region.x, region.y, left_length, region.width))
            if right_length > tolerance:
                regions.append(_Region(right_x, region.y, right_length, region.width))
        else:
            lower_width = offset
            upper_y = coordinate + kerf
            upper_width = region.y + region.width - upper_y
            if lower_width > tolerance:
                regions.append(_Region(region.x, region.y, region.length, lower_width))
            if upper_width > tolerance:
                regions.append(_Region(region.x, upper_y, region.length, upper_width))

    unmatched_regions = list(regions)
    for placement_number, placement in enumerate(layout.placements, start=1):
        if placement.length <= 0 or placement.width <= 0:
            raise ValueError(f"Placement {placement_number} has non-positive dimensions")
        matches = [
            i for i, region in enumerate(unmatched_regions)
            if eq(placement.x, region.x)
            and eq(placement.y, region.y)
            and eq(placement.length, region.length)
            and eq(placement.width, region.width)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Placement {placement_number} does not correspond to exactly one "
                "terminal rectangle produced by the ordered cuts"
            )
        unmatched_regions.pop(matches[0])

    return True
