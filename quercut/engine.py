from .strategies.base import Strategy
from .models import CutConfig
from .parser import parse_input
from .output import format_output

class CuttingOptimizer:
    def __init__(self, strategy: Strategy, config: CutConfig):
        self.strategy = strategy
        self.config = config

    def optimize(self, input_text: str) -> str:
        stocks, parts, kerf = parse_input(input_text)
        # возможно, конфиг kerf переопределяется из входа
        effective_config = CutConfig(kerf=kerf, trim_margin=self.config.trim_margin)
        layouts = self.strategy.layout(stocks, parts, effective_config)
        return format_output(layouts, effective_config.kerf)