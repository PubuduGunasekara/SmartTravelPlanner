from config import *
from travel_matrix import build_matrix, save_matrix

m, l = build_matrix(AP, START_ADDRESS, END_ADDRESS, "car")
save_matrix(m, l, "activities/seattle_matrix2.json")
