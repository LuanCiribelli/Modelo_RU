from mesa import Agent
from utilities import manhattan_distance, MovementUtils
from constants import *
from mapa.mapa_RU import CellType
 




class StudentAgent(Agent):
    def __init__(self, unique_id, model, x, y):
        super().__init__(unique_id, model)
        self.pos = (x, y)
        self.state = "SEARCHING_TRAY"
        self.waiting_time = 0
        self.blocked_steps = 0

    def determine_goal(self):
        if self.state == "SEARCHING_TRAY":
            return self.model.pathfinding.nearest_tray(self)
        elif self.state == "WAITING_AT_TRAY":
            return self.pos
        elif self.state == "EXITING":
            return self.model.pathfinding.nearest_exit(self)

    def move_towards(self, goal):
        valid_moves = self.model.movement_utils.valid_moves(self, goal, "StudentAgent")
        if valid_moves:
            best_step = min(valid_moves, key=lambda step: manhattan_distance(step, goal))
            self.model.grid.move_agent(self, best_step)
            self.blocked_steps = 0  # Reset blocked_steps if a valid move is found
        else:
            self.blocked_steps += 1  # Increment blocked_steps if no valid move


    def reached_goal(self, goal):
        if self.state == "SEARCHING_TRAY":
            self.state = "WAITING_AT_TRAY"
        elif self.state == "WAITING_AT_TRAY":
            self.waiting_time += 1
            if self.waiting_time >= WAITING_TIME_THRESHOLD:
                self.state = "EXITING"
        elif self.state == "EXITING":
            current_cell_contents = self.model.grid.get_cell_list_contents([self.pos])
            if any(content.type == "S" for content in current_cell_contents if hasattr(content, 'type')):
                self.model.grid.remove_agent(self)
                self.model.schedule.remove(self)

    def step(self):
        if self.state != "WAITING_AT_TRAY":
            goal = self.determine_goal()
            if self.is_at_goal(goal):
                self.reached_goal(goal)
            else:
                self.move_towards(goal)
        else:
            self.reached_goal(self.pos)

    def is_at_goal(self, goal):
        return self.pos == goal






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
