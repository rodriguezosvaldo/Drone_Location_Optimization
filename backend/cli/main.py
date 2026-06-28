import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

from src.docks_and_incidents import create_docks_and_incidents, specific_area_docks_and_incidents
from src.optimization_model import maximize_incidents_covered, minimize_docks_used
from visualizations.map_incidents_and_docks import create_map

DOCKS_EXCEL_FILE_PATH = str(PROJECT_ROOT / "output" / "docks_JCPS_MetroSafe.xlsx")
INCIDENTS_EXCEL_FILE_PATH = str(PROJECT_ROOT / "output" / "clean_and_geocoded_LMPD_data_2025.xlsx")



def optimization_menu(docks, incidents_in_one_day):
    while True:
        print("\n                    Optimization Menu")
        print("---------------------------------------------------")
        print("1. Maximize the number of incidents covered")
        print("2. Maximize the number of incidents covered by specific docks")
        print("---------------------------------------------------")
        print("3. Maximize the number of incidents covered increasing budget")
        print("4. Maximize the number of incidents covered by specific docks increasing budget")
        print("---------------------------------------------------")
        print("0. Exit")
        print("---------------------------------------------------")
        choice = input("\nEnter your choice: ")

        if choice == "1":
            dock_locations_quantity = int(input("Enter the number of dock locations available (Budget constraint): ")) # Budget constraint
            maximize_incidents_covered(docks, incidents_in_one_day, dock_locations_quantity)      
        
        elif choice == "0":
            break
        else:
            print("Invalid choice")
            continue

def menu():
    # Create all docks and incidents in the data
    docks, incidents, incidents_in_one_day = create_docks_and_incidents(DOCKS_EXCEL_FILE_PATH, INCIDENTS_EXCEL_FILE_PATH)

    while True:
        print("\n                    Main Menu")
        print("---------------------------------------------------")
        print("1. Analize the entire area")
        print("2. Analize a specific area")
        print("0. Exit")
        print("---------------------------------------------------")
        choice = input("\nEnter your choice: ")
        if choice == "1":
            covered_incidents = []
            for incident in incidents:
                if incident.covered_by(docks):
                    covered_incidents.append(incident)
            create_map(docks, incidents, "docks_and_incidents_map", covered_incidents)
            optimization_menu(docks, incidents_in_one_day)
        elif choice == "2":
            specific_area_docks, specific_area_incidents = specific_area_docks_and_incidents(docks, incidents_in_one_day)
            covered_incidents = []
            for incident in specific_area_incidents:
                if incident.covered_by(specific_area_docks):
                    covered_incidents.append(incident)
            create_map(specific_area_docks, specific_area_incidents, "docks_and_incidents_map", covered_incidents)
            optimization_menu(specific_area_docks, specific_area_incidents)
        elif choice == "0":
            break
        else:
            print("Invalid choice")
            continue
        


            

    


if __name__ == "__main__":
    menu()
