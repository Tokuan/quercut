# simple_cross.py

from typing import List
from .base import Strategy
from ..models import StockSheet, Part, CutConfig, CutLayout, Direction
from .guillotine_base import GuillotineBaseStrategy

class SimpleCrossStrategy(Strategy, GuillotineBaseStrategy):
    """Первый рез — поперёк листа: колонки идут по длине, детали внутри
    колонки отделяются горизонтальными резами."""

    name = "Simple Cross (первый рез поперёк)"

    def layout(self, stocks: List[StockSheet],
               parts: List[Part],
               config: CutConfig) -> List[CutLayout]:
        return self._layout_sheets(
            stocks, parts, config,
            lambda usable_l, usable_w, batches, cfg: self._pack_single_sheet(
                usable_l, usable_w, batches, cfg.kerf, Direction.VERTICAL
            ),
        )
