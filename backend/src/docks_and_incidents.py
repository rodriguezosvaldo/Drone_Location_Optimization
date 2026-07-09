import numpy as np
import pandas as pd
import math
from collections import defaultdict
from datetime import date

# CONSTANTS
# Drone speed and response time are constant values
DRONE_SPEED = 35.8 # 35.8 miles/hour data from https://www.skydio.com/x10/technical-specs
RESPONSE_TIME = 0.033 # 0.033 hours = 2 minutes target response time
RESPONSE_TIME_STEP_HOURS = 1 / 60  # 1 minute per iterative increase step
MAX_MISSION_TIME = 1800 # 1800 seconds = 30 minutes (https://www.skydio.com/x10/technical-specs gives 40 minutes in ideal conditions)
BATTERY_RECHARGE_TIME = 3600 # 3600 seconds = 1 hour (https://www.skydio.com/x10/technical-specs using charger 230W)
CYCLE_TIME = MAX_MISSION_TIME + BATTERY_RECHARGE_TIME # 1800 + 3600 = 5400 seconds = 90 minutes
DRONE_DISPOSITION_TIME = 57600 # 57600 seconds = 16 hours (Two shifts of 8 hours each)
DRONE_COVERAGE_CAPACITY = int(DRONE_DISPOSITION_TIME / CYCLE_TIME) # 57600 / 5400 = 10.66 = 10 incidents per day

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
        
    def change_drone_speed(self, new_drone_speed):
        self.drone_speed = new_drone_speed
        self.effective_radius = self.drone_speed * self.response_time
        return self.effective_radius

    def change_response_time(self, new_response_time):
        self.response_time = new_response_time
        self.effective_radius = self.drone_speed * self.response_time
        return self.effective_radius

    def change_drone_coverage_capacity(self, new_coverage_capacity):
        self.drone_coverage_capacity = new_coverage_capacity
        return self.drone_coverage_capacity

def clone_docks(docks, response_time=None, drone_speed=None, drone_coverage_capacity=None):
    """Return a new list of Dock objects, optionally overriding response time, drone speed, and coverage capacity."""
    cloned = []
    for dock in docks:
        new_dock = Dock(dock.name, dock.latitude, dock.longitude)
        capacity = (
            drone_coverage_capacity
            if drone_coverage_capacity is not None
            else dock.drone_coverage_capacity
        )
        new_dock.drone_coverage_capacity = capacity
        speed = drone_speed if drone_speed is not None else dock.drone_speed
        rt = response_time if response_time is not None else dock.response_time
        new_dock.drone_speed = speed
        new_dock.response_time = rt
        new_dock.effective_radius = speed * rt
        cloned.append(new_dock)
    return cloned

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

# Returns the docks and incidents within a specific area around the specific docks
def filter_priority_area(docks, incidents, priority_dock_names):
    EXTRA_DISTANCE_DEGREES = 0.014 # 0.014 degrees = 1 mile to get an area slightly larger than the effective radius
    priority_docks = []
    for dock in docks:
        if dock.name in priority_dock_names:
            priority_docks.append(dock)
    if not priority_docks:
        raise ValueError("No priority docks found in the loaded docks dataset")
    all_docks_latitudes = [d.latitude for d in priority_docks]
    all_docks_longitudes = [d.longitude for d in priority_docks]
    effective_radius = max(d.effective_radius for d in priority_docks)
    effective_radius_degrees = effective_radius / 69 # miles to degrees

    extra_distance = effective_radius_degrees + EXTRA_DISTANCE_DEGREES
    latitude_closest_to_ecuador = min(all_docks_latitudes) - extra_distance
    latitude_farthest_from_ecuador = max(all_docks_latitudes) + extra_distance
    longitude_closest_to_greenwich = min(all_docks_longitudes) - extra_distance
    longitude_farthest_from_greenwich = max(all_docks_longitudes) + extra_distance

    priority_area_docks = [
        dock
        for dock in docks
        if dock.latitude >= latitude_closest_to_ecuador
        and dock.latitude <= latitude_farthest_from_ecuador
        and dock.longitude >= longitude_closest_to_greenwich
        and dock.longitude <= longitude_farthest_from_greenwich
    ]
    priority_area_incidents = [
        incident
        for incident in incidents
        if incident.latitude >= latitude_closest_to_ecuador
        and incident.latitude <= latitude_farthest_from_ecuador
        and incident.longitude >= longitude_closest_to_greenwich
        and incident.longitude <= longitude_farthest_from_greenwich
    ]
    bounds = {
        "latitude_closest_to_ecuador": latitude_closest_to_ecuador,
        "latitude_farthest_from_ecuador": latitude_farthest_from_ecuador,
        "longitude_closest_to_greenwich": longitude_closest_to_greenwich,
        "longitude_farthest_from_greenwich": longitude_farthest_from_greenwich,
    }
    return priority_area_docks, priority_area_incidents, bounds


def specific_area_docks_and_incidents(docks, incidents, priority_dock_names):
    priority_area_docks, priority_area_incidents, bounds = filter_priority_area(
        docks,
        incidents,
        priority_dock_names,
    )
    priority_area_incidents_by_date = peak_day_incidents(priority_area_incidents)
    print(f"Priority area docks: {len(priority_area_docks)}")
    print(f"Priority area incidents: {len(priority_area_incidents_by_date)}")

    return (
        priority_area_docks,
        priority_area_incidents_by_date,
        bounds["latitude_closest_to_ecuador"],
        bounds["latitude_farthest_from_ecuador"],
        bounds["longitude_closest_to_greenwich"],
        bounds["longitude_farthest_from_greenwich"],
    )

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
        incident = Incident(row['name'], row['latitude'], row['longitude'], row['date'])
        incidents.append(incident)
    print(f"Incidents created: {len(incidents)}")
    return incidents

def get_priority_dock_names(excel_file_path):
    priority_docks_list = []
    priority_docks_data = pd.read_excel(excel_file_path)
    for index, row in priority_docks_data.iterrows():
        priority_docks_list.append(row['name'])
    print(f"Priority docks list created: {len(priority_docks_list)}")
    return priority_docks_list

def _incident_date(incident):
    """Normalize incident.date to a datetime.date."""
    value = incident.date
    if isinstance(value, date) and not hasattr(value, "hour"):
        return value
    if hasattr(value, "date"):
        return value.date()
    return pd.to_datetime(value).date()

def peak_day_incidents(incidents):
    """Return incidents that occurred on the busiest day within the given list."""
    if not incidents:
        return []

    incidents_by_date = defaultdict(list)
    for incident in incidents:
        incidents_by_date[_incident_date(incident)].append(incident)

    busiest_date = max(incidents_by_date, key=lambda day: len(incidents_by_date[day]))
    return incidents_by_date[busiest_date]


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

        # incidents_by_month has the following structure:
        # {
        #     1: {  # enero
        #         date(2024, 1, 3):  [Incident, Incident, ...],   # day with the minimum count
        #         date(2024, 1, 8):  [Incident, ...],             # day closest to the mean
        #         date(2024, 1, 15): [Incident, ...],             # day with the maximum count
        #     },
        #     2: { ... },  # february
        #     ...
        #     12: { ... }, # december
        # }
        incidents_by_month[month] = {
            day: month_incidents_by_date[day] for day in sorted(representative_dates)
        }
    
    # Day with the maximum number of incidents in the entire timeframe of the dataset
    incidents_in_one_day = peak_day_incidents(incidents)
    if incidents_in_one_day:
        busiest_date = _incident_date(incidents_in_one_day[0])
        print(f"Maximum number of incidents in one day: {len(incidents_in_one_day)}")
        print(f"Date maximum number of incidents: {busiest_date}")

    return incidents_in_one_day

def create_docks_and_incidents(
    docks_excel_file_path,
    incidents_excel_file_path,
    priority_docks_excel_file_path=None,
):
    print("Creating docks and incidents...")
    docks = get_docks(docks_excel_file_path)
    incidents = get_incidents(incidents_excel_file_path)
    incidents_in_one_day = get_incidents_by_date(incidents)
    if priority_docks_excel_file_path:
        priority_dock_names = get_priority_dock_names(priority_docks_excel_file_path)
    else:
        priority_dock_names = None

    return docks, incidents, incidents_in_one_day, priority_dock_names
