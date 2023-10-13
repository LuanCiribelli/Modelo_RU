


from mesa import Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.visualization.modules import  TextElement
from mesa.datacollection import DataCollector

from mapa.mapa_RU import  CellType
from constants import *
from agents import StudentAgent, MovementUtils, Pathfinding, StaticAgent




# 3. Modelo e Visualização

class ModelText(TextElement):
    def __init__(self):
        pass
    
    def render(self, model):
        student_agents = [agent for agent in model.schedule.agents if isinstance(agent, StudentAgent)]
        avg_waiting_time = sum(agent.waiting_time for agent in student_agents) / len(student_agents) if student_agents else 0
        return f"Passo atual: {model.time} | Tempo médio de espera: {avg_waiting_time}"




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





