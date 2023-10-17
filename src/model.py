


from mesa import Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.visualization.modules import  TextElement
from mesa.datacollection import DataCollector

from mapa.mapa_RU import  CellType
from constants import *
from agents import StudentAgent, Pathfinding, StaticAgent
from utilities import MovementUtils



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
        CellType.EXIT: 'Saida',
        CellType.JUICE: 'Suco',
        CellType.SPICES: 'Tempero',
        CellType.DESSERT: 'Sobremesa',
        CellType.TABLE: 'Mesa',
    }

    def __init__(self, external_grid):
        self.height = len(external_grid)
        self.width = len(external_grid[0])
        self.external_grid = external_grid
        self.movement_utils = MovementUtils(self)
        self.pathfinding = Pathfinding(self, self.movement_utils)
        self.steps_since_last_student = 0
        self.datacollector = DataCollector({
            "Average_Waiting_Time": lambda m: sum([agent.waiting_time for agent in m.schedule.agents if isinstance(agent, StudentAgent)]) / (len([agent for agent in m.schedule.agents if isinstance(agent, StudentAgent)]) or 1)
        })

        self.grid = MultiGrid(self.width, self.height, True)
        self.schedule = RandomActivation(self)
        self.time = 0
        self.error_message = None
        self.next_id = 0

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
        print("Método step foi chamado!")
        
        # Se houver uma mensagem de erro, interrompa a simulação.
        if self.error_message:
            print(self.error_message)
            return

        self.time += 1
        self.schedule.step()

        # No primeiro step ou a cada 8 steps, adicione um estudante.
        if self.time == 1 or self.time % 8 == 0:
            self.add_new_student()

        self.datacollector.collect(self)
    
        # Verifique se todos os estudantes estão bloqueados.
        all_students_blocked = all([student.blocked_steps >= MAX_BLOCKED_STEPS for student in self.schedule.agents if isinstance(student, StudentAgent)])
        if all_students_blocked:
            self.error_message = "Erro, todos os estudantes presos, modelo parado"
            print(self.error_message)
            return

        # Se não houver mais nenhum StudentAgent, pare a simulação.
        if not any(isinstance(agent, StudentAgent) for agent in self.schedule.agents):
            self.running = False

    def get_next_id(self):
        self.next_id += 1
        return self.next_id

    def add_new_student(self):
            print("Tentando adicionar novo estudante...")
            turnstile_coords = [(0, 0), (0, 1),(61,0),(61,1)]  # Coordenadas das catracas
            entry_coords = [(1, 0), (1, 1),(60,0),(60,1) ]  # Coordenadas à direita das catracas
          
            # Escolhe uma entrada aleatória das disponíveis
            chosen_entry = self.random.choice(entry_coords)

            # Verifica se a entrada escolhida está vazia
            if not self.grid.get_cell_list_contents([chosen_entry]):
                print(f"Adicionando estudante em {chosen_entry}...")
                student_id = self.get_next_id()
                student = StudentAgent(student_id, self, *chosen_entry)
                self.grid.place_agent(student, chosen_entry)
                self.schedule.add(student)


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
            "Catraca": "gray",
            "Parede": "black",
            "Bandeja": "green",  # Default color, but can be overridden below
            "Saida": "red",
            "Suco": "blue",
            "Tempero": "purple",
            "Sobremesa": "gold",
            "Mesa": "#766c6a",
        }

        # Override the color for trays based on content and portions.
        if agent.type == "Bandeja":
            if agent.content == "vegan":
                shape_colors["Bandeja"] = "lightgreen"
            elif agent.content == "meat":
                shape_colors["Bandeja"] = "brown"
            if agent.portions == 0:
                shape_colors["Bandeja"] = "red"

        return {
            "Shape": "rect",
            "Color": shape_colors.get(agent.type, "white"),
            "Filled": "true",
            "Layer": 1,
            "w": 1,
            "h": 1
        }






