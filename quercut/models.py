from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto


class Direction(Enum):
    HORIZONTAL = auto()  # рез вдоль (параллельно длине листа)
    VERTICAL = auto()    # рез поперёк (параллельно ширине листа)


@dataclass(frozen=True)
class StockSheet:
    """Один лист-заготовка."""
    length: int
    width: int
    label: str = ""
    is_unlimited: bool = False  # True для целых листов, False для обрезков


@dataclass
class EdgeBand:
    """Кромка для стороны детали."""
    thickness: float = 0.0
    material: str = ""
    color: str = ""


@dataclass
class Part:
    """Деталь из заказа."""
    label: str = ""
    length: int = 0
    width: int = 0
    quantity: int = 0
    rotatable: bool = True   # можно ли повернуть на 90°
    global_index: int = 0
    # Кромки по сторонам (None = нет кромки)
    edge_length_top: Optional[EdgeBand] = None     # верхняя по длине
    edge_length_bottom: Optional[EdgeBand] = None  # нижняя по длине
    edge_width_left: Optional[EdgeBand] = None     # левая по ширине
    edge_width_right: Optional[EdgeBand] = None    # правая по ширине


@dataclass
class PartBatch:
    """Пул одинаковых деталей с оставшимся количеством."""
    part: Part
    remaining: int


@dataclass
class PlacedPart:
    """Одна уложенная деталь с координатами."""
    part_label: str
    x: int
    y: int
    length: int    # фактический размер по X
    width: int     # фактический размер по Y
    rotated: bool = False
    global_index: int = 0


@dataclass
class Cut:
    """Линия реза (гильотинного)."""
    x1: int
    y1: int
    x2: int
    y2: int
    direction: Direction


@dataclass
class CutTreeNode:
    """Узел дерева резов — для валидации и извлечения линий."""
    x: int
    y: int
    length: int
    width: int
    cut_type: Optional[Direction] = None
    kerf: int = 0
    left: Optional['CutTreeNode'] = None
    right: Optional['CutTreeNode'] = None
    part: Optional[PlacedPart] = None  # только для листьев

    def extract_cuts(self) -> List[Cut]:
        """Рекурсивно собирает все линии резов из дерева."""
        cuts = []
        if self.cut_type is not None and self.left and self.right:
            if self.cut_type == Direction.HORIZONTAL:
                # Горизонтальный рез: y = self.y + self.left.width (ширина левой части)
                y_cut = self.y + self.left.width + self.kerf // 2  # условно по центру пропила
                cuts.append(Cut(self.x, y_cut, self.x + self.length, y_cut, Direction.HORIZONTAL))
            else:  # VERTICAL
                x_cut = self.x + self.left.length + self.kerf // 2
                cuts.append(Cut(x_cut, self.y, x_cut, self.y + self.width, Direction.VERTICAL))
            cuts.extend(self.left.extract_cuts())
            cuts.extend(self.right.extract_cuts())
        return cuts


@dataclass
class CutLayout:
    """Раскладка одного листа (или обрезка, если используется)."""
    layout_id: str
    stock_length: int
    stock_width: int
    repetition: int = 1
    placements: List[PlacedPart] = field(default_factory=list)
    cuts: List[Cut] = field(default_factory=list)          # <-- добавлено
    # Опционально можно хранить дерево резов, но пока достаточно cuts
    cut_tree: Optional[CutTreeNode] = None


@dataclass(frozen=True)
class CutConfig:
    """Глобальные параметры раскроя."""
    kerf: int = 0
    trim_left: int = 0
    trim_right: int = 0
    trim_top: int = 0
    trim_bottom: int = 0
    min_remnant_area: int = 0