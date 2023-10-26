from mesa import Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.visualization.modules import TextElement
from mesa.datacollection import DataCollector

import pandas as pd
from datetime import datetime

from mapa.mapa_RU import CellType
from constants import *
from agents import StudentAgent, StaticAgent, MovementUtils


DATAFRAME = pd.read_csv('../logentrada.csv')

# Convert 'Entrada' to datetime
DATAFRAME['Entrada'] = pd.to_datetime(DATAFRAME['Entrada'])

# Filter for a specific day and "Almoço"
desired_date = '2023-01-05'
filtered_df = DATAFRAME[(DATAFRAME['Entrada'].dt.date == datetime.strptime(desired_date, '%Y-%m-%d').date()) & 
                        (DATAFRAME['Refeicao'] == 'Almoco')]

# Compute total seconds from the start of the day
filtered_df['seconds_from_start'] = filtered_df['Entrada'].dt.hour * 3600 + filtered_df['Entrada'].dt.minute * 60 + filtered_df['Entrada'].dt.second
filtered_df = filtered_df.sort_values(by='seconds_from_start')


class ModelText(TextElement):
    def __init__(self):
        pass

    def render(self, model):
        student_agents = [agent for agent in model.schedule.agents if isinstance(agent, StudentAgent)]
        avg_waiting_time = sum(agent.waiting_time for agent in student_agents) / len(student_agents) if student_agents else 0
        return f"Current Step: {model.time} | Average Waiting Time: {avg_waiting_time}"

class RestaurantModel(Model):
    AGENT_TYPE_MAPPING = {
        CellType.TURNSTILE: 'Turnstile',
        CellType.WALL: 'Wall',
        CellType.TRAY: 'Tray',
        CellType.EXIT: 'Exit',
        CellType.JUICE: 'Juice',
        CellType.SPICES: 'Spices',
        CellType.DESSERT: 'Dessert',
        CellType.TABLE: 'Table',
    }

    def __init__(self, external_grid):
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
        self.start_hour = 11  # Starting from 11:00:00
        self.time = self.start_hour * 3600  # Convert the starting hour to seconds
        self.error_message = None
        self.next_id = 0
        self.filtered_df = filtered_df
        self.locations_cache = {
            'trays': self.find_cell_positions(CellType.TRAY),
            'juices': self.find_cell_positions(CellType.JUICE),
            'spices': self.find_cell_positions(CellType.SPICES),
            'desserts': self.find_cell_positions(CellType.DESSERT),
            'tables': self.find_cell_positions(CellType.TABLE),
            'exits': self.find_cell_positions(CellType.EXIT)
        }

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
        shape_colors = {
            "Turnstile": "gray",
            "Wall": "black",
            "Tray": "green",  # Default color, but can be overridden below
            "Exit": "red",
            "Juice": "blue",
            "Spices": "purple",
            "Dessert": "gold",
            "Table": "#766c6a",
        }

        # Override the color for trays based on content and portions.
        if agent.type == "Tray":
            if agent.content == "vegan":
                shape_colors["Tray"] = "lightgreen"
            elif agent.content == "meat":
                shape_colors["Tray"] = "brown"
            if agent.portions == 0:
                shape_colors["Tray"] = "red"
 
        return {
            "Shape": "rect",
            "Color": shape_colors.get(agent.type, "white"),
            "Filled": "true",
            "Layer": 1,
            "w": 1,
            "h": 1
        }
