from mesa import Agent
from constants import DEFAULT_TRAY_PORTIONS, WAITING_TIME_THRESHOLD
from mapa.mapa_RU import CellType
import random

def manhattan_distance(pos1, pos2):
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


class StaticAgent(Agent):
    def __init__(self, unique_id, model, pos_x, pos_y, agent_type):
        super().__init__(unique_id, model)
        self.x = pos_x
        self.y = pos_y
        self.type = agent_type
        self.content = self._determine_content()

    def _determine_content(self):
        if self.type == "EMPTY_TRAY":
            return "EMPTY"
        elif "Tray" in self.type:
            self.food_count = DEFAULT_TRAY_PORTIONS
            return self.type.split('_')[0]
        else:
            return None

    def refill(self):
        if "Tray" in self.type:
            self.food_count = DEFAULT_TRAY_PORTIONS
            print(f"Refilled {self.type} at position {self.x}, {self.y}")


class StudentAgent(Agent):
    STATES = [
        "GOING_TO_RICE_TRAY", "GOING_TO_BROWN_RICE_TRAY", "GOING_TO_BEANS_TRAY",
        "GOING_TO_GUARN_TRAY", "GOING_TO_VEG_TRAY", "GOING_TO_MEAT_TRAY",
        "GOING_TO_SAL_TRAY", "GOING_TO_TALHER_TRAY", "GOING_TO_JUICE",
        "GOING_TO_SPICES", "GOING_TO_DESSERT", "GOING_TO_TABLE", "GOING_TO_EXIT"
    ]

    def __init__(self, unique_id, model, x, y):
        super().__init__(unique_id, model)
        self.pos = (x, y)
        self.state = "GOING_TO_RICE_TRAY"
        self.waiting_time = 0
        self.blocked_steps = 0
        self.visited_groups = set()
        self.current_goal = None
        self.current_path = None
        self.type = "Student"
        self._initialize_food_attributes()
        self._initialize_preferences() 

    def _initialize_preferences(self):
        # Diet preference
        rand_diet = random.uniform(0, 1)
        if rand_diet <= 0.08:
            self.diet = "vegan"
        elif 0.08 < rand_diet <= 0.98:
            self.diet = "meat_eater"
        else:
            self.diet = "no_meat_or_veg"

        # Rice preference
        rand_rice = random.uniform(0, 1)
        if rand_rice <= 0.95:
            self.rice_type = "rice"
        elif 0.95 < rand_rice <= 0.98:
            self.rice_type = "brown_rice"
        else:
            self.rice_type = "no_rice"

    def _initialize_food_attributes(self):
        self.got_rice = False
        self.got_beans = False
        self.got_meat = False
        self.got_salad = False
        self.got_talheres = False

    def move_towards(self, goal):
        if self.current_path and len(self.current_path) > 1:
            next_step = self.current_path[1]

            # Check if next step is not occupied by another agent
            if not any(isinstance(obj, (StudentAgent, StaticAgent)) for obj in self.model.grid.get_cell_list_contents([next_step])):
                self.model.grid.move_agent(self, next_step)
                self.blocked_steps = 0
                self.current_path.pop(0)  # Remove the step we just took
            else:
                self.blocked_steps += 1
                print(f"Agent {self.unique_id} is blocked.")
        else:
            self.current_path = self.a_star_pathfinding(self.pos, goal)
            print(
                f"Agent {self.unique_id} recalculating path: {self.current_path}")

            # If still no path is found, use collision avoidance
            if not self.current_path:
                print(f"Agent {self.unique_id} using collision avoidance.")
                possible_steps = [(self.pos[0] + dx, self.pos[1] + dy)
                                  for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]]
                possible_steps = [step for step in possible_steps if not any(isinstance(
                    obj, (StudentAgent, StaticAgent)) for obj in self.model.grid.get_cell_list_contents([step]))]
                next_step = min(possible_steps, key=lambda step: manhattan_distance(
                    step, goal), default=None)
                if next_step:
                    self.model.grid.move_agent(self, next_step)
                    self.blocked_steps = 0
                else:
                    self.blocked_steps += 1

    def determine_goal(self):
        tray_sequence = [
            {"state": "GOING_TO_RICE_TRAY", "skip_chance": self.get_rice_skip_chance()},
            {"state": "GOING_TO_BROWN_RICE_TRAY", "skip_chance": self.get_brown_rice_skip_chance()},
            {"state": "GOING_TO_BEANS_TRAY", "skip_chance": 0.5},  # 50% chance to skip
            {"state": "GOING_TO_GUARN_TRAY", "skip_chance": 0.5},
            {"state": "GOING_TO_VEG_TRAY", "skip_chance": self.get_veg_skip_chance()},
            {"state": "GOING_TO_MEAT_TRAY", "skip_chance": self.get_meat_skip_chance()},
            {"state": "GOING_TO_SAL_TRAY", "skip_chance": 0.5},
            {"state": "GOING_TO_TALHER_TRAY", "skip_chance": 0.0},  # 0% chance to skip as it's obligatory
        ]

        # Get the next state in the sequence
        for tray in tray_sequence:
            if self.state == tray["state"]:
                # Decide whether to skip based on random chance
                if random.random() < tray["skip_chance"]:
                    continue  # Skip to the next tray in sequence
                else:
                    tray_name = self.state.replace("GOING_TO_", "").lower()
                    return self._goal_for_tray(tray_name)
        
        # If state doesn't match any in sequence (or after completing the sequence)
        return self._goal_for_special_state()

    def get_rice_skip_chance(self):
        # Return chance to skip based on agent's rice preference
        if self.rice_type == "no_rice":
            return 1.0
        elif self.rice_type == "brown_rice":
            return 0.0  # As we'd rather have them go to the brown rice tray
        return 0.0  # Default: Don't skip

    def get_brown_rice_skip_chance(self):
        if self.rice_type == "no_rice":
            return 1.0
        elif self.rice_type == "rice":
            return 1.0  # If they prefer regular rice, skip brown rice
        return 0.0  # Default: Don't skip

    def get_veg_skip_chance(self):
        if self.diet == "vegan":
            return 0.0  # Vegans will always want veggies
        elif self.diet == "no_meat_or_veg":
            return 1.0  # Skip both meat and veg trays
        return 0.5  # Default: 50% chance to skip

    def get_meat_skip_chance(self):
        if self.diet == "vegan":
            return 1.0  # Vegans will skip meat
        elif self.diet == "no_meat_or_veg":
            return 1.0  # Skip both meat and veg trays
        return 0.0  # Default: Don't skip


    def _goal_for_tray(self, tray_name):
        tray_key = tray_name + "s"
        
        # Sort trays based on manhattan distance and queue length
        sorted_trays = sorted(
            self.model.locations_cache[tray_key], 
            key=lambda pos: (len(self.model.tray_queues[tray_key]), manhattan_distance(self.pos, pos))
        )
        
        # Get the top prioritized tray
        tray_pos = sorted_trays[0]
        self.join_queue(tray_key)

        # Check the cell above and below the tray
        above = (tray_pos[0], tray_pos[1] - 1)
        below = (tray_pos[0], tray_pos[1] + 1)

        # If the cell above is empty, return it as the goal
        if 0 <= above[1] < self.model.height and not any(isinstance(obj, (StudentAgent, StaticAgent)) for obj in self.model.grid.get_cell_list_contents([above])):
            return above

        # Otherwise, if the cell below is empty, return it as the goal
        elif 0 <= below[1] < self.model.height and not any(isinstance(obj, (StudentAgent, StaticAgent)) for obj in self.model.grid.get_cell_list_contents([below])):
            return below

        # Default: return the tray position if neither above nor below is available
        return tray_pos


    def _goal_for_special_state(self):
        specific_goals = {
            "GOING_TO_JUICE": self.get_adjacent_empty_cell(random.choice(self.model.locations_cache['juices'])), # Randomly select a juice            "GOING_TO_SPICES": self.get_adjacent_empty_cell(min(self.model.locations_cache['spices'], key=lambda pos: manhattan_distance(self.pos, pos)), directions=['left', 'right']),
            "GOING_TO_SPICES": self.get_adjacent_empty_cell(self.random.choice(self.model.locations_cache['spices'])),
            "GOING_TO_DESSERT": self.get_adjacent_empty_cell(min(self.model.locations_cache['desserts'], key=lambda pos: manhattan_distance(self.pos, pos)), directions=['above', 'right', 'left']),
            "GOING_TO_TABLE": self.get_adjacent_empty_cell(self.random.choice(self.model.locations_cache['tables'])),
            "GOING_TO_EXIT": self.get_adjacent_empty_cell(min(self.model.locations_cache['exits'], key=lambda pos: manhattan_distance(self.pos, pos)), directions=['left', 'right']),        }
        return specific_goals.get(self.state, self.pos)
 
    def get_adjacent_empty_cell(self, target_pos, directions=['above', 'below', 'left', 'right']):
        x, y = target_pos
        target_type = self._type_from_state()

        possible_directions = {
            'above': (x, y-1),
            'below': (x, y+1),
            'left': (x-1, y),
            'right': (x+1, y)
        }

        for direction, pos in possible_directions.items():
            if direction in directions and 0 <= pos[0] < self.model.width and 0 <= pos[1] < self.model.height:
                cell_contents = self.model.grid.get_cell_list_contents([pos])
                if not cell_contents or (len(cell_contents) == 1 and isinstance(cell_contents[0], StaticAgent) and cell_contents[0].type == target_type):
                    return pos

        return self.pos  # Default: return the agent's own position if no adjacent cell with the target type found

    def _type_from_state(self):
        return self.state.replace("GOING_TO_", "")

    def reached_goal(self, goal):
        # Verifique as células ao redor da posição atual para encontrar o item
        neighbors = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=False)
        item = None
        for neighbor in neighbors:
            contents = self.model.grid.get_cell_list_contents([neighbor])
            types = [getattr(agent, 'type', 'No type') for agent in contents]
            #print(f"Neighbor: {neighbor}, Contents: {contents}, Types: {types}")

            item_contents = self.model.grid.get_cell_list_contents([neighbor])
            
            # Add a condition for Exit type and state GOING_TO_EXIT
            if any(agent.type == "Exit" for agent in item_contents) and self.state == "GOING_TO_EXIT":
                self.model.grid.remove_agent(self)
                self.model.schedule.remove(self)
                self.model.num_students -= 1
                for queue in self.model.tray_queues.values():
                    if self in queue:
                        queue.remove(self)
                return  # Exit early as the agent is removed

            item = next((agent for agent in item_contents if hasattr(agent, "type") and agent.type in [
                        "Juice", "Dessert", "Spices", "Table"]), None)
            if item:
                break

        # Se item for None, verifique bandejas
        if not item:
            for neighbor in neighbors:
                tray_contents = self.model.grid.get_cell_list_contents([
                                                                       neighbor])
                item = next((agent for agent in tray_contents if hasattr(
                    agent, "type") and "Tray" in agent.type), None)
                if item:
                    break

        if not item:
            return  # Nenhum item ou bandeja encontrada perto do objetivo, saia cedo

        print(f"Agent {self.unique_id} encountered item type: {item.type} in state: {self.state}")

        if item.type == "Juice" and self.state == "GOING_TO_JUICE":
            self.state = "GOING_TO_SPICES"
        elif item.type == "Spices" and self.state == "GOING_TO_SPICES":
            self.state = "GOING_TO_DESSERT"
        elif item.type == "Dessert" and self.state == "GOING_TO_DESSERT":
            self.state = "GOING_TO_TABLE"
        elif item.type == "Table" and self.state == "GOING_TO_TABLE":
            self.state = "GOING_TO_EXIT"
        

        elif "Tray" in item.type:
            # Lógica ao alcançar a bandeja (Tray)
            # Se a bandeja estiver vazia, recarregue-a
            if item.food_count == 0:
                print(f"Agent {self.unique_id} waiting for refill.")
                item.refill()
                self.waiting_time += 1
                return  # Return after waiting for refill, so the agent tries to get food again in the next step

            # Se houver comida, diminua a contagem e atualize os atributos do agente
            item.food_count -= 1
            self.update_food_attributes()

            transitions = {
                "GOING_TO_RICE_TRAY": "GOING_TO_BROWN_RICE_TRAY",
                "GOING_TO_BROWN_RICE_TRAY": "GOING_TO_BEANS_TRAY",
                "GOING_TO_BEANS_TRAY": "GOING_TO_GUARN_TRAY",
                "GOING_TO_GUARN_TRAY": "GOING_TO_VEG_TRAY",
                "GOING_TO_VEG_TRAY": "GOING_TO_MEAT_TRAY",
                "GOING_TO_MEAT_TRAY": "GOING_TO_SAL_TRAY",
                "GOING_TO_SAL_TRAY": "GOING_TO_TALHER_TRAY",
                "GOING_TO_TALHER_TRAY": "GOING_TO_JUICE",
                "GOING_TO_JUICE": "GOING_TO_SPICES",
                "GOING_TO_SPICES": "GOING_TO_DESSERT",
                "GOING_TO_DESSERT": "GOING_TO_TABLE",
                "GOING_TO_TABLE": "GOING_TO_EXIT",
            }
            self.state = transitions.get(self.state, "GOING_TO_EXIT")
            print(f"Agent {self.unique_id} transitioned to state {self.state}")

            tray_queues = ["rice_trays", "brown_rice_trays", 'rice_trays', 'brown_rice_trays', 'beans_trays', 'guarn_trays', 'veg_trays',
                           'meat_trays', 'sal_trays', 'talher_trays']
            for tray_queue in tray_queues:
                if self in self.model.tray_queues[tray_queue]:
                    self.model.tray_queues[tray_queue].remove(self)

    def update_food_attributes(self):
        # This method updates the agent's attributes based on which tray they visited
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

    def join_queue(self, tray_type):
        queue = self.model.tray_queues[tray_type]
        if self not in queue:
            queue.append(self)

    def reconstruct_path(self, came_from, current):
        total_path = [current]
        while current in came_from:
            current = came_from[current]
            total_path.append(current)
        return total_path[::-1]  # Return reversed path

    def a_star_pathfinding(self, start, goal):
        open_set = {start}
        came_from = {}
        g_score = {(coords[1][0], coords[1][1]): float('inf')
                   for coords in self.model.grid.coord_iter()}
        g_score[start] = 0
        f_score = {(coords[1][0], coords[1][1]): float('inf')
                   for coords in self.model.grid.coord_iter()}
        f_score[start] = manhattan_distance(start, goal)

        while open_set:
            current = min(open_set, key=lambda pos: f_score[pos])
            # print(f"Current: {current}")
            if current == goal:
                return self.reconstruct_path(came_from, current)

            open_set.remove(current)
            for neighbor in self.model.grid.get_neighborhood(current, moore=False, include_center=False):
                # print(f"Checking neighbor: {neighbor}")  # Add this line to debug the neighbors under consideration
                if not any(isinstance(obj, StaticAgent) for obj in self.model.grid.get_cell_list_contents([neighbor])):
                    tentative_g_score = g_score[current] + 1

                    if tentative_g_score < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g_score
                        f_score[neighbor] = g_score[neighbor] + \
                            manhattan_distance(neighbor, goal)
                        if neighbor not in open_set:
                            open_set.add(neighbor)

        return []

    def step(self):

        # print(f"StudentAgent {self.unique_id} is in state {self.state} at position {self.pos}")

        if not self.current_goal or self.blocked_steps > WAITING_TIME_THRESHOLD:
            self.current_goal = self.determine_goal()
            self.current_path = self.a_star_pathfinding(
                self.pos, self.current_goal)
            self.blocked_steps = 0

        #print(f"Agent {self.unique_id} goal determined: {self.current_goal}")

        neighbors = self.model.grid.get_neighborhood(
            self.pos, moore=False, include_center=False)
        free_neighbors = [
            cell for cell in neighbors if not self.model.grid.is_cell_empty(cell)]

        if self.is_at_goal(self.current_goal):
            #print(f"Agent {self.unique_id} reached its goal at {self.current_goal}")
            self.reached_goal(self.current_goal)
            self.current_goal = None  # Reset the goal after reaching
            self.current_path = None
        else:
            self.move_towards(self.current_goal)

    def is_at_goal(self, goal):
        return self.pos == goal


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
