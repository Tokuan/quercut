"""
Генератор SVG для визуализации раскроя.
Принимает список CutLayout и глобальные параметры (kerf, trim_margin).
Рисует лист с областью подрезки, размещённые детали и линии резов.
"""

from typing import List
from .models import CutLayout, PlacedPart, Cut, Direction, CutConfig
import math

def generate_svg(layouts: List[CutLayout], config: CutConfig, max_width=1200) -> str:
    """
    Возвращает строку с SVG-кодом, где каждый Layout представлен отдельной панелью.
    Панели располагаются горизонтально, переносятся на новую строку при нехватке ширины.
    """
    margin = 20  # отступ между листами на рисунке
    # Собираем все SVG-фрагменты
    svg_panels = []
    for layout in layouts:
        svg_panels.append(_render_layout(layout, config))

    # Группируем панели в сетку
    panel_width = max(l.stock_length for l in layouts) + 2 * margin
    panel_height = max(l.stock_width for l in layouts) + 2 * margin
    cols = max(1, (max_width - margin) // (panel_width + margin))
    rows = math.ceil(len(svg_panels) / cols)
    total_width = cols * (panel_width + margin) + margin
    total_height = rows * (panel_height + margin) + margin

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {total_height}" width="{min(total_width, max_width)}">']
    svg.append(f'<rect width="{total_width}" height="{total_height}" fill="white"/>')

    for i, panel in enumerate(svg_panels):
        col = i % cols
        row = i // cols
        x = margin + col * (panel_width + margin)
        y = margin + row * (panel_height + margin)
        # Оборачиваем панель в группу с трансляцией
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
    usable_l = stock_l - trim_l - trim_r
    usable_w = stock_w - trim_t - trim_b

    lines = []
    # Фон листа
    lines.append(
        f'<rect x="0" y="0" width="{stock_l}" height="{stock_w}" fill="#f0f0f0" stroke="black" stroke-width="2"/>')

    # Область подрезки (рамка)
    if trim_l > 0 or trim_r > 0 or trim_t > 0 or trim_b > 0:
        lines.append(
            f'<rect x="{trim_l}" y="{trim_b}" width="{usable_l}" height="{usable_w}" fill="#ffffff" stroke="gray" stroke-width="1" stroke-dasharray="5,5"/>')
    # Детали
    colors = ['#cce5ff', '#d4edda', '#fff3cd', '#f8d7da', '#e2d8f0', '#cff4fc', '#f9e2af', '#e0e0e0']
    for i, pp in enumerate(layout.placements):
        color = colors[i % len(colors)]
        x, y, w, h = pp.x, pp.y, pp.length, pp.width
        lines.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" stroke="black" stroke-width="1"/>')
        label = pp.part_label[:8] if pp.part_label else ""
        lines.append(f'<text x="{x+2}" y="{y+12}" font-size="36" font-family="monospace">{label}</text>')
        if w > 20 and h > 15:
            lines.append(f'<text x="{x+w/2}" y="{y+h-3}" font-size="24" font-family="monospace" text-anchor="middle">{pp.length}x{pp.width}</text>')
    # Резы
    for cut in layout.cuts:
        x1, y1, x2, y2 = cut.x1, cut.y1, cut.x2, cut.y2
        lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="red" stroke-width="2" opacity="0.7"/>')
    lines.append(f'<text x="5" y="{stock_w - 5}" font-size="36" font-family="sans-serif" fill="black">{layout.layout_id}</text>')
    return '\n'.join(lines)