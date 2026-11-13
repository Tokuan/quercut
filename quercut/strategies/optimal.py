# optimal.py

from typing import List
from .base import Strategy
from ..models import StockSheet, Part, PartBatch, CutConfig, CutLayout, Direction
from .guillotine_base import GuillotineBaseStrategy

class OptimalGuillotineStrategy(Strategy, GuillotineBaseStrategy):
    """Для каждого листа пробует оба направления первого реза
    и оставляет вариант с меньшим остатком."""

    name = "Optimal Guillotine (выбор направления первого реза)"

    def layout(self, stocks: List[StockSheet],
               parts: List[Part],
               config: CutConfig) -> List[CutLayout]:
        def pack_one(usable_l, usable_w, batches, cfg):
            best = None
            for first_cut in (Direction.VERTICAL, Direction.HORIZONTAL):
                temp_batches = [PartBatch(part=b.part, remaining=b.remaining) for b in batches]
                new_batches, placements, cuts = self._pack_single_sheet(
                    usable_l, usable_w, temp_batches, cfg.kerf, first_cut
                )
                if placements:
                    waste = usable_l * usable_w - sum(p.length * p.width for p in placements)
                    if best is None or waste < best[0]:
                        best = (waste, new_batches, placements, cuts)

            if best is None:
                return batches, [], []
            return best[1], best[2], best[3]

        return self._layout_sheets(stocks, parts, config, pack_one)
