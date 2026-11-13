from typing import Callable, List, Optional, Tuple
from ..models import (
    StockSheet, Part, PartBatch, PlacedPart, Cut, CutConfig, CutLayout, Direction
)

class CutNode:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.used = False
        self.part = None
        self.right = None
        self.down = None
        self.vertical_cut = None
        self.horizontal_cut = None

class Sheet:
    def __init__(self, width, height, kerf, index):
        self.width = width
        self.height = height
        self.kerf = kerf
        self.index = index
        self.root = CutNode(0, 0, width, height)
        self.placed_parts: List[PlacedPart] = []

class GuillotineBaseStrategy:
    """Базовый класс гильотинных стратегий.

    Детали разворачиваются в экземпляры и сортируются от больших к меньшим:
    сначала по длине, затем по ширине. Заполнение рекурсивное: в текущий
    прямоугольник ставится самая большая помещающаяся деталь, а остаток
    распиливается на продолжение полосы (заполняется сразу же) и новый
    свободный прямоугольник.
    """

    @staticmethod
    def _has_valid_remainder(region_size: float, part_size: float, kerf: float) -> bool:
        """A part may leave either no remainder or material wider than the kerf."""
        remainder = region_size - part_size
        tolerance = 1e-9
        return remainder >= -tolerance and (
            abs(remainder) <= tolerance or remainder > kerf + tolerance
        )

    @staticmethod
    def _fits(node: CutNode, width: float, height: float, kerf: float) -> bool:
        if width > node.width or height > node.height:
            return False
        return (
            GuillotineBaseStrategy._has_valid_remainder(node.width, width, kerf)
            and GuillotineBaseStrategy._has_valid_remainder(node.height, height, kerf)
        )

    def _place_into(self, node: CutNode, pending: list, counts: List[int],
                    placements: List[PlacedPart], kerf: float,
                    first_cut: Direction):
        """Ставит самую большую помещающуюся деталь и рекурсивно заполняет остатки."""
        for i, item in enumerate(pending):
            if item is None:
                continue
            batch_idx, part = item
            width, height, rotated = part.length, part.width, False
            if not self._fits(node, width, height, kerf):
                if not part.rotatable or part.length == part.width:
                    continue
                width, height, rotated = part.width, part.length, True
                if not self._fits(node, width, height, kerf):
                    continue
            pending[i] = None
            counts[batch_idx] += 1
            self._split_node(node, part, width, height, rotated, kerf, first_cut)
            placements.append(
                PlacedPart(
                    part_label=part.label,
                    x=node.x,
                    y=node.y,
                    length=width,
                    width=height,
                    rotated=rotated,
                    global_index=part.global_index
                )
            )

            if first_cut == Direction.VERTICAL:
                # Первый рез поперёк отделяет колонку: сначала заполняем её
                # продолжение (node.down), затем новое пространство справа.
                if node.down:
                    self._place_into(node.down, pending, counts, placements, kerf, first_cut)
                if node.right:
                    self._place_into(node.right, pending, counts, placements, kerf, first_cut)
            else:
                # Первый рез вдоль отделяет полосу: сначала заполняем её
                # продолжение (node.right), затем новое пространство снизу.
                if node.right:
                    self._place_into(node.right, pending, counts, placements, kerf, first_cut)
                if node.down:
                    self._place_into(node.down, pending, counts, placements, kerf, first_cut)
            return

    def _split_node(self, node: CutNode, part: Part, width: int,
                    height: int, rotated: bool, kerf: float,
                    first_cut: Direction):
        """Разделяет узел резами в направлении первого реза."""
        node.used = True
        node.part = part
        k = kerf

        remaining_w = node.width - width
        remaining_h = node.height - height

        if first_cut == Direction.VERTICAL:
            # Первым идёт рез во всю высоту узла: правый остаток сохраняет
            # всю высоту, нижний остаток зажат в колонке шириной детали.
            if remaining_w > 0:
                node.vertical_cut = {
                    "type": "vertical",
                    "x": node.x + width,
                    "y1": node.y,
                    "y2": node.y + node.height
                }
                node.right = CutNode(
                    node.x + width + k,
                    node.y,
                    remaining_w - k,
                    node.height
                )
            if remaining_h > 0:
                node.horizontal_cut = {
                    "type": "horizontal",
                    "y": node.y + height,
                    "x1": node.x,
                    "x2": node.x + width
                }
                node.down = CutNode(
                    node.x,
                    node.y + height + k,
                    width,
                    remaining_h - k
                )
        else:
            # Первым идёт рез во всю ширину узла: нижний остаток сохраняет
            # всю ширину, правый остаток зажат в полосе высотой детали.
            if remaining_h > 0:
                node.horizontal_cut = {
                    "type": "horizontal",
                    "y": node.y + height,
                    "x1": node.x,
                    "x2": node.x + node.width
                }
                node.down = CutNode(
                    node.x,
                    node.y + height + k,
                    node.width,
                    remaining_h - k
                )
            if remaining_w > 0:
                node.vertical_cut = {
                    "type": "vertical",
                    "x": node.x + width,
                    "y1": node.y,
                    "y2": node.y + height
                }
                node.right = CutNode(
                    node.x + width + k,
                    node.y,
                    remaining_w - k,
                    height
                )

    def _extract_cuts(self, node: Optional[CutNode], cuts_list: List[Cut],
                      first_cut: Direction):
        """Извлекает резы в порядке, допустимом для их физического выполнения."""
        if not node:
            return

        ordered_cuts = (
            (node.vertical_cut, node.horizontal_cut)
            if first_cut == Direction.VERTICAL
            else (node.horizontal_cut, node.vertical_cut)
        )

        for cut in ordered_cuts:
            if not cut:
                continue
            if cut["type"] == "vertical":
                cuts_list.append(Cut(
                    x1=cut["x"],
                    y1=cut["y1"],
                    x2=cut["x"],
                    y2=cut["y2"],
                    direction=Direction.VERTICAL
                ))
            else:
                cuts_list.append(Cut(
                    x1=cut["x1"],
                    y1=cut["y"],
                    x2=cut["x2"],
                    y2=cut["y"],
                    direction=Direction.HORIZONTAL
                ))

        # Оба реза текущего узла должны быть выполнены до резов в его
        # дочерних областях. Порядок обхода этих областей не влияет на
        # доступность резов: они уже отделены родительскими резами.
        self._extract_cuts(node.right, cuts_list, first_cut)
        self._extract_cuts(node.down, cuts_list, first_cut)

    def _pack_single_sheet(self, sheet_w: int, sheet_h: int,
                           batches: List[PartBatch], kerf: float,
                           first_cut: Direction):
        """Упаковывает один лист, возвращает обновлённые партии, placements, cuts."""
        # Разворачиваем партии в экземпляры: сначала по длине, затем по ширине.
        pending = []
        for batch_idx, b in enumerate(batches):
            for _ in range(b.remaining):
                pending.append((batch_idx, b.part))
        pending.sort(key=lambda item: (-item[1].length, -item[1].width))

        counts = [0] * len(batches)
        sheet = Sheet(sheet_w, sheet_h, kerf, 0)
        placements: List[PlacedPart] = []
        self._place_into(sheet.root, pending, counts, placements, kerf, first_cut)

        if not placements:
            return batches, [], []

        cuts: List[Cut] = []
        self._extract_cuts(sheet.root, cuts, first_cut)

        new_batches = [
            PartBatch(part=b.part, remaining=b.remaining - counts[i])
            for i, b in enumerate(batches)
        ]
        return new_batches, placements, cuts

    def _layout_sheets(self, stocks: List[StockSheet], parts: List[Part],
                       config: CutConfig,
                       pack_one: Callable[[int, int, List[PartBatch], CutConfig], tuple]):
        """Общий цикл раскроя по листам.

        pack_one(usable_l, usable_w, batches, config) возвращает кортеж
        (new_batches, placements, cuts) для одного листа.
        """
        batches = [PartBatch(part=p, remaining=p.quantity) for p in parts]
        layouts = []
        layout_id_ord = 1

        if not stocks:
            raise ValueError("Не задано ни одного типоразмера листа")

        unlimited_types = [s for s in stocks if s.is_unlimited]
        stock_queue = list(stocks)
        replenished = False
        round_placed_any = False

        while any(b.remaining > 0 for b in batches):
            if not stock_queue:
                if not unlimited_types:
                    break
                if replenished and not round_placed_any:
                    # Полный круг неограниченных листов не разместил ни одной
                    # детали — дальше циклиться бессмысленно.
                    break
                stock_queue = [
                    StockSheet(t.length, t.width, t.label, is_unlimited=True)
                    for t in unlimited_types
                ]
                replenished = True
                round_placed_any = False

            stock = stock_queue.pop(0)

            usable_l = stock.length - config.trim_left - config.trim_right
            usable_w = stock.width - config.trim_top - config.trim_bottom
            if usable_l <= 0 or usable_w <= 0:
                continue

            new_batches, placements, cuts = pack_one(usable_l, usable_w, batches, config)
            if not placements:
                continue
            round_placed_any = True

            # Сдвигаем координаты на отступы
            for p in placements:
                p.x += config.trim_left
                p.y += config.trim_bottom
            for c in cuts:
                c.x1 += config.trim_left
                c.y1 += config.trim_bottom
                c.x2 += config.trim_left
                c.y2 += config.trim_bottom

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

        # Сохраняем неразмещённые детали
        self.unplaced_parts = [
            {
                'label': b.part.label,
                'length': b.part.length,
                'width': b.part.width,
                'remaining': b.remaining
            }
            for b in batches if b.remaining > 0
        ]

        return layouts
