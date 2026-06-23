from abc import ABC, abstractmethod
from typing import List
from ..models import StockSheet, Part, CutConfig, CutLayout

class Strategy(ABC):
    name: str = "Base"

    @abstractmethod
    def layout(self,
               stocks: List[StockSheet],
               parts: List[Part],
               config: CutConfig) -> List[CutLayout]:
        """Возвращает список использованных листов с размещёнными деталями.
        Стратегия может модифицировать переданный список parts (уменьшать quantity).
        """
        ...