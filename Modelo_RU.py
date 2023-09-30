from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
from random import choice
from mapa.mapa_RU import GridConfig, CellType


class StudentAgent(Agent):
    def __init__(self, unique_id, model, x, y):
        super().__init__(unique_id, model)
        self.pos = (x, y)
        self.state = "QUEUEING_TURNSTILE"
        self.blocked_steps = 0
        self.waiting_time = 0

    def nearest_tray(self):
        x, y = self.pos
        tray_coords = [(i, j) for i, row in enumerate(external_grid)
                   for j, cell in enumerate(row) if cell == CellType.TRAY]
        min_distance = float('inf')
        nearest = None

        for tray in tray_coords:
            if self.model.grid.is_cell_empty(tray):
                distance = abs(tray[0] - x) + abs(tray[1] - y)
                if distance < min_distance:
                    min_distance = distance
                    nearest = tray
                    if min_distance == 1:  # Se a bandeja mais próxima for adjacente, retorne
                        break

        return nearest

    def is_empty_or_catraca(self, x, y):
        cell_contents = self.model.grid.get_cell_list_contents([(x, y)])
        # Verificar se o conteúdo da célula é StaticAgent e não é uma parede
        return all(isinstance(agent, StaticAgent) and agent.type != "Parede" for agent in cell_contents) and not any(isinstance(agent, StudentAgent) for agent in cell_contents)

    def move_towards_target(self, target):
        x, y = self.pos
        tx, ty = target
        possible_steps = []

        if x < tx and self.is_empty_or_catraca(x + 1, y):
            possible_steps.append((x + 1, y))
        elif x > tx and self.is_empty_or_catraca(x - 1, y):
            possible_steps.append((x - 1, y))

        if y < ty and self.is_empty_or_catraca(x, y + 1):
            possible_steps.append((x, y + 1))
        elif y > ty and self.is_empty_or_catraca(x, y - 1):
            possible_steps.append((x, y - 1))

        return possible_steps

    def move(self):
        x, y = self.pos
        possible_steps = []

        # Se estiver na fila para a catraca
        if self.state == "QUEUEING_TURNSTILE":
            # Tente se mover horizontalmente em direção à catraca
            possible_steps = self.move_towards_target(
                (self.model.width - 1, y))
            if not possible_steps:  # Se não puder se mover horizontalmente, tente verticalmente
                if y > 0 and self.is_empty_or_catraca(x, y - 1):
                    possible_steps.append((x, y - 1))
                elif y < self.model.height - 1 and self.is_empty_or_catraca(x, y + 1):
                    possible_steps.append((x, y + 1))

            if x == self.model.width - 2 and self.is_empty_or_catraca(x + 1, y):
                self.state = "SEARCHING_TRAY"

        # Se estiver procurando uma bandeja
        elif self.state == "SEARCHING_TRAY":
            nearest = self.nearest_tray()
            if not nearest:
                self.state = "EXITING"
            else:
                if (x, y) == nearest:
                    if self.waiting_time < 2:
                        self.waiting_time += 1
                        return
                    else:
                        self.waiting_time = 0
                        self.state = "EXITING"
                else:
                    possible_steps = self.move_towards_target(nearest)

        # Se estiver saindo
        elif self.state == "EXITING":
            if y < self.model.height - 1 and self.is_empty_or_catraca(x, y + 1):
                possible_steps.append((x, y + 1))
            else:
                self.model.grid.remove_agent(self)
                return

        # Escolha um dos possíveis passos
        new_position = choice(possible_steps) if possible_steps else None
        if new_position:
            self.model.grid.move_agent(self, new_position)
            self.blocked_steps = 0
        else:
            self.blocked_steps += 1

    def step(self):
        self.move()


class StaticAgent(Agent):
    def __init__(self, unique_id, model, x, y, agent_type):
        super().__init__(unique_id, model)
        self.pos = (x, y)
        self.type = agent_type


def agent_portrayal(agent):
    if isinstance(agent, StudentAgent):
        color = "red" if agent.model.error_message else "blue"
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



class RestaurantModel(Model):
    def __init__(self, external_grid):
        self.height = len(external_grid)
        self.width = len(external_grid[0])

        self.grid = MultiGrid(self.width, self.height, True)
        self.schedule = RandomActivation(self)
        self.time = 0

        self.error_message = None

        for y in range(self.height):
            for x in range(self.width):
                cell_value = external_grid[y][x]
                if cell_value == CellType.STUDENT:
                    student = StudentAgent((x, y), self, x, y)
                    self.grid.place_agent(student, (x, y))
                    self.schedule.add(student)
                elif cell_value in [CellType.TURNSTILE, CellType.WALL, CellType.TRAY, CellType.EXIT]:
                    agent_type = {
                        CellType.TURNSTILE: 'Catraca',
                        CellType.WALL: 'Parede',
                        CellType.TRAY: 'Bandeja',
                        CellType.EXIT: 'Saida'
                    }[cell_value]
                    self.grid.place_agent(StaticAgent(
                        (x, y), self, x, y, agent_type), (x, y))

    def step(self):
        if self.error_message:
            return
        # Chamar o .step() uma vez apenas
        self.schedule.step()

        all_students_blocked = all(
            [student.blocked_steps >= 10 for student in self.schedule.agents if isinstance(student, StudentAgent)])
        if all_students_blocked:
            self.error_message = "Erro, todos os estudantes presos, modelo parado"


external_grid = GridConfig.get_grid()

# Defina o tamanho do grid de acordo com external_grid
grid = CanvasGrid(agent_portrayal, len(
    external_grid[0]), len(external_grid), 600, 1500)

# Modifique os parâmetros para se ajustar ao tamanho de external_grid
server = ModularServer(RestaurantModel, [grid], "University Restaurant Model", {
                       "external_grid": external_grid})
server.launch()
