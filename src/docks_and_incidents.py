import numpy as np
import pandas as pd
import math

# CONSTANTS
# Drone speed and response time are constant values
DRONE_SPEED = 35.8 # 35.8 miles/hour = 16 meters/s data from https://www.skydio.com/x10/technical-specs
RESPONSE_TIME = 0.033 # 0.033 hours = 2 minutes target response time

METROSAFE_DOCK_LOCATIONS = [
    "1510 South 6th Street",
    "1525 Winter Avenue",
    "2620 Frankfort Avenue",
    "2900 Hikes Lane",
    "3228 River Park Drive",
    "3511 Fincastle Road",
    "4535 Manslick Road",
    "601 West Chestnut Street",
]

class Dock:
    def __init__(self, name, latitude, longitude, drone_speed, response_time):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.drone_speed = drone_speed
        self.response_time = response_time
        self.effective_radius = self.drone_speed * self.response_time # miles

    def incidents_covered(self, incidents):
        covered_incidents = []
        total_distance_to_covered_incidents = 0.0
        for incident in incidents:
            if coverage(self, incident):
                covered_incidents.append(incident)
                total_distance_to_covered_incidents += distance(self, incident)
        return covered_incidents, total_distance_to_covered_incidents

class Incident:
    def __init__(self, incident_id, latitude, longitude, date):
        self.incident_id = incident_id
        self.latitude = latitude
        self.longitude = longitude
        self.date = date

    def covered_by(self, docks):
        covered_by = []
        for dock in docks:
            if coverage(dock, self):
                covered_by.append(dock)
        return covered_by

def distance(dock, incident):
    delta_latitude_miles = np.abs(incident.latitude - dock.latitude) * 69
    mean_latitude = (incident.latitude + dock.latitude) / 2
    delta_longitude_miles = np.abs(incident.longitude - dock.longitude) * math.cos(mean_latitude) * 69
    return np.sqrt(delta_latitude_miles**2 + delta_longitude_miles**2)

# Returns True if the incident is within the effective radius of the dock, False otherwise
def coverage(dock, incident):
    return distance(dock, incident) <= dock.effective_radius

# Create docks and incidents objects from data
def get_docks(excel_file_path):
    docks = []
    docks_data = pd.read_excel(excel_file_path)
    for index, row in docks_data.iterrows():
        dock = Dock(row['name'], row['latitude'], row['longitude'], DRONE_SPEED, RESPONSE_TIME)
        docks.append(dock)
    print(f"Docks created: {len(docks)}")
    return docks

def get_incidents(excel_file_path):
    incidents = []
    incidents_data = pd.read_excel(excel_file_path)
    for index, row in incidents_data.iterrows():
        incident = Incident(row['incident_number'], row['latitude'], row['longitude'], row['date'])
        incidents.append(incident)
    print(f"Incidents created: {len(incidents)}")
    return incidents


def create_docks_and_incidents(docks_excel_file_path, incidents_excel_file_path):
    print("Creating docks and incidents...")
    docks = get_docks(docks_excel_file_path)
    incidents = get_incidents(incidents_excel_file_path)
    return docks, incidents
