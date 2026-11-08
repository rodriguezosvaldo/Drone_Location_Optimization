# Drone Location Optimization

## Introduction

This software helps decide where to place drone docking stations so that emergency (or other time-sensitive) demand is covered as well as possible under a limited budget.

It is useful for projects that need to:

- Choose a subset of candidate docking sites from a larger list
- Maximize incident coverage within a target response time
- Explore trade-offs between response time, budget (number of docks), and coverage percentage
- Compare deployment scenarios side by side (maps and charts)

Typical use cases include public-safety “drone as first responder” programs, campus or industrial emergency coverage, and any similar facility-location problem where demand points and candidate sites are known by latitude/longitude.

The main way to use the tool is the **web interface**. The steps below take you from cloning the repository to running an optimization on your own machine.

---

## Requirements

Before you start, make sure you have:

- **Python 3.10+** (tested with 3.13)
- **Git**
- An active **Gurobi license** (academic or commercial) — required to solve the optimization model

---

## Setup (clone → install → run)

### 1. Clone the repository

This downloads a copy of the project to your computer:

```bash
git clone https://github.com/rodriguezosvaldo/Drone_Location_Optimization.git
cd Drone_Location_Optimization
```

### 2. Create a virtual environment and install dependencies

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Gurobi

Install and activate your Gurobi license according to [Gurobi’s documentation](https://www.gurobi.com/documentation/). Without a valid license, the web app can load data and show maps, but optimization runs will fail.

### 4. Start the web application

From the project root (with the virtual environment activated):

```powershell
python run_web.py
```

Then open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

To stop the server, press `Ctrl+C` in the terminal.

---

## Using the web interface

The app has four sections in the left sidebar: **Data**, **Optimization**, **Compare**, and **Results**.

### Step A — Load your data (Data tab)

1. Prepare Excel files (`.xlsx` / `.xls`) with the columns below.
2. Select:
  - **Incidents file** (required)
  - **Docks file** (required)
  - **Priority docks file** (optional) — a subset of docks you want to treat as preferred (for example, stations already installed)
3. Click **Upload**.

The status card should show that data is loaded.

#### Required file formats


| File                          | Required columns                        | Notes                                                       |
| ----------------------------- | --------------------------------------- | ----------------------------------------------------------- |
| **Incidents**                 | `name`, `latitude`, `longitude`, `date` | One row per incident / demand point                         |
| **Docks**                     | `name`, `latitude`, `longitude`         | Candidate docking stations                                  |
| **Priority docks** (optional) | `name`                                  | Preferred docks; names must match entries in the docks file |


### Step B — Explore the map (Optimization tab)

1. Choose **Entire Area** (or **Priority Area** when a priority docks file was uploaded).
2. Optionally enable **Peak day incidents**:
  - **Off (default):** the map and optimization use **all** incidents in the selected area.
  - **On:** the app finds the single calendar day with the most incidents in that area and uses **only those** incidents. This is useful when you want to size the network for a high-demand day instead of an average across the full period.
3. Click **Generate Map** to preview docks and incidents on the map.

### Step C — Run an optimization (Optimization tab)

1. Set parameters as needed:
  - **Drone coverage capacity** — max incidents one drone can handle per day (default: 10)
  - **Drone speed** — mph (default: 35.8)
  - **Response time** — minutes (default: 2)
  - **Budget** — maximum number of docks to open (default: 8)
  - **Percentage to cover** — single value, or a **Range** (from / to / step) for multiple runs
2. Optionally enable **Open priority docks first** when priority docks are available.
3. Click **Run**.

After a successful run you can:

- Review coverage metrics in the results panel
- Use the iterative options (**Increase response time?** / **Increase budget?**) and click **Run** again. This runs several optimizations in sequence, raising response time and/or budget by the configured **Step** each time, until maximum incident coverage is reached (or coverage stops improving).
- Click **Refresh** to reset the optimization panel

### Step D — Compare scenarios (Compare tab)

Use this tab to run two scenarios with different parameters and compare maps and charts side by side. When both scenarios have iterative results, **Compare Charts** opens a combined comparison view.

### Step E — Download outputs (Results tab)

Generated maps, charts, and Excel tables appear under **Generated files**. Download what you need, or use **Delete All** to clear outputs from the server.

---

## Tips

- Keep the terminal running while you use the browser; closing it stops the app.
- Re-activate the virtual environment each new terminal session before running `python run_web.py`.
- If optimization fails, confirm that Gurobi is licensed and that your Excel columns match the table above.
- Hold the scroll wheel (or Space) and drag to move the map canvas.

---

## Repository layout (brief)

```
Drone_Location_Optimization/
├── run_web.py              # Start the web app
├── requirements.txt        # Installs backend dependencies
├── backend/                # FastAPI API + optimization models
├── frontend/               # Web UI (HTML / CSS / JS)
├── data/                   # Optional raw project datasets
└── output/                 # Optional processed datasets / figures
```

For most users, cloning the repo, installing dependencies, and running `python run_web.py` is enough. 