# Modelo do Restaurante Universitario

## Luan Reis e Arthur

 ### Definição de Parâmetros e Ambiente

#- **Entradas**: 2 conjuntos de 2 catracas cada
#- **Bandejas**: Cada entrada leva a 3 bandejas diferentes
#- **Refeições**: Desjejum, Almoço, Jantar
#- **Objetivo**: Reduzir filas e lotação no restaurante universitário

from mesa.visualization.ModularVisualization import ModularServer
from model import RestaurantModel, ModelText, agent_portrayal
from mapa.mapa_RU import GridConfig
from mesa.visualization.modules import CanvasGrid, TextElement

if __name__ == "__main__":
    external_grid = GridConfig.get_grid()
    model_text = ModelText()
    # Adjusting grid dimensions for better visualization
    grid = CanvasGrid(agent_portrayal, len(external_grid[0]), len(external_grid), 800, 1600)
    server = ModularServer(RestaurantModel, [grid, model_text], "University Restaurant Model", {"external_grid": external_grid})
    server.launch()