from src.optimization_model import maximize_incidents_covered
from visualizations.charts_optimization_results import (
    export_comparison_results,
    export_scenario_results,
)

# MetroSafe current dock locations
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


def _union_covered_incidents(dock_list, incidents):
    covered = set()
    for dock in dock_list:
        for incident in dock.incidents_covered(incidents)[0]:
            covered.add(incident)
    return covered


def _append_result(results, entry):
    if results:
        entry["delta_coverage"] = entry["incidents_covered"] - results[-1]["incidents_covered"]
    else:
        entry["delta_coverage"] = entry["incidents_covered"]
    results.append(entry)


def no_fixed_locations(docks, incidents, k_min, k_max, dock_locations_quantity, max_dock_coverage_capacity):
    results = []
    for k in range(k_min, k_max + 1):
        print(f"Running optimization test for k = {k}...")
        r = maximize_incidents_covered(docks, incidents, k, dock_locations_quantity, max_dock_coverage_capacity)
        if r is None:
            continue
        if r["incidents_covered"] == 0:
            break

        _append_result(results, r)
        if results[-1]["delta_coverage"] == 0 and len(results) > 1:
            break

    return results


def fixed_locations(docks, incidents, k_max, dock_locations_quantity, max_dock_coverage_capacity):
    fixed_docks = [d for d in docks if d.name in METROSAFE_DOCK_LOCATIONS]
    docks_remaining = [d for d in docks if d.name not in METROSAFE_DOCK_LOCATIONS]
    fixed_covered = _union_covered_incidents(fixed_docks, incidents)

    results = []
    _append_result(
        results,
        {
            "k": len(fixed_docks),
            "incidents_covered": len(fixed_covered),
            "coverage_rate": len(fixed_covered) / len(incidents),
            "amount_selected_docks": len(fixed_docks),
            "selected_docks": fixed_docks,
            "covered_incidents": list(fixed_covered),
        },
    )

    for total_k in range(len(fixed_docks) + 1, k_max + 1):
        additional_k = total_k - len(fixed_docks)
        print(f"Running optimization test for {additional_k} additional dock(s) (total k = {total_k})...")
        r = maximize_incidents_covered(docks_remaining, incidents, additional_k, dock_locations_quantity, max_dock_coverage_capacity)
        if r is None:
            continue

        all_docks = fixed_docks + r["selected_docks"]
        covered = _union_covered_incidents(all_docks, incidents)
        entry = {
            "k": total_k,
            "incidents_covered": len(covered),
            "coverage_rate": len(covered) / len(incidents),
            "amount_selected_docks": len(all_docks),
            "selected_docks": all_docks,
            "covered_incidents": list(covered),
        }
        _append_result(results, entry)
        if results[-1]["delta_coverage"] == 0:
            break

    return results


def _validate_k_range(k_min, k_max):
    if k_min > k_max:
        print("The minimum number of docks must be less than or equal to the maximum.")
        return False
    if k_min < 1:
        print("The minimum number of docks must be at least 1.")
        return False
    if k_max < 1:
        print("The maximum number of docks must be at least 1.")
        return False
    return True


def menu(docks, incidents, dock_locations_quantity, max_dock_coverage_capacity):
    while True:
        print("\n                    Menu")
        print("---------------------------------------------------")
        print("1. Test optimizations with no fixed locations")
        print("2. Test optimizations starting from the 8 current MetroSafe dock locations")
        print("3. Run both scenarios and compare")
        print("0. Exit")
        print("---------------------------------------------------")
        choice = input("\nEnter your choice: ")

        if choice == "1":
            k_min = int(input("Enter the number of docks to optimize in the first iteration: "))
            k_max = int(input("Enter the maximum number of docks to optimize: "))
            if not _validate_k_range(k_min, k_max):
                continue
            results = no_fixed_locations(docks, incidents, k_min, k_max, dock_locations_quantity, max_dock_coverage_capacity)
            export_scenario_results("no_fixed", results, incidents)
        elif choice == "2":
            k_max = int(input("Enter the maximum total number of docks (including the 8 fixed): "))
            if k_max < len(METROSAFE_DOCK_LOCATIONS):
                print(f"The maximum must be at least {len(METROSAFE_DOCK_LOCATIONS)} (current MetroSafe docks).")
                continue
            results = fixed_locations(docks, incidents, k_max, dock_locations_quantity, max_dock_coverage_capacity)
            export_scenario_results("fixed_metrosafe", results, incidents)
        elif choice == "3":
            k_min = int(input("Enter the starting number of docks (no-fixed scenario): "))
            k_max = int(input("Enter the maximum total number of docks: "))
            if not _validate_k_range(k_min, k_max):
                continue
            if k_max < len(METROSAFE_DOCK_LOCATIONS):
                print(f"The maximum must be at least {len(METROSAFE_DOCK_LOCATIONS)} for the fixed scenario.")
                continue
            results_no_fixed = no_fixed_locations(docks, incidents, k_min, k_max, dock_locations_quantity, max_dock_coverage_capacity)
            results_fixed = fixed_locations(docks, incidents, k_max, dock_locations_quantity, max_dock_coverage_capacity)
            export_scenario_results("no_fixed", results_no_fixed, incidents)
            export_scenario_results("fixed_metrosafe", results_fixed, incidents)
            export_comparison_results(
                {
                    "no_fixed": results_no_fixed,
                    "fixed_metrosafe": results_fixed,
                }
            )
        elif choice == "0":
            break
        else:
            print("Invalid choice")


def test_multiple_optimizations(docks, incidents, dock_locations_quantity, max_dock_coverage_capacity):
    menu(docks, incidents, dock_locations_quantity, max_dock_coverage_capacity)
