from constants import *
import pandas as pd
from mesa import Agent


DATAFRAME = pd.read_csv('../logentrada.csv')

def manhattan_distance(pos1, pos2):
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


class MovementUtils:
    def __init__(self, model):
        self.model = model

    @staticmethod
    def valid_moves(agent, goal,agent_class_name="StudentAgent"):
        x, y = agent.pos
        possible_steps = [(x+dx, y+dy) for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)] 
                          if 0 <= x+dx < agent.model.width and 0 <= y+dy < agent.model.height 
                          and manhattan_distance((x+dx, y+dy), goal) < manhattan_distance((x, y), goal)
                          and all(content.type != "Parede" for content in agent.model.grid.get_cell_list_contents([(x+dx, y+dy)]) if hasattr(content, 'type'))
                          and all(content.type != "Bandeja" for content in agent.model.grid.get_cell_list_contents([(x+dx, y+dy)]) if hasattr(content, 'type'))
                          and not any(content.__class__.__name__ == agent_class_name for content in agent.model.grid.get_cell_list_contents([(x+dx, y+dy)]))]
        return possible_steps

    def is_valid_cell(self, cell_contents):
        return all(content.type != "Parede" for content in cell_contents if hasattr(content, 'type')) and not any(isinstance(content, StudentAgent) for content in cell_contents)