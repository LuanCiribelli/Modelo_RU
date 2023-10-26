from mesa import Agent
from constants import *
from mapa.mapa_RU import CellType
from constants import *


class StudentAgent(Agent):
    STATES = ["SEARCHING_TRAY", "GOING_TO_JUICE", "GOING_TO_SPICES", "GOING_TO_DESSERT", "GOING_TO_TABLE", "EXITING"]
    
    def __init__(self, unique_id, model, x, y):
        super().__init__(unique_id, model)
        self.pos = (x, y)
        self.state = "SEARCHING_TRAY"
        self.waiting_time = 0
        self.blocked_steps = 0
        self.visited_groups = set()
    
    def move_towards(self, goal):
        valid_moves = self.model.movement_utils.valid_moves(self, goal)
        if valid_moves:
            best_step = min(valid_moves, key=lambda step: manhattan_distance(step, goal))
            self.model.grid.move_agent(self, best_step)
            self.blocked_steps = 0  # Reset blocked_steps if a valid move is found
        else:
            self.blocked_steps += 1  # Increment blocked_steps if no valid move

    def determine_goal(self):
        if self.state == "SEARCHING_TRAY":
            tray_coords = self.model.locations_cache['trays']
            if not tray_coords:
                return self.pos  # If no trays, remain in position
            return self.model.movement_utils.nearest(self, CellType.TRAY)
        elif self.state == "GOING_TO_JUICE":
            nearest_juice = self.model.movement_utils.nearest(self, CellType.JUICE)
            return self.get_adjacent_empty_cell(nearest_juice)
        elif self.state == "GOING_TO_SPICES":
            spice_coords = self.model.locations_cache['spices']
            return self.model.movement_utils.nearest(self, CellType.SPICES)
        elif self.state == "GOING_TO_DESSERT":
            dessert_coords = self.model.locations_cache['desserts']
            return self.model.movement_utils.nearest(self, CellType.DESSERT)
        elif self.state == "GOING_TO_TABLE":
            table_coords = self.model.locations_cache['tables']
            return self.random.choice(table_coords)
        elif self.state == "EXITING":
            return self.model.movement_utils.nearest_exit(self)
        else:
            return self.pos  # Default case if an unknown state

    def get_adjacent_empty_cell(self, target_pos):
        x, y = target_pos
        possible_adjacent_cells = [(x+dx, y+dy) for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                                if 0 <= x+dx < self.model.width and 0 <= y+dy < self.model.height]
        for cell in possible_adjacent_cells:
            if not self.model.grid.get_cell_list_contents([cell]):
                return cell
        return self.pos  # Default: return the agent's own position if no adjacent empty cell found



    def reached_goal(self, goal):
        transitions = {
            "SEARCHING_TRAY": "GOING_TO_JUICE",
            "GOING_TO_JUICE": "GOING_TO_DESSERT",
            "GOING_TO_DESSERT": "GOING_TO_SPICES",
            "GOING_TO_SPICES": "GOING_TO_TABLE",
            "GOING_TO_TABLE": "EXITING"
        }
        self.state = transitions.get(self.state, "EXITING")

        if self.state == "EXITING":
            # Remove agent from the grid and schedule when exiting
            self.model.grid.remove_agent(self)
            self.model.schedule.remove(self)


    def step(self):
        goal = self.determine_goal()
        
        # Get the content (cell type) at the goal position
        
        goal_content = self.model.grid.get_cell_list_contents([goal])
        if goal_content:
            target_cell_type = next((content.type for content in goal_content if hasattr(content, 'type')), None)
        else:
            target_cell_type = None

        print(f"Student at position {self.pos}. In state {self.state} trying to go to position {goal} to get to the cell type {target_cell_type}")
        
        if self.is_at_goal(goal):
            self.reached_goal(goal)
        else:
            self.move_towards(goal)

            
    def is_at_goal(self, goal):
        return self.pos == goal

    def is_valid_position(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    
class StaticAgent(Agent):
    def __init__(self, unique_id, model, x, y, agent_type, content=None):
        super().__init__(unique_id, model)
        self.pos = (x, y)
        self.type = agent_type
        self.content = content
        
        if agent_type == "Bandeja":
            if content == "vegan":
                self.portions = VEGAN_TRAY_PORTIONS
            elif content == "meat":
                self.portions = MEAT_TRAY_PORTIONS
            else:
                self.portions = DEFAULT_TRAY_PORTIONS
        else:
            self.portions = None

AGENT_CLASSES = {
    "StudentAgent": StudentAgent,
    "StaticAgent": StaticAgent,
}


def manhattan_distance(pos1, pos2):
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


class MovementUtils:
    def __init__(self, model): 
        self.model = model

    @staticmethod
    def valid_moves(agent, goal):
        x, y = agent.pos
        possible_steps = [(x+dx, y+dy) for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)] 
                        if 0 <= x+dx < agent.model.width and 0 <= y+dy < agent.model.height
                        and not agent.model.grid.get_cell_list_contents([(x+dx, y+dy)])]
    

        return possible_steps

    def is_valid_cell(self, cell_contents):
        return all(content.type != "Parede" for content in cell_contents if hasattr(content, 'type')) and not any(isinstance(content, StudentAgent) for content in cell_contents)

    def students_around(self, tray):
        x, y = tray
        
        # Assuming the grid is of size grid_width x grid_height
        grid_width, grid_height = self.model.grid.width, self.model.grid.height

        # Calculate all neighboring locations
        locations = [(x+i, y+j) for i in [-1, 0, 1] for j in [-1, 0, 1]]

        # Filter locations to only those inside the grid
        valid_locations = [(x, y) for x, y in locations if 0 <= x < grid_width and 0 <= y < grid_height]

        # Count the number of students in the valid locations
        
        return sum(1 for loc in valid_locations if any(isinstance(content, StudentAgent) for content in self.model.grid.get_cell_list_contents([loc])))


    def nearest(self, agent, target_type):
            x, y = agent.pos
            target_coords = [(i, j) for i, row in enumerate(self.model.external_grid)
                            for j, cell in enumerate(row) if cell == target_type]

            if target_type == CellType.TABLE:
                # Sort tables by how many student agents are around them.
                target_coords = sorted(target_coords, key=lambda pos: self.students_around(pos))

            return min(target_coords, key=lambda pos: manhattan_distance((x, y), pos))


    def nearest_exit(self, agent):
        return self.nearest(agent, CellType.EXIT)

    def nearest_tray(self, agent):
        tray_coords = [(i, j) for i, row in enumerate(self.model.external_grid)
                    for j, cell in enumerate(row) if cell == CellType.TRAY]

        # Sort trays by the number of portions left (in ascending order).
        sorted_tray_coords = sorted(tray_coords, key=lambda pos: self.model.grid.get_cell_list_contents([pos])[0].portions)

        if not sorted_tray_coords:
            return None

        return sorted_tray_coords[0]  # return the tray with the most portions left.

