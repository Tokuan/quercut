from typing import List
from .models import CutLayout, PlacedPart, Cut, Direction, CutConfig

def format_output(layouts: List[CutLayout], config: CutConfig) -> str:
    lines = []
    # Заголовок с параметрами
    lines.append(f"Kerf / Blade thickness\t{config.kerf}")
    if config.trim_left > 0:
        lines.append(f"Left trim\t{config.trim_left}")
    if config.trim_right > 0:
        lines.append(f"Right trim\t{config.trim_right}")
    if config.trim_top > 0:
        lines.append(f"Top trim\t{config.trim_top}")
    if config.trim_bottom > 0:
        lines.append(f"Bottom trim\t{config.trim_bottom}")
    lines.append("")

    # Статистика по листам
    lines.append("Required stocks")
    lines.append("Length\tWidth\tQuantity")
    stock_counts = {}
    for lay in layouts:
        key = (lay.stock_length, lay.stock_width)
        stock_counts[key] = stock_counts.get(key, 0) + lay.repetition
    for (l, w), cnt in stock_counts.items():
        lines.append(f"{l}\t{w}\t{cnt}")
    lines.append(f"Total\t\t{sum(stock_counts.values())}")
    lines.append("")
    lines.append("")
    lines.append("Cutting layouts")
    lines.append("")

    for layout in layouts:
        lines.append(f"Layout ID\tRepetition\tLength\tWidth")
        lines.append(f"{layout.layout_id}\t{layout.repetition}\t{layout.stock_length}\t{layout.stock_width}")

        # Детали
        lines.append("Panel length\tPanel width\tX\tY\tLabel")
        for pp in layout.placements:
            lines.append(f"{pp.length}\t{pp.width}\t{pp.x}\t{pp.y}\t{pp.part_label}")

        # Резы (визуализация)
        if layout.cuts:
            lines.append("Cuts")
            for cut in layout.cuts:
                dir_str = "H" if cut.direction == Direction.HORIZONTAL else "V"
                lines.append(f"{cut.x1}\t{cut.y1}\t{cut.x2}\t{cut.y2}\t{dir_str}")
        lines.append("")

    #lines.append("Created by www.opticutter.com")
    lines.append("")
    return "\n".join(lines)