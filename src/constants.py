import json

with open('../config.json', 'r') as f:
    config = json.load(f)

MAX_BLOCKED_STEPS = config["MAX_BLOCKED_STEPS"]
WAITING_TIME_THRESHOLD = config["WAITING_TIME_THRESHOLD"]
DISTANCE_THRESHOLD = config["DISTANCE_THRESHOLD"]
DEFAULT_TRAY_PORTIONS = config["DEFAULT_TRAY_PORTIONS"]
