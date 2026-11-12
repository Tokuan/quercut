from typing import List, Optional, Tuple
from ..models import Part, PartBatch, PlacedPart, Cut, Direction

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
    """Базовый класс для стратегий гильотинного раскроя на основе CutNode."""

    @staticmethod
    def _has_valid_remainder(region_size: float, part_size: float, kerf: float) -> bool:
        """A part may leave either no remainder or material wider than the kerf."""
        remainder = region_size - part_size
        tolerance = 1e-9
        return remainder >= -tolerance and (
            abs(remainder) <= tolerance or remainder > kerf + tolerance
        )

    def _calculate_score(self, node: CutNode, part_w: int, part_h: int) -> float:
        waste_area = (node.width * node.height) - (part_w * part_h)
        remaining_w = node.width - part_w
        remaining_h = node.height - part_h

        penalty = 0
        MIN_USEFUL_SIZE = 300
        if 0 < remaining_w < MIN_USEFUL_SIZE:
            penalty += 200000
        if 0 < remaining_h < MIN_USEFUL_SIZE:
            penalty += 200000
        return waste_area + penalty

    def _find_best_node(self, sheet: Sheet, part: Part) -> Tuple[Optional[CutNode], Optional[int], Optional[int], bool]:
        free_nodes = self._collect_free_nodes(sheet.root)
        best_node = None
        best_score = None
        best_rotation = False
        best_w = None
        best_h = None

        for node in free_nodes:
            # Без поворота
            if (
                part.length <= node.width
                and part.width <= node.height
                and self._has_valid_remainder(node.width, part.length, sheet.kerf)
                and self._has_valid_remainder(node.height, part.width, sheet.kerf)
            ):
                score = self._calculate_score(node, part.length, part.width)
                if best_score is None or score < best_score:
                    best_score = score
                    best_node = node
                    best_rotation = False
                    best_w = part.length
                    best_h = part.width
            # С поворотом
            if part.rotatable and part.length != part.width:
                if (
                    part.width <= node.width
                    and part.length <= node.height
                    and self._has_valid_remainder(node.width, part.width, sheet.kerf)
                    and self._has_valid_remainder(node.height, part.length, sheet.kerf)
                ):
                    score = self._calculate_score(node, part.width, part.length) + 1
                    if best_score is None or score < best_score:
                        best_score = score
                        best_node = node
                        best_rotation = True
                        best_w = part.width
                        best_h = part.length

        return best_node, best_w, best_h, best_rotation

    def _collect_free_nodes(self, node: Optional[CutNode], free_nodes=None) -> List[CutNode]:
        if free_nodes is None:
            free_nodes = []
        if not node:
            return free_nodes
        if not node.used:
            free_nodes.append(node)
        self._collect_free_nodes(node.right, free_nodes)
        self._collect_free_nodes(node.down, free_nodes)
        return free_nodes

    def _try_place(self, sheet: Sheet, part: Part, strategy: str) -> bool:
        node, w, h, rotated = self._find_best_node(sheet, part)
        if node:
            self._split_node(sheet, node, part, w, h, rotated, strategy)
            return True
        return False

    def _split_node(self, sheet: Sheet, node: CutNode, part: Part, width: int, height: int, rotated: bool, strategy: str):
        """Разделяет узел. Реализация зависит от strategy ('rip' или 'cross')."""
        node.used = True
        node.part = part
        k = sheet.kerf

        remaining_w = node.width - width
        remaining_h = node.height - height

        if strategy == "rip":
            # Сначала вертикальный рез, потом горизонтальный.
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
        else:  # cross
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

        sheet.placed_parts.append(
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

    def _extract_cuts(self, node: Optional[CutNode], cuts_list: List[Cut], strategy: str):
        """Извлекает резы в порядке, допустимом для их физического выполнения."""
        if not node:
            return

        ordered_cuts = (
            (node.vertical_cut, node.horizontal_cut)
            if strategy == "rip"
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
        self._extract_cuts(node.right, cuts_list, strategy)
        self._extract_cuts(node.down, cuts_list, strategy)

    def _pack_single_sheet(self, sheet_w: int, sheet_h: int, batches: List[PartBatch], kerf: int, trim: int, strategy: str):
        """Упаковывает один лист, возвращает обновлённые партии, placements, cuts."""
        # Копия партий
        work_batches = [PartBatch(part=b.part, remaining=b.remaining) for b in batches]

        # Расширяем в плоский список
        parts_expanded = []
        for idx, b in enumerate(work_batches):
            for _ in range(b.remaining):
                p = Part(
                    label=b.part.label,
                    length=b.part.length,
                    width=b.part.width,
                    quantity=1,
                    rotatable=b.part.rotatable,
                    global_index=b.part.global_index
                )
                parts_expanded.append((idx, p))
        parts_expanded.sort(key=lambda item: item[1].length * item[1].width, reverse=True)

        sheet = Sheet(sheet_w, sheet_h, kerf, 0)

        for idx, p in parts_expanded:
            self._try_place(sheet, p, strategy)

        # Подсчитываем размещённые детали
        placed_per_batch = [0] * len(work_batches)
        for pp in sheet.placed_parts:
            found = False
            for i, b in enumerate(work_batches):
                if pp.rotated:
                    if (b.part.label == pp.part_label and
                        b.part.width == pp.length and
                        b.part.length == pp.width):
                        placed_per_batch[i] += 1
                        found = True
                        break
                else:
                    if (b.part.label == pp.part_label and
                        b.part.length == pp.length and
                        b.part.width == pp.width):
                        placed_per_batch[i] += 1
                        found = True
                        break
            if not found:
                # Дополнительный поиск по размерам
                for i, b in enumerate(work_batches):
                    if ((b.part.length == pp.length and b.part.width == pp.width) or
                        (b.part.rotatable and b.part.width == pp.length and b.part.length == pp.width)):
                        placed_per_batch[i] += 1
                        break

        for i, b in enumerate(work_batches):
            b.remaining -= placed_per_batch[i]

        if not sheet.placed_parts:
            return batches, [], []

        placements = []
        for pp in sheet.placed_parts:
            placements.append(PlacedPart(
                part_label=pp.part_label,
                x=pp.x + trim,
                y=pp.y + trim,
                length=pp.length,
                width=pp.width,
                rotated=pp.rotated,
                global_index=pp.global_index
            ))
        cuts = []
        self._extract_cuts(sheet.root, cuts, strategy)
        for c in cuts:
            c.x1 += trim
            c.y1 += trim
            c.x2 += trim
            c.y2 += trim

        return work_batches, placements, cuts
