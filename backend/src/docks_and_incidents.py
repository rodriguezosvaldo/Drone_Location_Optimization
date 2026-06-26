import numpy as np
import pandas as pd
import math
from collections import defaultdict
from datetime import date

# CONSTANTS
# Drone speed and response time are constant values
DRONE_SPEED = 35.8 # 35.8 miles/hour data from https://www.skydio.com/x10/technical-specs
RESPONSE_TIME = 0.033 # 0.033 hours = 2 minutes target response time
MAX_MISSION_TIME = 1800 # 1800 seconds = 30 minutes (https://www.skydio.com/x10/technical-specs gives 40 minutes in ideal conditions)
BATTERY_RECHARGE_TIME = 3600 # 3600 seconds = 1 hour (https://www.skydio.com/x10/technical-specs using charger 230W)
CICLE_TIME = MAX_MISSION_TIME + BATTERY_RECHARGE_TIME # 1800 + 3600 = 5400 seconds = 90 minutes
DRONE_DISPOSITION_TIME = 57600 # 57600 seconds = 16 hours (Two shifts of 8 hours each)
DRONE_COVERAGE_CAPACITY = int(DRONE_DISPOSITION_TIME / CICLE_TIME) # 57600 / 5400 = 10.66 = 10 incidents per day

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
    def __init__(self, name, latitude, longitude):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.drone_speed = DRONE_SPEED
        self.response_time = RESPONSE_TIME
        self.drone_coverage_capacity = DRONE_COVERAGE_CAPACITY
        self.dock_weight = 1
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
    delta_longitude_miles = np.abs(incident.longitude - dock.longitude) * math.cos(math.radians(mean_latitude)) * 69
    return np.sqrt(delta_latitude_miles**2 + delta_longitude_miles**2)

# Returns True if the incident is within the effective radius of the dock, False otherwise
def coverage(dock, incident):
    return distance(dock, incident) <= dock.effective_radius

def specific_area_docks_and_incidents(docks, incidents):
    all_docks_latitudes = [d.latitude for d in docks]
    all_docks_longitudes = [d.longitude for d in docks]
    effective_radius = max(d.effective_radius for d in docks)
    effective_radius_degrees = effective_radius * 69 # miles to degrees

    latitude_closest_to_ecuador = min(abs(lat) for lat in all_docks_latitudes) - effective_radius_degrees
    latitude_farthest_from_ecuador = max(abs(lat) for lat in all_docks_latitudes) + effective_radius_degrees
    longitude_closest_to_greenwich = min(abs(lon) for lon in all_docks_longitudes) - effective_radius_degrees
    longitude_farthest_from_greenwich = max(abs(lon) for lon in all_docks_longitudes) + effective_radius_degrees

    specific_area_docks = [dock for dock in docks if dock.latitude >= latitude_closest_to_ecuador and dock.latitude <= latitude_farthest_from_ecuador and dock.longitude >= longitude_closest_to_greenwich and dock.longitude <= longitude_farthest_from_greenwich]
    specific_area_incidents = [incident for incident in incidents if incident.latitude >= latitude_closest_to_ecuador and incident.latitude <= latitude_farthest_from_ecuador and incident.longitude >= longitude_closest_to_greenwich and incident.longitude <= longitude_farthest_from_greenwich]

    return specific_area_docks, specific_area_incidents

# Create docks and incidents objects from data
def get_docks(excel_file_path):
    docks = []
    docks_data = pd.read_excel(excel_file_path)
    for index, row in docks_data.iterrows():
        dock = Dock(row['name'], row['latitude'], row['longitude'])
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

def _incident_date(incident):
    """Normalize incident.date to a datetime.date."""
    value = incident.date
    if isinstance(value, date) and not hasattr(value, "hour"):
        return value
    if hasattr(value, "date"):
        return value.date()
    return pd.to_datetime(value).date()

def get_incidents_by_date(incidents):
    """Group incidents by month and representative days (max, mean, min daily counts).

    Returns a dict keyed by month (1-12). Each month maps dates to incident lists:
    - date(s) with the highest daily count that month
    - date(s) whose daily count is closest to the monthly mean
    - date(s) with the lowest daily count that month
    """
    incidents_by_date = defaultdict(list)
    for incident in incidents:
        incidents_by_date[_incident_date(incident)].append(incident)

    incidents_by_month = {}
    for month in range(1, 13):
        month_incidents_by_date = {
            day: day_incidents
            for day, day_incidents in incidents_by_date.items()
            if day.month == month
        }
        if not month_incidents_by_date:
            incidents_by_month[month] = {}
            continue

        daily_counts = {
            day: len(day_incidents)
            for day, day_incidents in month_incidents_by_date.items()
        }
        max_count = max(daily_counts.values())
        min_count = min(daily_counts.values())
        mean_count = sum(daily_counts.values()) / len(daily_counts)

        max_dates = [day for day, count in daily_counts.items() if count == max_count]
        min_dates = [day for day, count in daily_counts.items() if count == min_count]
        mean_distance = min(abs(count - mean_count) for count in daily_counts.values())
        mean_dates = [
            day
            for day, count in daily_counts.items()
            if abs(count - mean_count) == mean_distance
        ]

        representative_dates = {
            min(max_dates),
            min(mean_dates),
            min(min_dates),
        }

        incidents_by_month[month] = {
            day: month_incidents_by_date[day] for day in sorted(representative_dates)
        }

    return incidents_by_month

def create_docks_and_incidents(docks_excel_file_path, incidents_excel_file_path):
    print("Creating docks and incidents...")
    docks = get_docks(docks_excel_file_path)
    incidents = get_incidents(incidents_excel_file_path)
    incidents_by_month = get_incidents_by_date(incidents)

    return docks, incidents, incidents_by_month
