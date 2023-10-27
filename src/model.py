from mesa import Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.visualization.modules import TextElement
from mesa.datacollection import DataCollector

from datetime import datetime

from mapa.mapa_RU import CellType
from constants import *
from agents import StudentAgent, StaticAgent, MovementUtils


class ModelText(TextElement):
    def __init__(self):
        pass

    def render(self, model):
        student_agents = [agent for agent in model.schedule.agents if isinstance(agent, StudentAgent)]
        avg_waiting_time = sum(agent.waiting_time for agent in student_agents) / len(student_agents) if student_agents else 0
        return f"Current Hour: {model.get_human_readable_time()} | Average Waiting Time: {avg_waiting_time}"

class RestaurantModel(Model):
    AGENT_TYPE_MAPPING = {
        CellType.TURNSTILE: 'Turnstile',
        CellType.WALL: 'Wall',
        CellType.EXIT: 'Exit',
        CellType.JUICE: 'Juice',
        CellType.SPICES: 'Spices',
        CellType.DESSERT: 'Dessert',
        CellType.TABLE: 'Table',
        CellType.EMPTY_TRAY: 'Empty_tray',
        CellType.RICE_TRAY: 'Rice_tray',
        CellType.BROWN_RICE_TRAY: 'Brown_Rice_Tray',
        CellType.BEANS_TRAY: 'Beans_Tray',
        CellType.GUARN_TRAY: 'Guarn_Tray',
        CellType.VEG_TRAY: 'Veg_Tray',
        CellType.MEAT_TRAY: 'Meat_Tray',
        CellType.SAL_TRAY: 'Sal_Tray',
        CellType.TALHER_TRAY: 'Talher_Tray',
    }

    def __init__(self, external_grid, day, meal, hour, filtered_df):        
        self.height = len(external_grid)
        self.width = len(external_grid[0])
        self.external_grid = external_grid
        self.movement_utils = MovementUtils(self)
        self.steps_since_last_student = 0
        self.datacollector = DataCollector({
            "Average_Waiting_Time": lambda m: sum([agent.waiting_time for agent in m.schedule.agents if isinstance(agent, StudentAgent)]) / (len([agent for agent in m.schedule.agents if isinstance(agent, StudentAgent)]) or 1)
        })

        self.grid = MultiGrid(self.width, self.height, True)
        self.schedule = RandomActivation(self)
        self.day = day
        self.meal = meal
        self.hour = int(hour.split(":")[0]) * 3600  # Convert to seconds
        self.time = self.hour
        self.error_message = None
        self.next_id = 0
        self.filtered_df = filtered_df
        self.locations_cache = {
            'empty_trays': self.find_cell_positions(CellType.EMPTY_TRAY),
            'rice_trays': self.find_cell_positions(CellType.RICE_TRAY),
            'brown_rice_trays': self.find_cell_positions(CellType.BROWN_RICE_TRAY),
            'beans_trays': self.find_cell_positions(CellType.BEANS_TRAY),
            'guarn_trays': self.find_cell_positions(CellType.GUARN_TRAY),
            'veg_trays': self.find_cell_positions(CellType.VEG_TRAY),
            'meat_trays': self.find_cell_positions(CellType.MEAT_TRAY),
            'sal_trays': self.find_cell_positions(CellType.SAL_TRAY),
            'talher_trays': self.find_cell_positions(CellType.TALHER_TRAY),
            'juices': self.find_cell_positions(CellType.JUICE),
            'spices': self.find_cell_positions(CellType.SPICES),
            'desserts': self.find_cell_positions(CellType.DESSERT),
            'tables': self.find_cell_positions(CellType.TABLE),
            'exits': self.find_cell_positions(CellType.EXIT)
        }
        
        for y, row in enumerate(external_grid):
            for x, cell_value in enumerate(row):
                if cell_value in self.AGENT_TYPE_MAPPING:
                    agent_type = self.AGENT_TYPE_MAPPING[cell_value]
                    agent = StaticAgent((x, y), self, x, y, agent_type)
                    self.grid.place_agent(agent, (x, y))

    def step(self):
        """Defines the action taken in each time step of the simulation."""
        current_time = self.get_human_readable_time()
        print(f"Step method called! Current time: {current_time}")


        # If there is an error message, stop the simulation.
        if self.error_message:
            print(self.error_message)
            return

        self.time += 1
        self.schedule.step()

        # Add a new student on the first step or every 8 steps.
        matching_rows = self.filtered_df[self.filtered_df['seconds_from_start'] == self.time]
        for _, row in matching_rows.iterrows():
         self.add_new_student(catraca_id=row['IDCatraca'])

        self.datacollector.collect(self)
        '''
        # Check if all students are blocked.
        all_students_blocked = all([student.blocked_steps >= MAX_BLOCKED_STEPS for student in self.schedule.agents if isinstance(student, StudentAgent)])
        if all_students_blocked:
            self.error_message = "Error, all students blocked, model stopped"
            print(self.error_message)
            return
    
        # If there are no more StudentAgents, stop the simulation.
        if not any(isinstance(agent, StudentAgent) for agent in self.schedule.agents):
            self.running = False
        '''
    def get_next_id(self):
        self.next_id += 1
        return self.next_id

    def find_cell_positions(self, cell_type):
        return [(i, j) for i, row in enumerate(self.external_grid)
                for j, cell in enumerate(row) if cell == cell_type]

    def update_cache(self, cell_type):
        """To be called whenever there's a change in a specific type of cell."""
        self.locations_cache[cell_type] = self.find_cell_positions(cell_type)


    def get_human_readable_time(self):
        hours = self.time // 3600
        minutes = (self.time % 3600) // 60
        seconds = self.time % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"


    def add_new_student(self, catraca_id):


        catraca_mapping = {1: (1, 2), 2: (1, 5), 3: (82, 5), 4: (82, 2)}
        entry_coords = [(1, 2), (1, 5), (82, 5), (82, 2)]

        chosen_entry = catraca_mapping.get(catraca_id)
        if not chosen_entry:
            print(f"Warning: Catraca ID {catraca_id} not found in mapping. Choosing random entry.")
            chosen_entry = self.random.choice(entry_coords)


        # Check if the chosen entry is empty
        if not self.grid.get_cell_list_contents([chosen_entry]):
            print(f"Adding student at {chosen_entry}...")
            student_id = self.get_next_id()
            student = StudentAgent(student_id, self, *chosen_entry)
            self.grid.place_agent(student, chosen_entry)
            self.schedule.add(student)
        
        
        print(f"Trying to add a new student at {chosen_entry}")

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
    else:  # This covers all other types of agents, including trays.
         tray_colors = {
        "Rice": "pink",
        "Brown": "brown",
        "Beans": "black",
        "Guarn": "blue",
        "Veg": "purple",
        "Meat": "red",
        "Sal": "yellow",
        "Talher": "orange",
        "EMPTY": "green"
    }
    shape_colors = {
        "Turnstile": "gray",
        "Wall": "black",
        "Exit": "red",
        "Juice": "blue",
        "Spices": "purple",
        "Dessert": "gold",
        "Table": "#766c6a",
        "EMPTY_TRAY": tray_colors["EMPTY"]  # This line ensures that empty trays get the green color
    }

    # Assigning color for trays based on their content
    if "Tray" in agent.type and agent.content:
        return {
            "Shape": "rect",
            "Color": tray_colors.get(agent.content, "green"),
            "Filled": "true",
            "Layer": 1,
            "w": 1,
            "h": 1
        }

    # Assigning color for other static agents
    else:
        return {
            "Shape": "rect",
            "Color": shape_colors.get(agent.type, "green"),
            "Filled": "true",
            "Layer": 1,
            "w": 1,
            "h": 1
        }
