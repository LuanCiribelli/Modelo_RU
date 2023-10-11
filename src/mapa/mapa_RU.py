import json
from enum import Enum

class CellType(Enum):
    STUDENT = 'E'
    TURNSTILE = 'C'
    EMPTY = '0'
    WALL = 'P'
    TRAY = 'B'
    EXIT = 'S'

class GridConfig:

    @staticmethod
    def get_grid():
        with open('mapa\grid_config.json', 'r') as file:
            data = json.load(file)
            raw_grid = data['grid']
        return [[CellType(cell) for cell in row] for row in raw_grid]
