# quercut/strategy_factory.py

"""
Единая точка входа для создания стратегий раскроя.
"""

from .strategies.simple_rip import SimpleRipStrategy
from .strategies.simple_cross import SimpleCrossStrategy
from .strategies.optimal import OptimalGuillotineStrategy
from .strategies.advanced import AdvancedGuillotineStrategy


def create_strategy(strategy: str = 'simple',
                    preferred_direction: str = 'both',
                    strip_sorting: str = 'desc'):
    """
    Создаёт и возвращает экземпляр стратегии раскроя.

    Параметры:
        strategy: 'simple' | 'advanced'
        preferred_direction:
            для 'simple': 'horizontal' → SimpleRip, 'vertical' → SimpleCross, 'both' → Optimal
            для 'advanced': передаётся в конструктор
        strip_sorting: 'desc' | 'asc' | 'area' (только для 'advanced')
    """

    if strategy == 'simple':
        if preferred_direction == 'horizontal':
            return SimpleRipStrategy()
        elif preferred_direction == 'vertical':
            return SimpleCrossStrategy()
        else:  # 'both'
            return OptimalGuillotineStrategy()

    elif strategy == 'advanced':
        return AdvancedGuillotineStrategy(
            preferred_direction=preferred_direction,
            strip_sorting=strip_sorting,
        )

    raise ValueError(f"Неизвестная стратегия: {strategy}")