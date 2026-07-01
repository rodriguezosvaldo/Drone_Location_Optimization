import os
import sys
from pathlib import Path
import webbrowser

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

from src.docks_and_incidents import create_docks_and_incidents, specific_area_docks_and_incidents
from src.optimization_model import maximize_incidents_covered
from visualizations.map_incidents_and_docks import create_map
from visualizations.charts_optimization_results import chart_incidents_covered_vs_k

DOCKS_EXCEL_FILE_PATH = str(PROJECT_ROOT / "output" / "docks_JCPS_MetroSafe.xlsx")
INCIDENTS_EXCEL_FILE_PATH = str(PROJECT_ROOT / "output" / "clean_and_geocoded_LMPD_data_2025.xlsx")
PRIORITY_DOCKS_EXCEL_FILE_PATH = str(PROJECT_ROOT / "output" / "priority_docks.xlsx")


def optimization_menu(priority_docks, docks, incidents_in_one_day, latitude_closest_to_ecuador=None, latitude_farthest_from_ecuador=None, longitude_closest_to_greenwich=None, longitude_farthest_from_greenwich=None):
    priority_dock_names = [d.name for d in priority_docks]
    while True:
        print("\n                    Optimization Menu")
        print("---------------------------------------------------")
        print("1. Maximize the number of incidents covered")
        print("2. Maximize the number of incidents covered by priority docks")
        print("---------------------------------------------------")
        print("0. Exit")
        print("---------------------------------------------------")
        choice = input("\nEnter your choice: ")

        if choice == "1":
            dock_locations_quantity = int(input("Enter the number of dock locations available (Budget constraint): ")) # Budget constraint
            results = maximize_incidents_covered(docks, incidents_in_one_day, dock_locations_quantity)
            create_map(
                priority_dock_names,
                results["selected_docks"],
                incidents_in_one_day,
                f"optimized_map_{dock_locations_quantity}_docks",
                results["incidents_covered"],
                results["dock_assignments"],
                latitude_closest_to_ecuador=latitude_closest_to_ecuador,
                latitude_farthest_from_ecuador=latitude_farthest_from_ecuador,
                longitude_closest_to_greenwich=longitude_closest_to_greenwich,
                longitude_farthest_from_greenwich=longitude_farthest_from_greenwich,
            )
            map_file = Path(__file__).resolve().parent.parent.parent / "output" / f"optimized_map_{dock_locations_quantity}_docks.html"
            if map_file.exists():
                webbrowser.open(map_file.resolve().as_uri())

            dock_locations_quantity = results["k"]
            amount_incidents_covered = results["amount_incidents_covered"]
            increase_budget = input("Increase budget to cover 100% of incidents? (y/n): ")
            if increase_budget == "y":
                results_list = [results]
                incidents_to_cover = len(incidents_in_one_day)
                while amount_incidents_covered < incidents_to_cover:
                    dock_locations_quantity += 1
                    results = maximize_incidents_covered(docks, incidents_in_one_day, dock_locations_quantity)
                    results_list.append(results)
                    create_map(
                        priority_dock_names,
                        results["selected_docks"],
                        incidents_in_one_day,
                        f"increase_budget_{dock_locations_quantity}_docks",
                        results["incidents_covered"],
                        results["dock_assignments"],
                        latitude_closest_to_ecuador=latitude_closest_to_ecuador,
                        latitude_farthest_from_ecuador=latitude_farthest_from_ecuador,
                        longitude_closest_to_greenwich=longitude_closest_to_greenwich,
                        longitude_farthest_from_greenwich=longitude_farthest_from_greenwich,
                    )
                    map_file = Path(__file__).resolve().parent.parent.parent / "output" / f"increase_budget_{dock_locations_quantity}_docks.html"
                    if map_file.exists():
                        webbrowser.open(map_file.resolve().as_uri())

                    dock_locations_quantity = results["k"]
                    if results["amount_incidents_covered"] == amount_incidents_covered:
                        break
                    amount_incidents_covered = results["amount_incidents_covered"]
                chart_incidents_covered_vs_k(results_list, scenario_name="increase_budget")
            elif increase_budget == "n":
                continue
            else:
                print("Invalid choice")
                continue
        elif choice == "2":
            dock_locations_quantity = int(input("Enter the number of dock locations available (Budget constraint): ")) # Budget constraint
            results = maximize_incidents_covered(docks, incidents_in_one_day, dock_locations_quantity, priority_docks) 
            results_list = [results]
            create_map(
                priority_dock_names,
                results["selected_docks"],
                incidents_in_one_day,
                f"priority_docks_optimized_map_{dock_locations_quantity}_docks",
                results["incidents_covered"],
                results["dock_assignments"],
                latitude_closest_to_ecuador=latitude_closest_to_ecuador,
                latitude_farthest_from_ecuador=latitude_farthest_from_ecuador,
                longitude_closest_to_greenwich=longitude_closest_to_greenwich,
                longitude_farthest_from_greenwich=longitude_farthest_from_greenwich,
            )
            map_file = Path(__file__).resolve().parent.parent.parent / "output" / f"priority_docks_optimized_map_{dock_locations_quantity}_docks.html"
            if map_file.exists():
                webbrowser.open(map_file.resolve().as_uri())   

            dock_locations_quantity = results["k"]
            amount_incidents_covered = results["amount_incidents_covered"]
            increase_budget = input("Increase budget to cover 100% of incidents? (y/n): ")
            if increase_budget == "y":
                incidents_to_cover = len(incidents_in_one_day)
                while amount_incidents_covered < incidents_to_cover:
                    dock_locations_quantity += 1
                    results = maximize_incidents_covered(docks, incidents_in_one_day, dock_locations_quantity, priority_docks)
                    results_list.append(results)
                    create_map(
                        priority_dock_names,
                        results["selected_docks"],
                        incidents_in_one_day,
                        f"priority_docks_increase_budget_{dock_locations_quantity}_docks",
                        results["incidents_covered"],
                        results["dock_assignments"],
                        latitude_closest_to_ecuador=latitude_closest_to_ecuador,
                        latitude_farthest_from_ecuador=latitude_farthest_from_ecuador,
                        longitude_closest_to_greenwich=longitude_closest_to_greenwich,
                        longitude_farthest_from_greenwich=longitude_farthest_from_greenwich,
                    )
                    map_file = Path(__file__).resolve().parent.parent.parent / "output" / f"priority_docks_increase_budget_{dock_locations_quantity}_docks.html"
                    if map_file.exists():
                        webbrowser.open(map_file.resolve().as_uri())

                    dock_locations_quantity = results["k"]
                    if results["amount_incidents_covered"] == amount_incidents_covered:
                        break
                    amount_incidents_covered = results["amount_incidents_covered"]
                chart_incidents_covered_vs_k(results_list, scenario_name="priority_docks_increase_budget")
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
    docks, incidents, incidents_in_one_day, priority_dock_names = create_docks_and_incidents(DOCKS_EXCEL_FILE_PATH, INCIDENTS_EXCEL_FILE_PATH, PRIORITY_DOCKS_EXCEL_FILE_PATH)
    priority_docks = []
    for dock in docks:
        if dock.name in priority_dock_names:
            priority_docks.append(dock)
    
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
            for incident in incidents_in_one_day:
                if incident.covered_by(docks):
                    covered_incidents.append(incident)
            create_map(priority_dock_names, docks, incidents_in_one_day, "docks_and_incidents_map", covered_incidents)
            optimization_menu(priority_docks, docks, incidents_in_one_day)
        elif choice == "2":
            (
                priority_area_docks,
                priority_area_incidents_by_date,
                latitude_closest_to_ecuador,
                latitude_farthest_from_ecuador,
                longitude_closest_to_greenwich,
                longitude_farthest_from_greenwich,
            ) = specific_area_docks_and_incidents(docks, incidents, priority_dock_names)
            covered_incidents = []
            for incident in priority_area_incidents_by_date:
                if incident.covered_by(priority_area_docks):
                    covered_incidents.append(incident)
            create_map(
                priority_dock_names,
                priority_area_docks,
                priority_area_incidents_by_date,
                "docks_and_incidents_map",
                covered_incidents,
                latitude_closest_to_ecuador=latitude_closest_to_ecuador,
                latitude_farthest_from_ecuador=latitude_farthest_from_ecuador,
                longitude_closest_to_greenwich=longitude_closest_to_greenwich,
                longitude_farthest_from_greenwich=longitude_farthest_from_greenwich,
            )
            optimization_menu(priority_docks, priority_area_docks, priority_area_incidents_by_date, latitude_closest_to_ecuador, latitude_farthest_from_ecuador, longitude_closest_to_greenwich, longitude_farthest_from_greenwich)
        elif choice == "0":
            break
        else:
            print("Invalid choice")
            continue
        


            

    


if __name__ == "__main__":
    menu()
