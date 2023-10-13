from constants import *
import pandas as pd

DATAFRAME = pd.read_csv('../logentrada.csv')

def manhattan_distance(pos1, pos2):
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


   