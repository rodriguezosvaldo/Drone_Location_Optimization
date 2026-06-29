import os
import sys
from pathlib import Path
import webbrowser

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

from src.docks_and_incidents import create_docks_and_incidents, specific_area_docks_and_incidents, METROSAFE_DOCK_LOCATIONS
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
        print("0. Exit")
        print("---------------------------------------------------")
        choice = input("\nEnter your choice: ")

        if choice == "1":
            dock_locations_quantity = int(input("Enter the number of dock locations available (Budget constraint): ")) # Budget constraint
            results = maximize_incidents_covered(docks, incidents_in_one_day, dock_locations_quantity)
            create_map(
                results["selected_docks"],
                incidents_in_one_day,
                f"optimized_map_{dock_locations_quantity}_docks",
                results["incidents_covered"],
                results["dock_assignments"],
            )
            map_file = Path(__file__).resolve().parent.parent.parent / "output" / f"optimized_map_{dock_locations_quantity}_docks.html"
            if map_file.exists():
                webbrowser.open(map_file.resolve().as_uri())

            dock_locations_quantity = results["k"]
            amount_incidents_covered = results["amount_incidents_covered"]
            increase_budget = input("Increase budget to cover 100% of incidents? (y/n): ")
            if increase_budget == "y":
                incidents_to_cover = len(incidents_in_one_day)
                while amount_incidents_covered < incidents_to_cover:
                    dock_locations_quantity += 1
                    results = maximize_incidents_covered(docks, incidents_in_one_day, dock_locations_quantity)
                    create_map(
                        results["selected_docks"],
                        incidents_in_one_day,
                        f"increase_budget_{dock_locations_quantity}_docks",
                        results["incidents_covered"],
                        results["dock_assignments"],
                    )
                    map_file = Path(__file__).resolve().parent.parent.parent / "output" / f"increase_budget_{dock_locations_quantity}_docks.html"
                    if map_file.exists():
                        webbrowser.open(map_file.resolve().as_uri())

                    dock_locations_quantity = results["k"]
                    if results["amount_incidents_covered"] == amount_incidents_covered:
                        break
                    amount_incidents_covered = results["amount_incidents_covered"]
            elif increase_budget == "n":
                continue
            else:
                print("Invalid choice")
                continue
        elif choice == "2":
            dock_locations_quantity = int(input("Enter the number of dock locations available (Budget constraint): ")) # Budget constraint
            specific_docks = [d for d in docks if d.name in METROSAFE_DOCK_LOCATIONS]
            results = maximize_incidents_covered(docks, incidents_in_one_day, dock_locations_quantity, specific_docks) 
            create_map(
                results["selected_docks"],
                incidents_in_one_day,
                f"specific_docks_optimized_map_{dock_locations_quantity}_docks",
                results["incidents_covered"],
                results["dock_assignments"],
            )
            map_file = Path(__file__).resolve().parent.parent.parent / "output" / f"specific_docks_optimized_map_{dock_locations_quantity}_docks.html"
            if map_file.exists():
                webbrowser.open(map_file.resolve().as_uri())   

            dock_locations_quantity = results["k"]
            amount_incidents_covered = results["amount_incidents_covered"]
            increase_budget = input("Increase budget to cover 100% of incidents? (y/n): ")
            if increase_budget == "y":
                incidents_to_cover = len(incidents_in_one_day)
                while amount_incidents_covered < incidents_to_cover:
                    dock_locations_quantity += 1
                    results = maximize_incidents_covered(docks, incidents_in_one_day, dock_locations_quantity, specific_docks)
                    create_map(
                        results["selected_docks"],
                        incidents_in_one_day,
                        f"specific_docks_increase_budget_{dock_locations_quantity}_docks",
                        results["incidents_covered"],
                        results["dock_assignments"],
                    )
                    map_file = Path(__file__).resolve().parent.parent.parent / "output" / f"specific_docks_increase_budget_{dock_locations_quantity}_docks.html"
                    if map_file.exists():
                        webbrowser.open(map_file.resolve().as_uri())

                    dock_locations_quantity = results["k"]
                    if results["amount_incidents_covered"] == amount_incidents_covered:
                        break
                    amount_incidents_covered = results["amount_incidents_covered"]
            elif increase_budget == "n":
                continue
            else:
                print("Invalid choice")
                continue  
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
            (
                specific_area_docks,
                specific_area_incidents,
                latitude_closest_to_ecuador,
                latitude_farthest_from_ecuador,
                longitude_closest_to_greenwich,
                longitude_farthest_from_greenwich,
            ) = specific_area_docks_and_incidents(docks, incidents)
            covered_incidents = []
            for incident in specific_area_incidents:
                if incident.covered_by(specific_area_docks):
                    covered_incidents.append(incident)
            create_map(
                specific_area_docks,
                specific_area_incidents,
                "docks_and_incidents_map",
                covered_incidents,
                latitude_closest_to_ecuador=latitude_closest_to_ecuador,
                latitude_farthest_from_ecuador=latitude_farthest_from_ecuador,
                longitude_closest_to_greenwich=longitude_closest_to_greenwich,
                longitude_farthest_from_greenwich=longitude_farthest_from_greenwich,
            )
            optimization_menu(specific_area_docks, specific_area_incidents)
        elif choice == "0":
            break
        else:
            print("Invalid choice")
            continue
        


            

    


if __name__ == "__main__":
    menu()
