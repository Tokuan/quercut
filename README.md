
# Quercut

Гильотинный раскрой листовых материалов на Python.

## Возможности

-   **4 режима раскроя**: Простой (Simple Rip / Simple Cross / Optimal) и Продвинутый (Advanced)
-   **Единая точка входа**: фабрика стратегий `create_strategy()`
-   **Подрезка краёв**: раздельные отступы слева, справа, сверху, снизу
-   **Учёт толщины реза** (kerf), может быть дробным (например, 3.2 мм)
-   **Поворот деталей** (grain direction)
-   **Сквозная нумерация**: каждой детали присваивается `global_index` в порядке исходного списка
-   **Визуализация в SVG**: цветной и чёрно-белый режимы для печати
-   **Установка как Python-пакет**: `pip install quercut`

## Установка

```bash
# Из локальной папки (режим разработки)
pip install -e /path/to/Quercut

# Из GitHub
pip install git+https://github.com/Tokuan/quercut.git
```

## Быстрый старт (Python API)

```python
from quercut.parser import parse_input
from quercut.strategy_factory import create_strategy
from quercut.visualization import generate_svg
from quercut.output import format_output
from quercut.models import CutConfig

# 1. Подготовка данных в формате Opticutter
input_text = """
K	4.0
LT	15
RT	15
TT	15
BT	15
@	Length	Width	Quantity	Grain direction
S	3000	2000
@	Length	Width	Quantity	Grain direction	Label
P	200	300	6
P	300	400	6
P	400	500	4
P	1000	200	4
P	100	500	3
P	800	300	5
P	800	400	5
P	800	1000	3
P	700	400	2
P	800	200	6
"""

# 2. Парсинг
stocks, parts, config = parse_input(input_text)

# 3. Выбор стратегии через фабрику
strategy = create_strategy(
    strategy='simple',            # 'simple' или 'advanced'
    preferred_direction='both',   # 'horizontal', 'vertical', 'both'
    strip_sorting='desc',         # 'desc', 'asc', 'area' (для advanced)
)

# 4. Раскрой
layouts = strategy.layout(stocks, parts, config)

# 5. Результаты
print(f"Использовано листов: {len(layouts)}")
for lo in layouts:
    print(f"  {lo.layout_id}: {len(lo.placements)} деталей")

# 6. Текстовый отчёт
report = format_output(layouts, config)
print(report)

# 7. SVG-визуализация (цветная)
svg = generate_svg(layouts, config)
with open('output.svg', 'w', encoding='utf-8') as f:
    f.write(svg)

# 8. SVG для чёрно-белой печати
svg_bw = generate_svg(layouts, config, monochrome=True)
with open('output_bw.svg', 'w', encoding='utf-8') as f:
    f.write(svg_bw)

# 9. Проверка неразмещённых деталей (если листы ограничены)
if hasattr(strategy, 'unplaced_parts') and strategy.unplaced_parts:
    for u in strategy.unplaced_parts:
        print(f"Не размещено: {u['remaining']} шт. {u['length']}×{u['width']} ({u['label']})")
```

## Формат входных данных (Opticutter-совместимый)

```
K	<толщина реза>
LT	<подрезка слева>
RT	<подрезка справа>
TT	<подрезка сверху>
BT	<подрезка снизу>
@	Length	Width	Quantity	Grain direction
S	<длина>	<ширина>	[количество]
@	Length	Width	Quantity	Grain direction	Label
P	<длина>	<ширина>	<количество>	[grain]	[label]
```

**Поля:**

| Ключ | Назначение | По умолчанию |
|------|-----------|--------------|
| `K`  | Толщина реза (мм), может быть дробной | 0 |
| `LT` | Подрезка слева (мм) | 0 |
| `RT` | Подрезка справа (мм) | 0 |
| `TT` | Подрезка сверху (мм) | 0 |
| `BT` | Подрезка снизу (мм) | 0 |
| `S`  | Лист материала: длина, ширина, количество | 1 шт. |
| `P`  | Деталь: длина, ширина, количество, grain (0=можно поворачивать, 1=нельзя), метка | rotatable=true |

**Примечание по `S` (листы):**

-   Если количество не указано — лист считается **неограниченным** (`is_unlimited=True`). Алгоритм будет создавать новые листы этого размера, пока не разместит все детали.
-   Если количество указано — это **ограниченный обрезок**. Когда такие листы заканчиваются, раскрой останавливается, и неразмещённые детали возвращаются в `unplaced_parts`.

## Формат ответа (JSON)

```json
{
  "success": true,
  "total_sheets": 2,
  "config": {
    "kerf": 4.0,
    "trim_left": 15,
    "trim_right": 15,
    "trim_top": 15,
    "trim_bottom": 15
  },
  "layouts": [
    {
      "layout_id": 1,
      "stock_length": 3000,
      "stock_width": 2000,
      "placements": [
        {
          "label": "",
          "x": 15,
          "y": 15,
          "length": 800,
          "width": 1000,
          "rotated": false,
          "global_index": 0
        }
      ],
      "cuts": [
        {
          "x1": 800,
          "y1": 15,
          "x2": 800,
          "y2": 1015,
          "direction": "VERTICAL"
        }
      ]
    }
  ],
  "unplaced": [
    {
      "label": "",
      "length": 200,
      "width": 300,
      "remaining": 3
    }
  ]
}
```

**Описание полей ответа:**

| Поле | Тип | Описание |
|------|-----|----------|
| `success` | bool | Всегда `true` при успешном расчёте |
| `total_sheets` | int | Количество использованных листов |
| `config` | object | Параметры раскроя (kerf + trim) |
| `layouts` | array | Список листов с размещёнными деталями |
| `layouts[].layout_id` | int | Идентификатор листа (1, 2, 3...) |
| `layouts[].stock_length` | int | Полная длина листа (с учётом подрезки) |
| `layouts[].stock_width` | int | Полная ширина листа |
| `layouts[].placements` | array | Размещённые детали |
| `placements[].x` | int | X-координата левого нижнего угла (от начала листа) |
| `placements[].y` | int | Y-координата левого нижнего угла |
| `placements[].length` | int | Размер детали по оси X |
| `placements[].width` | int | Размер детали по оси Y |
| `placements[].rotated` | bool | Была ли деталь повёрнута на 90° |
| `placements[].global_index` | int | Порядковый номер детали в исходном списке (начинается с 0) |
| `layouts[].cuts` | array | Линии резов |
| `cuts[].x1, y1` | int | Начало линии реза |
| `cuts[].x2, y2` | int | Конец линии реза |
| `cuts[].direction` | string | `"VERTICAL"` или `"HORIZONTAL"` |
| `unplaced` | array | Неразмещённые детали (пусто, если все размещены) |
| `unplaced[].remaining` | int | Сколько штук не размещено |

## REST API

### POST /api/cutting/api/calculate/

**Тело запроса:**

```json
{
  "kerf": 4.0,
  "trim_left": 15,
  "trim_right": 15,
  "trim_top": 15,
  "trim_bottom": 15,
  "strategy": "simple",
  "preferred_direction": "both",
  "strip_sorting": "desc",
  "stocks": [
    {
      "length": 3000,
      "width": 2000,
      "quantity": 1,
      "is_unlimited": true
    }
  ],
  "parts": [
    {
      "length": 200,
      "width": 300,
      "quantity": 6,
      "rotatable": true,
      "label": ""
    }
  ]
}
```

**Параметры стратегии:**

| Параметр | Тип | Значения | По умолчанию |
|----------|-----|---------|--------------|
| `strategy` | string | `"simple"`, `"advanced"` | `"simple"` |
| `preferred_direction` | string | `"horizontal"`, `"vertical"`, `"both"` | `"both"` |
| `strip_sorting` | string | `"desc"`, `"asc"`, `"area"` | `"desc"` |

**Логика выбора стратегии:**

-   `strategy="simple"` + `preferred_direction="horizontal"` → **SimpleRip** (первый рез вдоль)
-   `strategy="simple"` + `preferred_direction="vertical"` → **SimpleCross** (первый рез поперёк)
-   `strategy="simple"` + `preferred_direction="both"` → **Optimal** (перебор обоих направлений)
-   `strategy="advanced"` → **Advanced** (с перебором первых резов), использует `preferred_direction` и `strip_sorting`

**Ответ:** JSON (см. раздел «Формат ответа»).

## Система координат

-   Точка **(0, 0)** — левый нижний угол листа.
-   Ось **X** — длина листа (вправо).
-   Ось **Y** — ширина листа (вверх).
-   Подрезки сдвигают полезную область:
    -   `trim_left` отступает от левого края
    -   `trim_bottom` отступает от нижнего края
    -   `trim_right` отступает от правого края
    -   `trim_top` отступает от верхнего края

## Стратегии

### Simple (простая)

-   **SimpleRip** (`preferred_direction="horizontal"`): первый рез всегда вдоль (горизонтальный), затем полосы делятся вертикальными резами.
-   **SimpleCross** (`preferred_direction="vertical"`): первый рез всегда поперёк (вертикальный), затем полосы делятся горизонтальными резами.
-   **Optimal** (`preferred_direction="both"`): для каждого листа пробуются оба варианта, выбирается лучший.

### Advanced (продвинутая)

-   Перебирает возможные первые резы (ширины/высоты полос) для каждого листа.
-   Использует `preferred_direction` для ограничения перебора (`"horizontal"`, `"vertical"`, `"both"`).
-   Использует `strip_sorting` для порядка перебора размеров полос:
    -   `"desc"` — от больших к меньшим
    -   `"asc"` — от меньших к большим
    -   `"area"` — по убыванию суммарной площади деталей, помещающихся в полосу

## Лицензия

MIT
```
