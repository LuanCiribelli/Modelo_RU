# 1. Imports
from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.visualization.modules import CanvasGrid, TextElement
from mesa.visualization.ModularVisualization import ModularServer
from mesa.datacollection import DataCollector
import json
from mapa.mapa_RU import GridConfig, CellType

# Constants
with open('config.json', 'r') as f:
    config = json.load(f)

MAX_BLOCKED_STEPS = config["MAX_BLOCKED_STEPS"]
WAITING_TIME_THRESHOLD = config["WAITING_TIME_THRESHOLD"]
DISTANCE_THRESHOLD = config["DISTANCE_THRESHOLD"]

# 2. Global Utilities
def manhattan_distance(pos1, pos2):
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

# 3. Agents


#  StudentAgent
class StudentAgent(Agent):
    def __init__(self, unique_id, model, x, y):
        super().__init__(unique_id, model)
        self.pos = (x, y)
        self.state = "QUEUEING_TURNSTILE"
        self.blocked_steps = 0
        self.waiting_time = 0
        self.steps_in_current_state = 0
    
    def determine_goal(self):
        if self.state == "QUEUEING_TURNSTILE":
            tray = self.model.pathfinding.nearest_tray(self) 
            if manhattan_distance(self.pos, tray) < DISTANCE_THRESHOLD:
                self.state = "SEARCHING_TRAY"
                return tray

        goal_functions = {
            "QUEUEING_TURNSTILE": self.get_turnstile_goal,
            "SEARCHING_TRAY": lambda: self.model.pathfinding.nearest_tray(self),
            "EXITING": lambda: self.model.pathfinding.nearest_exit(self)

        }

        return goal_functions.get(self.state, lambda: self._unknown_state_error())()

    def get_turnstile_goal(self):
        return (self.model.width - 1, self.pos[1])
    
    def _unknown_state_error(self):
        raise ValueError(f"Unknown state: {self.state}")  # Point 3 addressed here

    def reached_goal(self, goal):
        if self.state == "QUEUEING_TURNSTILE":
            self.state = "SEARCHING_TRAY"
        elif self.state == "SEARCHING_TRAY":
            self.waiting_time += 1
            if self.waiting_time >= WAITING_TIME_THRESHOLD:  
                self.waiting_time = 0
                self.state = "EXITING"
        elif self.state == "EXITING":
            self.model.grid.remove_agent(self)
            self.model.schedule.remove(self)

    
    def get_best_step(self, goal):
        valid_moves = self.model.movement_utils.valid_moves(self, goal)
        if not valid_moves:
            self.blocked_steps += 1
            return None
        return min(valid_moves, key=lambda step: manhattan_distance(step, goal))


    def move(self):
        goal = self.determine_goal()
        if self.is_at_goal(goal):
            self.reached_goal(goal)
        else:
            best_step = self.get_best_step(goal)
            if best_step:
                self.model.grid.move_agent(self, best_step)

    def is_at_goal(self, goal):
        return self.pos == goal


    def step(self):
        "Defines the action taken by the student agent in each step."
        self.steps_in_current_state += 1
        if self.blocked_steps > MAX_BLOCKED_STEPS:
            pass
        if self.state == "QUEUEING_TURNSTILE" and self.steps_in_current_state > WAITING_TIME_THRESHOLD: 
            self.state = "SEARCHING_TRAY"
            self.steps_in_current_state = 0

        self.move()



class MovementUtils:
    def __init__(self, model):
        self.model = model

    @staticmethod
    def valid_moves(agent, goal):
        x, y = agent.pos
        possible_steps = [(x+dx, y+dy) for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)] 
                          if 0 <= x+dx < agent.model.width and 0 <= y+dy < agent.model.height 
                          and manhattan_distance((x+dx, y+dy), goal) < manhattan_distance((x, y), goal)
                          and all(content.type != "Parede" for content in agent.model.grid.get_cell_list_contents([(x+dx, y+dy)]) if hasattr(content, 'type'))
                          and not any(isinstance(content, StudentAgent) for content in agent.model.grid.get_cell_list_contents([(x+dx, y+dy)]))]
        return possible_steps

    def is_valid_cell(self, cell_contents):
        return all(content.type != "Parede" for content in cell_contents if hasattr(content, 'type')) and not any(isinstance(content, StudentAgent) for content in cell_contents)


class Pathfinding:
    def __init__(self, model, movement_utils):
        self.model = model
        self.movement_utils = movement_utils

    def students_around(self, tray):
        x, y = tray
        locations = [(x+i, y+j) for i in [-1, 0, 1] for j in [-1, 0, 1]]
        return sum(1 for loc in locations if any(isinstance(content, StudentAgent) for content in self.model.grid.get_cell_list_contents([loc])))

    def nearest(self, agent, target_type):
        x, y = agent.pos
        target_coords = [(i, j) for i, row in enumerate(self.model.external_grid)
                         for j, cell in enumerate(row) if cell == target_type]
        return min(target_coords, key=lambda pos: manhattan_distance((x, y), pos))

    def nearest_exit(self, agent):
        return self.nearest(agent, CellType.EXIT)

    def nearest_tray(self, agent):
        return self.nearest(agent, CellType.TRAY)

   

# 2.2 StaticAgent

class StaticAgent(Agent):
    """
    Agent representing static items in the restaurant like walls, turnstiles, etc.
    """
    
    def __init__(self, unique_id, model, x, y, agent_type):
        """
        Initialize a StaticAgent with its position and type.
        
        Args:
        - unique_id: A unique identifier for the agent.
        - model: The model instance in which the agent exists.
        - x, y: The agent's coordinates on the grid.
        - agent_type: The type of the static agent (e.g., 'Parede' for Wall).
        """
        super().__init__(unique_id, model)
        self.pos = (x, y)
        self.type = agent_type

# 3. Modelo e Visualização

class ModelText(TextElement):
    def __init__(self):
        pass
    
    def render(self, model):
        return f"Passo atual: {model.time} | Tempo médio de espera: {sum(agent.waiting_time for agent in model.schedule.agents if isinstance(agent, StudentAgent)) / len([agent for agent in model.schedule.agents if isinstance(agent, StudentAgent)])}"



# Modelo que representa o ambiente do restaurante
class RestaurantModel(Model):

    AGENT_TYPE_MAPPING = {
        CellType.TURNSTILE: 'Catraca',
        CellType.WALL: 'Parede',
        CellType.TRAY: 'Bandeja',
        CellType.EXIT: 'Saida'
    }

    def __init__(self, external_grid):
        self.height = len(external_grid)
        self.width = len(external_grid[0])
        self.external_grid = external_grid
        self.movement_utils = MovementUtils(self)
        self.pathfinding = Pathfinding(self, self.movement_utils)

        self.datacollector = DataCollector({
            "Average_Waiting_Time": lambda m: sum([agent.waiting_time for agent in m.schedule.agents if isinstance(agent, StudentAgent)]) / (len([agent for agent in m.schedule.agents if isinstance(agent, StudentAgent)]) or 1)
        })

        self.grid = MultiGrid(self.width, self.height, True)
        self.schedule = RandomActivation(self)
        self.time = 0
        self.error_message = None

        for y, row in enumerate(external_grid):
            for x, cell_value in enumerate(row):
                if cell_value == CellType.STUDENT:
                    student = StudentAgent((x, y), self, x, y)
                    self.grid.place_agent(student, (x, y))
                    self.schedule.add(student)
                elif cell_value in self.AGENT_TYPE_MAPPING:
                    agent_type = self.AGENT_TYPE_MAPPING[cell_value]
                    self.grid.place_agent(StaticAgent((x, y), self, x, y, agent_type), (x, y))

    def step(self):
        """Defines the action taken in each time step of the simulation."""
        if self.error_message:
            return
        self.time += 1
        self.schedule.step()
        self.datacollector.collect(self)
        all_students_blocked = all([student.blocked_steps >= MAX_BLOCKED_STEPS for student in self.schedule.agents if isinstance(student, StudentAgent)])
        if all_students_blocked:
            self.error_message = "Erro, todos os estudantes presos, modelo parado"
            return
        if not any(isinstance(agent, StudentAgent) for agent in self.schedule.agents):
            self.running = False



def agent_portrayal(agent):
    """Defines the visual portrayal of agents in the simulation."""
    if isinstance(agent, StudentAgent):
        if agent.waiting_time > WAITING_TIME_THRESHOLD:  
            color = "orange"
        elif agent.model.error_message:
            color = "red"
        else:
            color = "blue"
        return {
            "Shape": "circle",
            "Color": color,
            "Filled": "true",
            "Layer": 0,
            "r": 0.5
        }

    shape_colors = {
        "Catraca": "gray",
        "Parede": "black",
        "Bandeja": "green",
        "Saida": "red"
    }

    return {
        "Shape": "rect",
        "Color": shape_colors.get(agent.type, "white"),
        "Filled": "true",
        "Layer": 1,
        "w": 1,
        "h": 1
    }


if __name__ == "__main__":
    external_grid = GridConfig.get_grid()
    model_text = ModelText()
    # Adjusting grid dimensions for better visualization
    grid = CanvasGrid(agent_portrayal, len(external_grid[0]), len(external_grid), 800, 1600)
    server = ModularServer(RestaurantModel, [grid, model_text], "University Restaurant Model", {"external_grid": external_grid})
    server.launch()


