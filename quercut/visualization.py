from typing import List
from .models import CutLayout, PlacedPart, Cut, Direction, CutConfig
import math

# Иконка поворота (встроенная SVG)
ROTATE_ICON = """
<g id="rotate-icon" fill="none" stroke="#1565c0" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<polyline points="10.684 1.426 15.13 5.931 10.265 8.718" style="transform-box: fill-box; 
transform-origin: 50% 50%;" transform="matrix(0.999229, 0.039251, -0.039251, 0.999229, -0.000121, 0.006163)"/>
<polyline points="14.444 24.064 8.853 20.111 14.067 15.713"/><path d="M 14.456 5.739 C 7.881 4.362 4.13 8.43 4.248 12.099" style=""/>
<path d="M 9.378 19.967 C 14.131 20.558 18.479 15.643 18.361 11.901"/></g>
"""


def generate_svg(layouts: List[CutLayout], config: CutConfig, max_width=1200, monochrome: bool = False) -> str:
    margin = 20
    if not layouts:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1" width="1"></svg>'
    svg_panels = []
    for layout in layouts:
        svg_panels.append(_render_layout(layout, config, monochrome))

    # Компоновка листов
    panel_width = max(l.stock_length for l in layouts) + 2 * margin
    panel_height = max(l.stock_width for l in layouts) + 2 * margin
    cols = max(1, (max_width - margin) // (panel_width + margin))
    rows = math.ceil(len(svg_panels) / cols)
    total_width = cols * (panel_width + margin) + margin
    total_height = rows * (panel_height + margin) + margin

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {total_height}" width="{min(total_width, max_width)}">']
    svg.append(f'<rect width="{total_width}" height="{total_height}" fill="white"/>')
    svg.append('<style>')
    svg.append('.dim { font-family: "Ubuntu Mono", monospace; font-size: 36px; fill: #333; }')
    svg.append('.dim-large { font-family: "Ubuntu Mono", monospace; font-size: 48px; fill: #000; font-weight: bold; }')
    svg.append('.dim-small { font-family: "Ubuntu Mono", monospace; font-size: 36px; fill: #666; }')
    svg.append('.pos-num { font-family: "Ubuntu Mono", monospace; font-size: 64px; fill: #000; font-weight: bold; }')
    svg.append('</style>')

    # Добавляем иконку поворота в defs
    svg.append('<defs>')
    svg.append(ROTATE_ICON)
    svg.append('</defs>')

    for i, panel in enumerate(svg_panels):
        col = i % cols
        row = i // cols
        x = margin + col * (panel_width + margin)
        y = margin + row * (panel_height + margin)
        svg.append(f'<g transform="translate({x},{y})">')
        svg.append(panel)
        svg.append('</g>')

    svg.append('</svg>')
    return '\n'.join(svg)


def _render_layout(layout: CutLayout, config: CutConfig, monochrome: bool = False) -> str:
    stock_l = layout.stock_length
    stock_w = layout.stock_width
    trim_l = config.trim_left
    trim_r = config.trim_right
    trim_t = config.trim_top
    trim_b = config.trim_bottom
    kerf = float(config.kerf)

    if monochrome:
        colors = [
            '#ffffff', '#f0f0f0', '#e5e5e5', '#d9d9d9', '#cccccc',
            '#bfbfbf', '#a6a6a6', '#999999', '#8c8c8c'
        ]
        bg_color = "#ffffff"
        stock_stroke = "#000000"
        trim_color = "#000000"
        rect_stroke = "#000000"
        cut_stroke = "#000000"
        cut_opacity = "1"
        text_fill = "#000000"
        circle_fill = "#ffffff"
        circle_text = "#000000"
        icon_color = "#000000"
        kerf_fill = "#000000"
        kerf_opacity = "0.18"
    else:
        colors = [
            '#e3f2fd', '#e8f5e9', '#fff8e1', '#fce4ec', '#f3e5f5',
            '#e0f7fa', '#fff3e0', '#e8eaf6', '#f1f8e9', '#fbe9e7'
        ]
        bg_color = "#f8f9fa"
        stock_stroke = "#333"
        trim_color = "#999"
        rect_stroke = "#555"
        cut_stroke = "#d32f2f"
        cut_opacity = "0.8"
        text_fill = "#333"
        circle_fill = "#ffffff"
        circle_text = "#000000"
        icon_color = "#1565c0"
        kerf_fill = "#d32f2f"
        kerf_opacity = "0.18"

    lines = [
        f'<rect x="0" y="0" width="{stock_l}" height="{stock_w}" '
        f'fill="{bg_color}" stroke="{stock_stroke}" stroke-width="2"/>'
    ]

    # SVG's Y axis points down, while layout coordinates are measured upward
    # from the lower-left corner of the stock.
    if trim_l > 0 or trim_r > 0 or trim_t > 0 or trim_b > 0:
        usable_l = stock_l - trim_l - trim_r
        usable_w = stock_w - trim_t - trim_b
        lines.append(
            f'<rect x="{trim_l}" y="{trim_t}" width="{usable_l}" height="{usable_w}" '
            f'fill="#ffffff" stroke="{trim_color}" stroke-width="1" stroke-dasharray="8,4"/>'
        )
        if trim_l > 0:
            lines.append(
                f'<text x="{trim_l / 2}" y="{stock_w / 2}" class="dim-small" '
                f'text-anchor="middle" transform="rotate(-90,{trim_l / 2},{stock_w / 2})">LT {trim_l}</text>'
            )
        if trim_r > 0:
            rx = stock_l - trim_r / 2
            lines.append(
                f'<text x="{rx}" y="{stock_w / 2}" class="dim-small" '
                f'text-anchor="middle" transform="rotate(90,{rx},{stock_w / 2})">RT {trim_r}</text>'
            )
        if trim_t > 0:
            lines.append(
                f'<text x="{stock_l / 2}" y="{trim_t / 2}" class="dim-small" '
                f'text-anchor="middle">TT {trim_t}</text>'
            )
        if trim_b > 0:
            by = stock_w - trim_b / 2
            lines.append(
                f'<text x="{stock_l / 2}" y="{by}" class="dim-small" '
                f'text-anchor="middle">BT {trim_b}</text>'
            )

    lines.append('<defs>')
    lines.append(ROTATE_ICON.replace('#1565c0', icon_color))
    lines.append('</defs>')

    # Draw placed parts using the same lower-left coordinate convention as
    # the cutting strategies, converted to SVG's top-left coordinate system.
    for pp in layout.placements:
        color = colors[pp.global_index % len(colors)]
        x, y, w, h = pp.x, pp.y, pp.length, pp.width
        svg_y = stock_w - (y + h)

        lines.append(
            f'<rect x="{x}" y="{svg_y}" width="{w}" height="{h}" '
            f'fill="{color}" stroke="{rect_stroke}" stroke-width="1.5" rx="2"/>'
        )

        circle_r = 54
        cx = x + w - (circle_r + 16)
        cy = svg_y + h - (circle_r + 16)
        lines.append(f'<circle cx="{cx}" cy="{cy}" r="{circle_r}" fill="{circle_fill}" opacity="0.6"/>')
        lines.append(
            f'<text x="{cx}" y="{cy + 2}" class="pos-num" fill="{circle_text}" '
            f'text-anchor="middle" dominant-baseline="central">{pp.global_index + 1}</text>'
        )

        if w >= h:
            if w > 50:
                lines.append(
                    f'<text x="{x + w / 2}" y="{svg_y + 36}" class="dim-large" '
                    f'fill="{text_fill}" text-anchor="middle">{w}</text>'
                )
            if h > 40:
                tx, ty = x + 36, svg_y + h / 2
                lines.append(
                    f'<text x="{tx}" y="{ty}" class="dim-large" fill="{text_fill}" '
                    f'text-anchor="middle" transform="rotate(-90,{tx},{ty})">{h}</text>'
                )
        else:
            if w > 40:
                lines.append(
                    f'<text x="{x + w / 2}" y="{svg_y + 36}" class="dim-large" '
                    f'fill="{text_fill}" text-anchor="middle">{w}</text>'
                )
            if h > 50:
                tx, ty = x + 36, svg_y + h / 2
                lines.append(
                    f'<text x="{tx}" y="{ty}" class="dim-large" fill="{text_fill}" '
                    f'text-anchor="middle" transform="rotate(-90,{tx},{ty})">{h}</text>'
                )

        if pp.rotated:
            icon_size = 24
            icon_x = x + 4
            icon_y = svg_y + 4
            lines.append(
                f'<use href="#rotate-icon" x="{icon_x}" y="{icon_y}" '
                f'width="{icon_size}" height="{icon_size}"/>'
            )

    # A cut coordinate is the near edge of the kerf. Show the actual kerf
    # band in the positive axis direction, then draw its near-edge reference.
    for cut in layout.cuts:
        if cut.direction == Direction.VERTICAL:
            x = cut.x1
            y_top = stock_w - cut.y2
            cut_length = cut.y2 - cut.y1
            if kerf > 0:
                lines.append(
                    f'<rect x="{x}" y="{y_top}" width="{kerf}" height="{cut_length}" '
                    f'fill="{kerf_fill}" opacity="{kerf_opacity}"/>'
                )
            lines.append(
                f'<line x1="{x}" y1="{y_top}" x2="{x}" y2="{stock_w - cut.y1}" '
                f'stroke="{cut_stroke}" stroke-width="1.5" opacity="{cut_opacity}"/>'
            )
            free_segments = _find_free_segments_along_cut(
                cut, layout.placements, kerf
            )
            for seg in free_segments:
                seg_length = seg['end'] - seg['start']
                if seg_length >= 15:
                    mid_y = stock_w - (seg['start'] + seg['end']) / 2
                    tx = x - 8
                    lines.append(
                        f'<text x="{tx}" y="{mid_y}" class="dim-small" fill="{text_fill}" '
                        f'text-anchor="end" transform="rotate(-90,{tx},{mid_y})">{seg_length}</text>'
                    )
        else:
            y = cut.y1
            svg_y = stock_w - y
            if kerf > 0:
                lines.append(
                    f'<rect x="{cut.x1}" y="{svg_y - kerf}" width="{cut.x2 - cut.x1}" '
                    f'height="{kerf}" fill="{kerf_fill}" opacity="{kerf_opacity}"/>'
                )
            lines.append(
                f'<line x1="{cut.x1}" y1="{svg_y}" x2="{cut.x2}" y2="{svg_y}" '
                f'stroke="{cut_stroke}" stroke-width="1.5" opacity="{cut_opacity}"/>'
            )
            free_segments = _find_free_segments_along_cut(
                cut, layout.placements, kerf
            )
            for seg in free_segments:
                seg_length = seg['end'] - seg['start']
                if seg_length >= 15:
                    mid_x = (seg['start'] + seg['end']) / 2
                    lines.append(
                        f'<text x="{mid_x}" y="{svg_y - 8}" class="dim-small" '
                        f'fill="{text_fill}" text-anchor="middle">{seg_length}</text>'
                    )

    lines.append(
        f'<text x="{stock_l - 10}" y="{stock_w - 10}" class="dim-large" '
        f'fill="{text_fill}" text-anchor="end" font-weight="bold">{layout.layout_id}</text>'
    )
    return '\n'.join(lines)


def _find_free_segments_along_cut(cut: Cut, placements: List[PlacedPart], kerf: float):
    """Return intervals along a cut with no part touching either side.

    The calculation is continuous: it uses placement boundaries and the
    actual kerf width, so fractional coordinates do not require a pixel/mm grid.
    """
    tolerance = 1e-9
    if cut.direction == Direction.VERTICAL:
        axis_start, axis_end = sorted((cut.y1, cut.y2))
        cut_coordinate = cut.x1
        near_intervals = []
        far_coordinate = cut_coordinate + kerf
        for part in placements:
            part_start = part.y
            part_end = part.y + part.width
            if part.x < cut_coordinate + tolerance and part.x + part.length >= cut_coordinate - tolerance:
                near_intervals.append((part_start, part_end))
            if part.x <= far_coordinate + tolerance and part.x + part.length > far_coordinate - tolerance:
                near_intervals.append((part_start, part_end))
    else:
        axis_start, axis_end = sorted((cut.x1, cut.x2))
        cut_coordinate = cut.y1
        near_intervals = []
        far_coordinate = cut_coordinate + kerf
        for part in placements:
            part_start = part.x
            part_end = part.x + part.length
            if part.y < cut_coordinate + tolerance and part.y + part.width >= cut_coordinate - tolerance:
                near_intervals.append((part_start, part_end))
            if part.y <= far_coordinate + tolerance and part.y + part.width > far_coordinate - tolerance:
                near_intervals.append((part_start, part_end))

    clipped = sorted(
        (max(axis_start, start), min(axis_end, end))
        for start, end in near_intervals
        if min(axis_end, end) - max(axis_start, start) > tolerance
    )

    merged = []
    for start, end in clipped:
        if not merged or start > merged[-1][1] + tolerance:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    free_segments = []
    cursor = axis_start
    for start, end in merged:
        if start - cursor > tolerance:
            free_segments.append({'start': cursor, 'end': start})
        cursor = max(cursor, end)
    if axis_end - cursor > tolerance:
        free_segments.append({'start': cursor, 'end': axis_end})
    return free_segments
