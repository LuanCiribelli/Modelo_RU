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
from mesa.visualization.modules import CanvasGrid
from datetime import datetime
import pandas as pd 

DATAFRAME = pd.read_csv('../logentrada.csv')
# Convert 'Entrada' to datetime
DATAFRAME['Entrada'] = pd.to_datetime(DATAFRAME['Entrada'])

if __name__ == "__main__":
    external_grid = GridConfig.get_grid()
    model_text = ModelText()
    # Adjusting grid dimensions for better visualization

    # Get user input from the command line
    desired_day ='2023-01-05' #input("Enter the day (e.g., 2023-01-05): ")
    desired_meal ='Almoco' #input("Enter the meal (e.g., Almoco): ")
    desired_hour ='12:15' #input("Enter the hour (e.g., 12:00): ") 

    filtered_df = DATAFRAME[
        (DATAFRAME['Entrada'].dt.date == datetime.strptime(desired_day, '%Y-%m-%d').date()) & 
        (DATAFRAME['Refeicao'] == desired_meal)
    ].copy()
    filtered_df['seconds_from_start'] = filtered_df['Entrada'].dt.hour * 3600 + filtered_df['Entrada'].dt.minute * 60 + filtered_df['Entrada'].dt.second
    filtered_df = filtered_df.sort_values(by='seconds_from_start')

    grid = CanvasGrid(agent_portrayal, len(external_grid[0]), len(external_grid),600,600)
    model_cls = RestaurantModel
    server = ModularServer(model_cls, [grid, model_text], "University Restaurant Model", 
                       {"external_grid": external_grid, "day": desired_day, "meal": desired_meal, "hour": desired_hour, "filtered_df": filtered_df})

    server.launch()
