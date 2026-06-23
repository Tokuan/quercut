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


def generate_svg(layouts: List[CutLayout], config: CutConfig, max_width=1200) -> str:
    margin = 20
    svg_panels = []
    for layout in layouts:
        svg_panels.append(_render_layout(layout, config))

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
    svg.append('.dim { font-family: "Ubuntu Mono", monospace; font-size: 28px; fill: #333; }')
    svg.append('.dim-large { font-family: "Ubuntu Mono", monospace; font-size: 36px; fill: #000; font-weight: bold; }')
    svg.append('.dim-small { font-family: "Ubuntu Mono", monospace; font-size: 24px; fill: #666; }')
    svg.append('.pos-num { font-family: "Ubuntu Mono", monospace; font-size: 48px; fill: #000; font-weight: bold; }')
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


def _render_layout(layout: CutLayout, config: CutConfig) -> str:
    stock_l = layout.stock_length
    stock_w = layout.stock_width
    trim_l = config.trim_left
    trim_r = config.trim_right
    trim_t = config.trim_top
    trim_b = config.trim_bottom

    lines = []
    # Фон листа
    lines.append(
        f'<rect x="0" y="0" width="{stock_l}" height="{stock_w}" fill="#f8f9fa" stroke="#333" stroke-width="2"/>')

    # Область подрезки
    if trim_l > 0 or trim_r > 0 or trim_t > 0 or trim_b > 0:
        usable_l = stock_l - trim_l - trim_r
        usable_w = stock_w - trim_t - trim_b
        lines.append(
            f'<rect x="{trim_l}" y="{trim_b}" width="{usable_l}" height="{usable_w}" fill="#ffffff" stroke="#999" stroke-width="1" stroke-dasharray="8,4"/>')
        # Подписи отступов
        if trim_l > 0:
            lines.append(
                f'<text x="{trim_l / 2}" y="{stock_w / 2}" class="dim-small" text-anchor="middle" transform="rotate(-90,{trim_l / 2},{stock_w / 2})">LT {trim_l}</text>')
        if trim_r > 0:
            rx = stock_l - trim_r / 2
            lines.append(
                f'<text x="{rx}" y="{stock_w / 2}" class="dim-small" text-anchor="middle" transform="rotate(90,{rx},{stock_w / 2})">RT {trim_r}</text>')
        if trim_b > 0:
            lines.append(
                f'<text x="{stock_l / 2}" y="{trim_b / 2}" class="dim-small" text-anchor="middle">BT {trim_b}</text>')
        if trim_t > 0:
            ty = stock_w - trim_t / 2
            lines.append(f'<text x="{stock_l / 2}" y="{ty}" class="dim-small" text-anchor="middle">TT {trim_t}</text>')

    # Цвета для деталей
    colors = [
        '#e3f2fd', '#e8f5e9', '#fff8e1', '#fce4ec', '#f3e5f5',
        '#e0f7fa', '#fff3e0', '#e8eaf6', '#f1f8e9', '#fbe9e7'
    ]

    # Строим карту занятости для обрезков
    occupied = _build_occupied_grid(layout, config)

    # Рисуем детали
    for i, pp in enumerate(layout.placements):
        color = colors[i % len(colors)]
        x, y, w, h = pp.x, pp.y, pp.length, pp.width

        # Прямоугольник детали
        lines.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" stroke="#555" stroke-width="1.5" rx="2"/>')

        # Номер позиции (в правом нижнем углу, в кружочке)
        circle_r = 36
        cx = x + w - (circle_r+4)
        cy = y + h - (circle_r+4)
        lines.append(f'<circle cx="{cx}" cy="{cy}" r="{circle_r}" fill="#ffffff" opacity="0.9"/>')
        idx = pp.global_index + 1
        lines.append(
            f'<text x="{cx}" y="{cy + 2}" class="pos-num" fill="white" text-anchor="middle" dominant-baseline="central">{idx}</text>')

        # Размеры вдоль сторон
        if w >= h:
            if w > 50:
                lines.append(f'<text x="{x + w / 2}" y="{y + 36}" class="dim-large" text-anchor="middle">{w}</text>')
            if h > 40:
                lines.append(
                    f'<text x="{x + 26}" y="{y + h / 2}" class="dim-large" text-anchor="middle" transform="rotate(-90,{x + 36},{y + h / 2})">{h}</text>')
        else:
            if w > 40:
                lines.append(f'<text x="{x + w / 2}" y="{y + 36}" class="dim-large" text-anchor="middle">{w}</text>')
            if h > 50:
                lines.append(
                    f'<text x="{x + 36}" y="{y + h / 2}" class="dim-large" text-anchor="middle" transform="rotate(-90,{x + 36},{y + h / 2})">{h}</text>')

        # Иконка поворота, если деталь была повёрнута
        if pp.rotated:
            icon_size = 64
            icon_x = x + icon_size / 2 + 4
            icon_y = y + icon_size / 2 + 4
            lines.append(
                f'<use href="#rotate-icon" x="{icon_x - icon_size / 2}" y="{icon_y - icon_size / 2}" width="{icon_size}" height="{icon_size}"/>')

    # Рисуем резы и подписываем обрезные части
    for cut in layout.cuts:
        x1, y1, x2, y2 = cut.x1, cut.y1, cut.x2, cut.y2
        lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#d32f2f" stroke-width="1.5" opacity="0.6"/>')

        # Вычисляем длину обрезной части
        if cut.direction == Direction.VERTICAL:
            free_segments = _find_free_segments_along_cut(x1, y1, x2, y2, occupied, axis='y')
        else:
            free_segments = _find_free_segments_along_cut(x1, y1, x2, y2, occupied, axis='x')

        # Подписываем каждый свободный сегмент
        for seg in free_segments:
            seg_length = seg['end'] - seg['start']
            if seg_length >= 15:
                if cut.direction == Direction.VERTICAL:
                    mid_y = (seg['start'] + seg['end']) / 2
                    lines.append(
                        f'<text x="{x1 - 8}" y="{mid_y}" class="dim-small" fill="#c62828" text-anchor="end" transform="rotate(-90,{x1 - 8},{mid_y})">{seg_length}</text>')
                else:
                    mid_x = (seg['start'] + seg['end']) / 2
                    lines.append(
                        f'<text x="{mid_x}" y="{y1 - 8}" class="dim-small" fill="#c62828" text-anchor="middle">{seg_length}</text>')

    # Подпись Layout ID
    lines.append(
        f'<text x="{stock_l - 10}" y="{stock_w - 10}" class="dim-large" text-anchor="end" font-weight="bold">{layout.layout_id}</text>')

    return '\n'.join(lines)


def _build_occupied_grid(layout: CutLayout, config: CutConfig):
    stock_l = layout.stock_length
    stock_w = layout.stock_width
    grid = [[False] * stock_w for _ in range(stock_l)]

    for pp in layout.placements:
        x1 = max(0, pp.x)
        y1 = max(0, pp.y)
        x2 = min(stock_l, pp.x + pp.length)
        y2 = min(stock_w, pp.y + pp.width)
        for i in range(x1, x2):
            for j in range(y1, y2):
                grid[i][j] = True
    return grid


def _find_free_segments_along_cut(x1, y1, x2, y2, occupied, axis='y'):
    segments = []
    in_free = False
    start = None

    if axis == 'y':
        y_min = min(y1, y2)
        y_max = max(y1, y2)
        x = x1
        for y in range(y_min, y_max):
            left_occupied = (x > 0 and occupied[x - 1][y]) if x > 0 else True
            right_occupied = (x < len(occupied) - 1 and occupied[x + 1][y]) if x < len(occupied) - 1 else True

            is_free_segment = not left_occupied and not right_occupied

            if is_free_segment and not in_free:
                in_free = True
                start = y
            elif not is_free_segment and in_free:
                in_free = False
                if start is not None and y - start >= 5:
                    segments.append({'start': start, 'end': y})
        if in_free and start is not None and y_max - start >= 5:
            segments.append({'start': start, 'end': y_max})
    else:
        x_min = min(x1, x2)
        x_max = max(x1, x2)
        y = y1
        for x in range(x_min, x_max):
            bottom_occupied = (y > 0 and occupied[x][y - 1]) if y > 0 else True
            top_occupied = (y < len(occupied[0]) - 1 and occupied[x][y + 1]) if y < len(occupied[0]) - 1 else True

            is_free_segment = not bottom_occupied and not top_occupied

            if is_free_segment and not in_free:
                in_free = True
                start = x
            elif not is_free_segment and in_free:
                in_free = False
                if start is not None and x - start >= 5:
                    segments.append({'start': start, 'end': x})
        if in_free and start is not None and x_max - start >= 5:
            segments.append({'start': start, 'end': x_max})

    return segments