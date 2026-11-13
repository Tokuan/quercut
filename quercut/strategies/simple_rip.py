# simple_rip.py

from typing import List
from .base import Strategy
from ..models import StockSheet, Part, CutConfig, CutLayout, Direction
from .guillotine_base import GuillotineBaseStrategy

class SimpleRipStrategy(Strategy, GuillotineBaseStrategy):
    """Первый рез — вдоль листа: полосы идут по ширине, детали внутри
    полосы отделяются вертикальными резами."""

    name = "Simple Rip (первый рез вдоль)"

    def layout(self, stocks: List[StockSheet],
               parts: List[Part],
               config: CutConfig) -> List[CutLayout]:
        return self._layout_sheets(
            stocks, parts, config,
            lambda usable_l, usable_w, batches, cfg: self._pack_single_sheet(
                usable_l, usable_w, batches, cfg.kerf, Direction.HORIZONTAL
            ),
        )
