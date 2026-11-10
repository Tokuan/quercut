from typing import List, Optional, Tuple
from .base import Strategy
from ..models import (
    StockSheet, Part, PartBatch, PlacedPart, CutLayout, Cut, Direction, CutConfig
)
from .guillotine_base import GuillotineBaseStrategy

class AdvancedGuillotineStrategy(Strategy, GuillotineBaseStrategy):
    name = "Advanced Guillotine (параметризованная)"

    def __init__(self, preferred_direction="both", strip_sorting="desc", use_remnants=True):
        super().__init__()
        self.preferred_direction = preferred_direction   # "horizontal", "vertical", "both"
        self.strip_sorting = strip_sorting               # "desc", "asc", "area"
        self.use_remnants = use_remnants

    def layout(self, stocks, parts, config):
        batches = [PartBatch(part=p, remaining=p.quantity) for p in parts]
        layouts = []
        layout_id_ord = 1

        if not stocks:
            raise ValueError("Нет листов")

        # Находим шаблон для неограниченных листов
        unlimited_template = None
        for stock in stocks:
            if stock.is_unlimited:
                unlimited_template = stock
                break

        # Очередь листов
        stock_queue = list(stocks)

        while any(b.remaining > 0 for b in batches):
            if not stock_queue:
                if unlimited_template is not None:
                    # Создаём новый неограниченный лист
                    stock_queue.append(StockSheet(
                        unlimited_template.length,
                        unlimited_template.width,
                        unlimited_template.label,
                        is_unlimited=True
                    ))
                else:
                    # Листов больше нет — выходим
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

            # Перебираем первые резы и выбираем лучший
            best_placements = None
            best_cuts = None
            best_remaining = None
            best_waste = float('inf')
            best_temp_batches = None

            # Горизонтальные полосы (если разрешено)
            if self.preferred_direction in ("horizontal", "both"):
                heights = self._collect_sizes(batches, usable_w, orientation='horizontal')
                heights = self._sort_sizes(heights, batches, usable_l, usable_w, orientation='horizontal')
                for h in heights:
                    temp_batches = [PartBatch(part=b.part, remaining=b.remaining) for b in batches]
                    placements, cuts = self._fill_rectangle(
                        0, 0, usable_l, usable_w, temp_batches, config.kerf,
                        first_direction=Direction.HORIZONTAL, first_strip_size=h
                    )
                    if placements:
                        remaining = sum(b.remaining for b in temp_batches)
                        waste = usable_l * usable_w - sum(p.length * p.width for p in placements)
                        if best_remaining is None or remaining < best_remaining or (remaining == best_remaining and waste < best_waste):
                            best_remaining = remaining
                            best_waste = waste
                            best_placements = placements
                            best_cuts = cuts
                            best_temp_batches = temp_batches

            # Вертикальные полосы (если разрешено)
            if self.preferred_direction in ("vertical", "both"):
                widths = self._collect_sizes(batches, usable_l, orientation='vertical')
                widths = self._sort_sizes(widths, batches, usable_l, usable_w, orientation='vertical')
                for w in widths:
                    temp_batches = [PartBatch(part=b.part, remaining=b.remaining) for b in batches]
                    placements, cuts = self._fill_rectangle(
                        0, 0, usable_l, usable_w, temp_batches, config.kerf,
                        first_direction=Direction.VERTICAL, first_strip_size=w
                    )
                    if placements:
                        remaining = sum(b.remaining for b in temp_batches)
                        waste = usable_l * usable_w - sum(p.length * p.width for p in placements)
                        if best_remaining is None or remaining < best_remaining or (remaining == best_remaining and waste < best_waste):
                            best_remaining = remaining
                            best_waste = waste
                            best_placements = placements
                            best_cuts = cuts
                            best_temp_batches = temp_batches

            if best_placements is None:
                continue

            for p in best_placements:
                p.x += trim_left
                p.y += trim_bottom
            for c in best_cuts:
                c.x1 += trim_left
                c.y1 += trim_bottom
                c.x2 += trim_left
                c.y2 += trim_bottom

            for i, b in enumerate(batches):
                b.remaining = best_temp_batches[i].remaining

            layouts.append(CutLayout(
                layout_id=layout_id_ord,
                stock_length=stock.length,
                stock_width=stock.width,
                repetition=1,
                placements=best_placements,
                cuts=best_cuts
            ))
            layout_id_ord += 1

        # После цикла собираем неразмещённые детали
        unplaced = []
        for b in batches:
            if b.remaining > 0:
                unplaced.append({
                    'label': b.part.label,
                    'length': b.part.length,
                    'width': b.part.width,
                    'remaining': b.remaining
                })

        # Сохраняем неразмещённые детали в атрибут (опционально)
        self.unplaced_parts = unplaced

        return layouts

    def _fill_rectangle(self, x0, y0, L, W, batches, kerf, first_direction,
                        first_strip_size=None):
        if not any(b.remaining > 0 for b in batches):
            return [], []

        # Если явно задан размер первой полосы (из layout) — используем его
        if first_strip_size is not None:
            if first_direction == Direction.HORIZONTAL:
                strip_h = first_strip_size
                if strip_h <= W:
                    test_batches = [PartBatch(part=b.part, remaining=b.remaining) for b in batches]
                    placements, cuts, right_x = self._fill_horizontal_strip(
                        x0, y0, L, strip_h, test_batches, kerf
                    )
                    if placements:
                        # обновляем партии, заполняем остатки
                        return self._apply_strip_and_recurse(
                            x0, y0, L, W, batches, kerf, first_direction, strip_h,
                            placements, cuts, right_x, test_batches
                        )
            else:  # VERTICAL
                strip_w = first_strip_size
                if strip_w <= L:
                    test_batches = [PartBatch(part=b.part, remaining=b.remaining) for b in batches]
                    placements, cuts, bottom_y = self._fill_vertical_strip(
                        x0, y0, strip_w, W, test_batches, kerf
                    )
                    if placements:
                        return self._apply_strip_and_recurse(
                            x0, y0, L, W, batches, kerf, first_direction, strip_w,
                            placements, cuts, bottom_y, test_batches
                        )
            return [], []

        # Автоматический выбор размера полосы согласно strip_sorting
        if first_direction == Direction.HORIZONTAL:
            sizes = self._collect_sizes(batches, W, orientation='horizontal')
            sizes = self._sort_sizes(sizes, batches, L, W, orientation='horizontal')
            for h in sizes:
                test_batches = [PartBatch(part=b.part, remaining=b.remaining) for b in batches]
                placements, cuts, right_x = self._fill_horizontal_strip(
                    x0, y0, L, h, test_batches, kerf
                )
                if placements:
                    # первый подходящий размер даёт полосу
                    return self._apply_strip_and_recurse(
                        x0, y0, L, W, batches, kerf, first_direction, h,
                        placements, cuts, right_x, test_batches
                    )
        else:  # VERTICAL
            sizes = self._collect_sizes(batches, L, orientation='vertical')
            sizes = self._sort_sizes(sizes, batches, L, W, orientation='vertical')
            for w in sizes:
                test_batches = [PartBatch(part=b.part, remaining=b.remaining) for b in batches]
                placements, cuts, bottom_y = self._fill_vertical_strip(
                    x0, y0, w, W, test_batches, kerf
                )
                if placements:
                    return self._apply_strip_and_recurse(
                        x0, y0, L, W, batches, kerf, first_direction, w,
                        placements, cuts, bottom_y, test_batches
                    )

        # Если ничего не подошло – базовый упаковщик
        new_batches, placements, cuts = self._pack_single_sheet(
            L, W, batches, kerf, 0, "rip"
        )
        for p in placements:
            p.x += x0
            p.y += y0
        for c in cuts:
            c.x1 += x0
            c.y1 += y0
            c.x2 += x0
            c.y2 += y0
        for i, b in enumerate(batches):
            b.remaining = new_batches[i].remaining
        return placements, cuts

    def _apply_strip_and_recurse(self, x0, y0, L, W, batches, kerf, direction, size,
                                 placements_strip, cuts_strip, edge, test_batches):
        """Обновляет партии и формирует резы в физически исполнимом порядке."""
        for i, b in enumerate(batches):
            b.remaining = test_batches[i].remaining

        if direction == Direction.HORIZONTAL:
            right_x = edge
            strip_h = size

            # Сначала отделяем горизонтальную полосу от нижнего остатка.
            # После этого обе области становятся доступны для дальнейшего раскроя.
            rem_W = W - (strip_h + kerf)
            if rem_W > 0:
                cuts_strip.insert(
                    0, Cut(x0, y0 + strip_h, x0 + L, y0 + strip_h, Direction.HORIZONTAL)
                )

            # Внутренние вертикальные резы уже отделяют детали полосы
            # друг от друга и, если он есть, от правого остатка.
            if self.use_remnants and right_x < x0 + L:
                rem_L = (x0 + L) - right_x
                if rem_L > 0:
                    p_rec, c_rec = self._fill_rectangle(
                        right_x, y0, rem_L, strip_h, batches, kerf,
                        first_direction=Direction.VERTICAL
                    )
                    placements_strip.extend(p_rec)
                    cuts_strip.extend(c_rec)

            # Нижний остаток отделён первым горизонтальным резом,
            # поэтому его можно обрабатывать после правого остатка.
            if rem_W > 0:
                p_rec, c_rec = self._fill_rectangle(
                    x0, y0 + strip_h + kerf, L, rem_W, batches, kerf,
                    first_direction=Direction.HORIZONTAL
                )
                placements_strip.extend(p_rec)
                cuts_strip.extend(c_rec)

        else:  # VERTICAL
            bottom_y = edge
            strip_w = size

            # Сначала отделяем вертикальную полосу от правого остатка.
            rem_L = L - (strip_w + kerf)
            if rem_L > 0:
                cuts_strip.insert(
                    0, Cut(x0 + strip_w, y0, x0 + strip_w, y0 + W, Direction.VERTICAL)
                )

            # Внутренние горизонтальные резы полосы уже отделяют
            # детали друг от друга и, при наличии, нижний остаток.
            if self.use_remnants and bottom_y < y0 + W:
                rem_W = (y0 + W) - bottom_y
                if rem_W > 0:
                    p_rec, c_rec = self._fill_rectangle(
                        x0, bottom_y, strip_w, rem_W, batches, kerf,
                        first_direction=Direction.HORIZONTAL
                    )
                    placements_strip.extend(p_rec)
                    cuts_strip.extend(c_rec)

            # Правый остаток отделён первым вертикальным резом.
            if rem_L > 0:
                p_rec, c_rec = self._fill_rectangle(
                    x0 + strip_w + kerf, y0, rem_L, W, batches, kerf,
                    first_direction=Direction.VERTICAL
                )
                placements_strip.extend(p_rec)
                cuts_strip.extend(c_rec)

        return placements_strip, cuts_strip

    def _collect_sizes(self, batches, max_size, orientation):
        sizes = set()
        for b in batches:
            if b.remaining == 0:
                continue
            p = b.part
            if orientation == 'horizontal':
                sizes.add(p.width)
                if p.rotatable and p.length != p.width:
                    sizes.add(p.length)
            else:  # vertical
                sizes.add(p.length)
                if p.rotatable and p.width != p.length:
                    sizes.add(p.width)
        return [s for s in sizes if s <= max_size]

    def _sort_sizes(self, sizes, batches, max_L, max_W, orientation):
        if self.strip_sorting == "desc":
            return sorted(sizes, reverse=True)
        elif self.strip_sorting == "asc":
            return sorted(sizes)
        elif self.strip_sorting == "area":
            def area_for_size(size):
                total_area = 0
                for b in batches:
                    if b.remaining == 0:
                        continue
                    p = b.part
                    if orientation == 'horizontal':
                        if p.width == size and p.length <= max_L:
                            total_area += p.length * p.width * b.remaining
                        elif p.rotatable and p.length == size and p.width <= max_L:
                            total_area += p.width * p.length * b.remaining
                    else:
                        if p.length == size and p.width <= max_W:
                            total_area += p.length * p.width * b.remaining
                        elif p.rotatable and p.width == size and p.length <= max_W:
                            total_area += p.length * p.width * b.remaining
                return total_area
            return sorted(sizes, key=area_for_size, reverse=True)
        else:
            return sorted(sizes, reverse=True)

    def _select_strip_width(self, batches, max_L, max_W, kerf, vertical):
        """Выбирает размер полосы, максимизирующий суммарную длину (для горизонтальной) или высоту (для вертикальной) деталей."""
        best_size = None
        best_total_length = 0
        for b in batches:
            if b.remaining == 0:
                continue
            p = b.part
            if vertical:
                sizes = [p.length]
                if p.rotatable and p.width != p.length:
                    sizes.append(p.width)
                for size in sizes:
                    if size > max_L:
                        continue
                    total_length = 0
                    for b2 in batches:
                        if b2.remaining == 0:
                            continue
                        p2 = b2.part
                        # Деталь должна помещаться в полосу по длине и по высоте
                        if p2.length == size and p2.width <= max_W:
                            total_length += p2.width * b2.remaining
                        elif p2.rotatable and p2.width == size and p2.length <= max_W:
                            total_length += p2.length * b2.remaining
                    if total_length > best_total_length:
                        best_total_length = total_length
                        best_size = size
            else:  # horizontal
                sizes = [p.width]
                if p.rotatable and p.length != p.width:
                    sizes.append(p.length)
                for size in sizes:
                    if size > max_W:
                        continue
                    total_length = 0
                    for b2 in batches:
                        if b2.remaining == 0:
                            continue
                        p2 = b2.part
                        if p2.width == size and p2.length <= max_L:
                            total_length += p2.length * b2.remaining
                        elif p2.rotatable and p2.length == size and p2.width <= max_L:
                            total_length += p2.width * b2.remaining
                    if total_length > best_total_length:
                        best_total_length = total_length
                        best_size = size
        return best_size

    def _fill_horizontal_strip(self, x0, y0, strip_w, strip_h, batches, kerf):
        placements = []
        cuts = []
        x = x0
        # Сортируем детали по убыванию длины
        while x < x0 + strip_w:
            best = None
            best_len = 0
            for b in batches:
                if b.remaining == 0:
                    continue
                p = b.part
                if p.width == strip_h and p.length <= (x0 + strip_w - x):
                    if p.length > best_len:
                        best = (b, False, p.length, p.width)
                        best_len = p.length
                elif p.rotatable and p.length == strip_h and p.width <= (x0 + strip_w - x):
                    if p.width > best_len:
                        best = (b, True, p.width, p.length)
                        best_len = p.width
            if best is None:
                break
            b, rot, lx, wy = best
            b.remaining -= 1
            placements.append(PlacedPart(
                part_label=b.part.label,
                x=x, y=y0,
                length=lx, width=wy,
                rotated=rot,
                global_index=b.part.global_index
            ))
            # Отделяющий рез нужен и тогда, когда ширина пропила выходит
            # за дальнюю границу полосы: остаточная узкая полоска будет
            # поглощена пропилом. Важно не терять такой последний рез.
            if x + lx < x0 + strip_w:
                cuts.append(Cut(
                    x + lx, y0, x + lx, y0 + strip_h, Direction.VERTICAL
                ))
            x += lx + kerf
        return placements, cuts, x  # возвращаем x-координату конца последней детали

    def _fill_vertical_strip(self, x0, y0, strip_w, strip_h, batches, kerf):
        placements = []
        cuts = []
        y = y0
        while y < y0 + strip_h:
            best = None
            best_len = 0
            for b in batches:
                if b.remaining == 0:
                    continue
                p = b.part
                if p.length == strip_w and p.width <= (y0 + strip_h - y):
                    if p.width > best_len:
                        best = (b, False, p.length, p.width)
                        best_len = p.width
                elif p.rotatable and p.width == strip_w and p.length <= (y0 + strip_h - y):
                    if p.length > best_len:
                        best = (b, True, p.width, p.length)
                        best_len = p.length
            if best is None:
                break
            b, rot, lx, wy = best
            b.remaining -= 1
            placements.append(PlacedPart(
                part_label=b.part.label,
                x=x0, y=y,
                length=lx, width=wy,
                rotated=rot,
                global_index=b.part.global_index
            ))
            # Аналогично горизонтальному заполнению: последний рез может
            # выйти за край полосы, поглотив оставшийся узкий участок.
            if y + wy < y0 + strip_h:
                cuts.append(Cut(
                    x0, y + wy, x0 + strip_w, y + wy, Direction.HORIZONTAL
                ))
            y += wy + kerf
        return placements, cuts, y