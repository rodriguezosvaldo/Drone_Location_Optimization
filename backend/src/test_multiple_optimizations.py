from src.docks_and_incidents import METROSAFE_DOCK_LOCATIONS
from src.optimization_model import maximize_incidents_covered
from visualizations.charts_optimization_results import chart_incidents_covered_vs_k


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
        r = maximize_incidents_covered(docks, incidents, k, max_dock_coverage_capacity)
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
        r = maximize_incidents_covered(docks_remaining, incidents, additional_k, max_dock_coverage_capacity)
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

# Currently running only for day with the maximum number of incidents in each month
def compare_optimizations_by_month(docks, incidents_by_month, dock_locations_quantity, max_dock_coverage_capacity):
    monthly_results = []
    for month in sorted(incidents_by_month):
        days = incidents_by_month[month]
        if not days:
            continue

        max_incidents_day = max(days, key=lambda day: len(days[day]))
        peak_incidents = days[max_incidents_day]
        print(
            f"Running optimization for day {max_incidents_day} in month {month} "
            f"({len(peak_incidents)} incidents)..."
        )
        results = maximize_incidents_covered(
            docks,
            peak_incidents,
            dock_locations_quantity,
            max_dock_coverage_capacity,
        )
        if results is None:
            continue

        monthly_results.append(
            {
                "month": month,
                "peak_day": max_incidents_day,
                "peak_day_incidents": len(peak_incidents),
                "incidents_covered": results["incidents_covered"],
                "coverage_rate": results["coverage_rate"],
                "amount_selected_docks": results["amount_selected_docks"],
                "selected_docks": results["selected_docks"],
                "covered_incidents": results["covered_incidents"],
            }
        )

    return monthly_results


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


def menu(docks, incidents, incidents_by_month, dock_locations_quantity, max_dock_coverage_capacity):
    while True:
        print("\n                    Menu")
        print("---------------------------------------------------")
        print("1. Test optimizations with no fixed locations")
        print("2. Test optimizations starting from the 8 current MetroSafe dock locations")
        print("3. Run both scenarios and compare")
        print("4. Compare optimizations for the peak-incident day of each month")
        print("0. Exit")
        print("---------------------------------------------------")
        choice = input("\nEnter your choice: ")

        if choice == "1":
            k_min = int(input("Enter the number of docks to optimize in the first iteration: "))
            k_max = int(input("Enter the maximum number of docks to optimize: "))
            if not _validate_k_range(k_min, k_max):
                continue
            results = no_fixed_locations(docks, incidents, k_min, k_max, dock_locations_quantity, max_dock_coverage_capacity)
            chart_incidents_covered_vs_k(results, scenario_name="no_fixed")
        elif choice == "2":
            k_max = int(input("Enter the maximum total number of docks (including the 8 fixed): "))
            if k_max < len(METROSAFE_DOCK_LOCATIONS):
                print(f"The maximum must be at least {len(METROSAFE_DOCK_LOCATIONS)} (current MetroSafe docks).")
                continue
            results = fixed_locations(docks, incidents, k_max, dock_locations_quantity, max_dock_coverage_capacity)
            chart_incidents_covered_vs_k(results, scenario_name="fixed_metrosafe")
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
            chart_incidents_covered_vs_k(results_no_fixed, scenario_name="no_fixed")
            chart_incidents_covered_vs_k(results_fixed, scenario_name="fixed_metrosafe")
        elif choice == "4":
            compare_optimizations_by_month(
                docks,
                incidents_by_month,
                dock_locations_quantity,
                max_dock_coverage_capacity,
            )
        elif choice == "0":
            break
        else:
            print("Invalid choice")


def test_multiple_optimizations(docks, incidents, incidents_by_month, dock_locations_quantity, max_dock_coverage_capacity):
    menu(docks, incidents, incidents_by_month, dock_locations_quantity, max_dock_coverage_capacity)
