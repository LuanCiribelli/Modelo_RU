from mesa import Agent
from constants import *
from mapa.mapa_RU import CellType
from constants import *


class StudentAgent(Agent):
    STATES = ["GOING_TO_RICE_TRAY", "GOING_TO_BROWN_RICE_TRAY","GOING_TO_BEANS_TRAY","GOING_TO_GUARN_TRAY","GOING_TO_VEG_TRAY" ,"GOING_TO_MEAT_TRAY",
               "GOING_TO_SAL_TRAY","GOING_TO_TALHER_TRAY","GOING_TO_JUICE", "GOING_TO_SPICES", "GOING_TO_DESSERT", "GOING_TO_TABLE", "EXITING"]
    
    def __init__(self, unique_id, model, x, y):
        super().__init__(unique_id, model)
        self.pos = (x, y)
        self.state = "GOING_TO_RICE_TRAY"
        self.waiting_time = 0
        self.blocked_steps = 0
        self.visited_groups = set()
        self.got_rice = False
        self.got_beans = False
        self.got_meat = False
        self.got_salad = False
        self.got_talheres = False
    
    def move_towards(self, goal):
        path = self.a_star_pathfinding(self.pos, goal)
        if path:
            next_step = path[1]
            self.model.grid.move_agent(self, next_step)
            self.blocked_steps = 0
        else:
            self.blocked_steps += 1


    def determine_goal(self):
            if self.state == "GOING_TO_RICE_TRAY":
                return min(self.model.locations_cache['rice_trays'], key=lambda pos: manhattan_distance(self.pos, pos))
            elif self.state == "GOING_TO_BROWN_RICE_TRAY":
                return min(self.model.locations_cache['brown_rice_trays'], key=lambda pos: manhattan_distance(self.pos, pos))
            elif self.state == "GOING_TO_BEANS_TRAY":
                return min(self.model.locations_cache['beans_trays'], key=lambda pos: manhattan_distance(self.pos, pos))
            elif self.state == "GOING_TO_GUARN_TRAY":
                return min(self.model.locations_cache['guarn_trays'], key=lambda pos: manhattan_distance(self.pos, pos))
            elif self.state == "GOING_TO_VEG_TRAY":
                return min(self.model.locations_cache['veg_trays'], key=lambda pos: manhattan_distance(self.pos, pos))
            elif self.state == "GOING_TO_MEAT_TRAY":
                return min(self.model.locations_cache['meat_trays'], key=lambda pos: manhattan_distance(self.pos, pos))
            elif self.state == "GOING_TO_SAL_TRAY":
                return min(self.model.locations_cache['sal_trays'], key=lambda pos: manhattan_distance(self.pos, pos))
            elif self.state == "GOING_TO_TALHER_TRAY":
                return min(self.model.locations_cache['talher_trays'], key=lambda pos: manhattan_distance(self.pos, pos))
            elif self.state == "GOING_TO_JUICE":
                nearest_juice = min(self.model.locations_cache['juices'], key=lambda pos: manhattan_distance(self.pos, pos))
                return self.get_adjacent_empty_cell(nearest_juice)
            elif self.state == "GOING_TO_SPICES":
                return min(self.model.locations_cache['spices'], key=lambda pos: manhattan_distance(self.pos, pos))
            elif self.state == "GOING_TO_DESSERT":
                return min(self.model.locations_cache['desserts'], key=lambda pos: manhattan_distance(self.pos, pos))
            elif self.state == "GOING_TO_TABLE":
                return self.random.choice(self.model.locations_cache['tables'])
            elif self.state == "EXITING":
                return min(self.model.locations_cache['exits'], key=lambda pos: manhattan_distance(self.pos, pos))
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

    
    def reached_goal(self,goal):
        # Update the boolean values based on current state
        if self.state == "GOING_TO_RICE_TRAY":
            self.got_rice = True
        elif self.state == "GOING_TO_BEANS_TRAY":
            self.got_beans = True
        elif self.state == "GOING_TO_MEAT_TRAY":
            self.got_meat = True
        elif self.state == "GOING_TO_SAL_TRAY":
            self.got_salad = True
        elif self.state == "GOING_TO_TALHER_TRAY":
            self.got_talheres = True
            
        # Only allow transition to juice or further states if all items have been obtained
        if self.state == "GOING_TO_TALHER_TRAY" and not (self.got_rice and self.got_beans and self.got_meat and self.got_salad and self.got_talheres):
            return  # do not change state
        transitions = {
        "GOING_TO_RICE_TRAY": "GOING_TO_BROWN_RICE_TRAY",
        "GOING_TO_BROWN_RICE_TRAY": "GOING_TO_BEANS_TRAY",
        "GOING_TO_BEANS_TRAY":"GOING_TO_GUARN_TRAY",
        "GOING_TO_GUARN_TRAY":"GOING_TO_VEG_TRAY",
        "GOING_TO_VEG_TRAY":"GOING_TO_MEAT_TRAY",
        "GOING_TO_MEAT_TRAY":"GOING_TO_SAL_TRAY",
        "GOING_TO_SAL_TRAY":"GOING_TO_TALHER_TRAY",
        "GOING_TO_TALHER_TRAY":"GOING_TO_JUICE",
        "GOING_TO_JUICE":"GOING_TO_SPICES",
        "GOING_TO_SPICES":"GOING_TO_DESSERT",
        "GOING_TO_DESSERT":"GOING_TO_TABLE",
        "GOING_TO_TABLE":"EXITING",
        }
        self.state = transitions.get(self.state, "EXITING")

        if self.state == "EXITING":
            # Remove agent from the grid and schedule when exiting
            self.model.grid.remove_agent(self)
            self.model.schedule.remove(self)

    def reconstruct_path(self, came_from, current):
        total_path = [current]
        while current in came_from:
            current = came_from[current]
            total_path.append(current)
        return total_path[::-1]  # Return reversed path

    def a_star_pathfinding(self, start, goal):
        open_set = {start}
        came_from = {}
        g_score = {(coords[1][0], coords[1][1]): float('inf') for coords in self.model.grid.coord_iter()}
        g_score[start] = 0
        f_score = {(coords[1][0], coords[1][1]): float('inf') for coords in self.model.grid.coord_iter()}
        f_score[start] = manhattan_distance(start, goal)

        while open_set:
            current = min(open_set, key=lambda pos: f_score[pos])
            
            if current == goal:
                return self.reconstruct_path(came_from, current)

            open_set.remove(current)
            for neighbor in self.model.grid.get_neighborhood(current, moore=False, include_center=False):
                if not any(isinstance(obj, StaticAgent) and obj.type == CellType.WALL for obj in self.model.grid.get_cell_list_contents([neighbor])):
                    tentative_g_score = g_score[current] + 1

                    if tentative_g_score < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g_score
                        f_score[neighbor] = g_score[neighbor] + manhattan_distance(neighbor, goal)
                        if neighbor not in open_set:
                            open_set.add(neighbor)

        return []


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


    
class StaticAgent(Agent):
 
    def __init__(self, unique_id, model, pos_x, pos_y, agent_type, content=None):
        super().__init__(unique_id, model)
        self.x = pos_x
        self.y = pos_y
        self.type = agent_type
        # Determine content based on agent type
        if agent_type == "EMPTY_TRAY":
            self.content = "EMPTY"
        elif "Tray" in agent_type:
            self.content = agent_type.split('_')[0]
        else:
            self.content = None


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


    def nearest(self, agent, target_type):
            x, y = agent.pos
            target_coords = [(i, j) for i, row in enumerate(self.model.external_grid)
                            for j, cell in enumerate(row) if cell == target_type]
            return min(target_coords, key=lambda pos: manhattan_distance((x, y), pos))

    