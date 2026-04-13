from config import *
from travel_matrix import build_matrix, save_matrix



m, l = build_matrix(AP, ctx["start_address"], ctx["end_address"], "car")
save_matrix(m, l, "activities/seattle_matrix2.json")
