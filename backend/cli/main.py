import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

from src.docks_and_incidents import create_docks_and_incidents, METROSAFE_DOCK_LOCATIONS
from src.optimization_model import maximize_incidents_covered, minimize_docks_used
from src.test_multiple_optimizations import test_multiple_optimizations
from visualizations.map_incidents_and_docks import create_map

DOCKS_EXCEL_FILE_PATH = str(PROJECT_ROOT / "output" / "docks_JCPS_MetroSafe.xlsx")
INCIDENTS_EXCEL_FILE_PATH = str(PROJECT_ROOT / "output" / "clean_and_geocoded_LMPD_data_2025.xlsx")

docks = None
incidents = None
incidents_by_month = None


def menu():
    global docks, incidents, incidents_by_month

    while True:
        print("\n                    Menu")
        print("---------------------------------------------------")
        print("1. Create docks and incidents from data")
        print("******** Optimization Models ********")
        print("2. Maximize the number of incidents covered by the docks")
        print("3. Minimize the number of docks covering 100% of the incidents")
        print("4. Test multiple optimizations")
        print("5. Exit")
        print("---------------------------------------------------")
        choice = input("\nEnter your choice: ")

        if choice == "1":
            docks, incidents, incidents_by_month = create_docks_and_incidents(
                DOCKS_EXCEL_FILE_PATH, INCIDENTS_EXCEL_FILE_PATH
            )
            covered_incidents = []
            for incident in incidents:
                if incident.covered_by(docks):
                    covered_incidents.append(incident)

            create_map(docks, incidents, "docks_and_incidents_map", covered_incidents)
            continue
        elif choice == "2":
            try:
                if docks is None or incidents is None:
                    raise Exception("Create docks and incidents first to run the optimization model")
                optimize_fixed_locations = input("Do you want to optimize the fixed locations? (y/n): ").lower()
                if optimize_fixed_locations == "y":
                    fixed_docks = [d for d in docks if d.name in METROSAFE_DOCK_LOCATIONS]
                    dock_locations_quantity = int(input("Enter the number of dock locations available: "))
                    max_dock_coverage_capacity = int(input("Enter the maximum number of incidents a dock can cover: "))
                    maximize_incidents_covered(
                        fixed_docks, incidents, dock_locations_quantity, max_dock_coverage_capacity
                    )
                elif optimize_fixed_locations == "n":
                    dock_locations_quantity = int(input("Enter the number of dock locations available: "))
                    max_dock_coverage_capacity = int(input("Enter the maximum number of incidents a dock can cover: "))
                    maximize_incidents_covered(
                        docks, incidents, dock_locations_quantity, max_dock_coverage_capacity
                    )
                else:
                    print("Invalid choice")
                    continue
            except Exception as e:
                print("Be sure to create docks and incidents before running the optimization model")
                print(f"Error running the optimization model: {e}")
                continue
        # Do not use this for final version!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!  
        # This is only for testing purposes!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!  
        elif choice == "3":
            try:
                if docks is None or incidents is None:
                    raise Exception("Create docks and incidents first to run the optimization model")
                minimize_docks_used(docks, incidents)
            except Exception as e:
                print("Be sure to create docks and incidents before running the optimization model")
                print(f"Error running the optimization model: {e}")
                continue     
        elif choice == "4":
            if docks is None or incidents is None:
                print("Create docks and incidents first (option 1).")
                continue
            dock_locations_quantity = int(input("Enter the number of dock locations available: "))
            max_dock_coverage_capacity = int(input("Enter the maximum number of incidents a dock can cover: "))
            test_multiple_optimizations(
                docks, incidents, incidents_by_month, dock_locations_quantity, max_dock_coverage_capacity
            )
            continue
        elif choice == "5":
            break
        else:
            print("Invalid choice")
            continue


if __name__ == "__main__":
    menu()
