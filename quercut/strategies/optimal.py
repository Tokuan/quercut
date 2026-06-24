# optimal.py

from typing import List
from .base import Strategy
from ..models import StockSheet, Part, PartBatch, CutLayout, CutConfig
from .guillotine_base import GuillotineBaseStrategy

class OptimalGuillotineStrategy(Strategy, GuillotineBaseStrategy):
    name = "Optimal Guillotine (выбор rip/cross)"

    def layout(self, stocks: List[StockSheet],
               parts: List[Part],
               config: CutConfig) -> List[CutLayout]:
        batches = [PartBatch(part=p, remaining=p.quantity) for p in parts]
        layouts = []
        layout_id_ord = ord('A')

        if not stocks:
            raise ValueError("Не задано ни одного типоразмера листа")

        # Находим шаблон для неограниченных листов
        unlimited_template = None
        for stock in stocks:
            if stock.is_unlimited:
                unlimited_template = stock
                break

        stock_queue = list(stocks)

        while any(b.remaining > 0 for b in batches):
            if not stock_queue:
                if unlimited_template is not None:
                    stock_queue.append(StockSheet(
                        unlimited_template.length,
                        unlimited_template.width,
                        unlimited_template.label,
                        is_unlimited=True
                    ))
                else:
                    break
            stock = stock_queue.pop(0)

            trim_left = config.trim_left
            trim_right = config.trim_right
            trim_top = config.trim_top
            trim_bottom = config.trim_bottom
            usable_l = stock.length - trim_left - trim_right
            usable_w = stock.width - trim_top - trim_bottom
            if usable_l <= 0 or usable_w <= 0:
                continue

            # Пробуем rip и cross, выбираем лучший
            best_placements = None
            best_cuts = None
            best_batches = None
            best_waste = float('inf')

            for strategy in ("rip", "cross"):
                temp_batches = [PartBatch(part=b.part, remaining=b.remaining) for b in batches]
                new_batches, placements, cuts = self._pack_single_sheet(
                    usable_l, usable_w, temp_batches, config.kerf, 0, strategy
                )
                if placements:
                    waste = usable_l * usable_w - sum(p.length * p.width for p in placements)
                    if waste < best_waste:
                        best_waste = waste
                        best_placements = placements
                        best_cuts = cuts
                        best_batches = new_batches

            if best_batches is None:
                continue

            # Сдвиг координат
            for p in best_placements:
                p.x += trim_left
                p.y += trim_bottom
            for c in best_cuts:
                c.x1 += trim_left
                c.y1 += trim_bottom
                c.x2 += trim_left
                c.y2 += trim_bottom

            for i, b in enumerate(batches):
                b.remaining = best_batches[i].remaining

            layouts.append(CutLayout(
                layout_id=chr(layout_id_ord),
                stock_length=stock.length,
                stock_width=stock.width,
                repetition=1,
                placements=best_placements,
                cuts=best_cuts
            ))
            layout_id_ord += 1

        # Сохраняем неразмещённые детали
        unplaced = []
        for b in batches:
            if b.remaining > 0:
                unplaced.append({
                    'label': b.part.label,
                    'length': b.part.length,
                    'width': b.part.width,
                    'remaining': b.remaining
                })
        self.unplaced_parts = unplaced

        return layouts