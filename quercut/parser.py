from typing import List, Tuple
from .models import StockSheet, Part, CutConfig

def parse_input(text: str) -> Tuple[List[StockSheet], List[Part], CutConfig]:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    stocks = []
    parts = []
    config_data = {
        'kerf': 0,
        'trim_left': 0,
        'trim_right': 0,
        'trim_top': 0,
        'trim_bottom': 0
    }
    global_idx = 0

    for line in lines:
        if line.startswith('@'):
            continue
        tokens = line.split()
        if not tokens:
            continue
        key = tokens[0]
        if key == 'K':
            if len(tokens) > 1:
                config_data['kerf'] = float(tokens[1])
        elif key == 'LT':
            if len(tokens) > 1:
                config_data['trim_left'] = int(tokens[1])
        elif key == 'RT':
            if len(tokens) > 1:
                config_data['trim_right'] = int(tokens[1])
        elif key == 'TT':
            if len(tokens) > 1:
                config_data['trim_top'] = int(tokens[1])
        elif key == 'BT':
            if len(tokens) > 1:
                config_data['trim_bottom'] = int(tokens[1])
        elif key == 'S':
            if len(tokens) >= 3:
                length = int(tokens[1])
                width = int(tokens[2])
                if len(tokens) > 3:
                    qty = int(tokens[3])
                    is_unlimited = False  # указано точное количество → обрезки
                else:
                    qty = 1  # хотя бы 1, но в алгоритме будет восполняться
                    is_unlimited = True  # количество не указано → целые листы
                for _ in range(qty):
                    stocks.append(StockSheet(length, width, is_unlimited=is_unlimited))
        elif key == 'P':
            if len(tokens) >= 4:
                length = int(tokens[1])
                width = int(tokens[2])
                qty = int(tokens[3])
                rotatable = True
                label = ""
                if len(tokens) >= 5 and tokens[4] and tokens[4] != '0':
                    rotatable = False
                if len(tokens) >= 6:
                    label = tokens[5]
                parts.append(Part(label=label, length=length, width=width,
                                  quantity=qty, rotatable=rotatable, global_index=global_idx))
                global_idx += 1

    config = CutConfig(
        kerf=config_data['kerf'],
        trim_left=config_data['trim_left'],
        trim_right=config_data['trim_right'],
        trim_top=config_data['trim_top'],
        trim_bottom=config_data['trim_bottom']
    )
    for i, p in enumerate(parts):
        print(f"{i}: label={p.label}, global_index={p.global_index}, size={p.length}x{p.width}")

    return stocks, parts, config