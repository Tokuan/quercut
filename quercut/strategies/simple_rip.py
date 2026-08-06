# simple_rip.py

from typing import List
from .base import Strategy
from ..models import StockSheet, Part, PartBatch, CutLayout, CutConfig
from .guillotine_base import GuillotineBaseStrategy

class SimpleRipStrategy(Strategy, GuillotineBaseStrategy):
    name = "Simple Rip (первый рез вдоль)"

    def layout(self, stocks: List[StockSheet],
               parts: List[Part],
               config: CutConfig) -> List[CutLayout]:
        batches = [PartBatch(part=p, remaining=p.quantity) for p in parts]
        layouts = []
        layout_id_ord = 1

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

            new_batches, placements, cuts = self._pack_single_sheet(
                usable_l, usable_w, batches, config.kerf, 0, strategy="rip"
            )
            if placements:
                # Сдвигаем координаты на отступы
                for p in placements:
                    p.x += trim_left
                    p.y += trim_bottom
                for c in cuts:
                    c.x1 += trim_left
                    c.y1 += trim_bottom
                    c.x2 += trim_left
                    c.y2 += trim_bottom

                for i, b in enumerate(batches):
                    b.remaining = new_batches[i].remaining
                layouts.append(CutLayout(
                    layout_id=layout_id_ord,
                    stock_length=stock.length,
                    stock_width=stock.width,
                    repetition=1,
                    placements=placements,
                    cuts=cuts
                ))
                layout_id_ord += 1
            else:
                continue

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