import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from quercut.parser import parse_input
from quercut.output import format_output
from quercut.visualization import generate_svg
from quercut.models import CutConfig
from quercut.strategies.simple_rip import SimpleRipStrategy
from quercut.strategies.simple_cross import SimpleCrossStrategy
from quercut.strategies.optimal import OptimalGuillotineStrategy
from quercut.strategies.advanced import AdvancedGuillotineStrategy

SAMPLE_INPUT = """
K	4
LT	50
RT	15
TT	15
BT	15
@	Length	Width	Quantity	Grain direction
S	1200	2000    1
S	1600	2000    1
S	3000	2000    1
@	Length	Width	Quantity	Grain direction	Label
P   1800 320 3
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

if __name__ == "__main__":
    stocks, parts, config = parse_input(SAMPLE_INPUT)

    preferred_direction = "both"
    strip_sorting = "desc"

    # Выберите стратегию:
    #strategy = SimpleRipStrategy()
    strategy = SimpleCrossStrategy()
    #strategy = OptimalGuillotineStrategy()
    #strategy = AdvancedGuillotineStrategy()
    #strategy = AdvancedGuillotineStrategy(preferred_direction="horizontal", strip_sorting="desc")
    #strategy = AdvancedGuillotineStrategy(preferred_direction="vertical", strip_sorting="area")
    #strategy = AdvancedGuillotineStrategy(preferred_direction=preferred_direction, strip_sorting=strip_sorting)

    layouts = strategy.layout(stocks, parts, config)

    print(f"Использовано листов: {len(layouts)}")
    for lo in layouts:
        print(f" {lo.layout_id}: {len(lo.placements)} деталей")

    report = format_output(layouts, config)
    print("=== Текстовый отчёт ===")
    print("preferred_direction =", preferred_direction)
    print("strip_sorting =", strip_sorting)
    print(report)
    # Проверяем неразмещённые детали
    if hasattr(strategy, 'unplaced_parts') and strategy.unplaced_parts:
        print("\nНЕРАЗМЕЩЁННЫЕ ДЕТАЛИ:")
        for u in strategy.unplaced_parts:
            print(f"  {u['remaining']} шт. {u['length']}×{u['width']} (label: {u['label']})")

    svg = generate_svg(layouts, config, monochrome=False)
    with open("test_output.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("SVG сохранён в test_output.svg")