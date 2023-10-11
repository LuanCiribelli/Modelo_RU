from mesa import Agent
from utilities import manhattan_distance
from constants import WAITING_TIME_THRESHOLD, MAX_BLOCKED_STEPS



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
        # Check for an agent in front
        x, y = self.pos
        agent_in_front = self.model.grid.get_cell_list_contents([(x+1, y)])  # assuming the queue moves horizontally to the right
        
        # If the agent in front exists and is a student and isn't moving, then don't move
        if agent_in_front and isinstance(agent_in_front[0], StudentAgent) and agent_in_front[0].blocked_steps >= MAX_BLOCKED_STEPS:
            self.blocked_steps += 1
            return

        # Else, continue with the existing logic
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
