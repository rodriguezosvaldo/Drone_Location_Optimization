const API = "";

const activeJobPolls = {};
let currentMapPath = null;
let activeSection = "data";

const COMPARE_SCENARIOS = [
  { key: "s1", label: "Scenario 1" },
  { key: "s2", label: "Scenario 2" },
];

function $(id) {
  return document.getElementById(id);
}

function showToast(message, type = "success") {
  const toast = $("toast");
  toast.textContent = message;
  toast.className = `toast ${type}`;
  setTimeout(() => toast.classList.add("hidden"), 3500);
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    const detail = data?.detail || response.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

function optimizationContext(key = "default") {
  if (key === "default") {
    return {
      key: "default",
      compare: false,
      areaGroup: "area-mode",
      peakDayId: "peak-day-toggle",
      percentageGroup: "percentage-mode",
      fieldPrefix: "optimize-",
      pctRangePrefix: "pct-range-",
      percentageSingleId: "percentage-mode-single",
      percentageRangeId: "percentage-mode-range",
      priorityDocksFirstId: "priority-docks-first-toggle",
      priorityAreaRadioId: "area-priority",
      priorityAreaFullId: "area-full",
      runBtnId: "run-optimize-btn",
      iterativeRunBtnId: "run-iterative-btn",
      jobStatusId: "job-status",
      jobStatusTextId: "job-status-text",
      resultsId: "optimization-results",
      iterativeSectionId: "iterative-section",
      increaseResponseTimeId: "increase-response-time-toggle",
      increaseBudgetId: "increase-budget-toggle",
      responseTimeStepId: "response-time-step",
      budgetStepId: "budget-step",
      generateMapBtnId: "generate-map-btn",
    };
  }

  const prefix = `cmp-${key}-`;
  return {
    key,
    compare: true,
    areaGroup: "compare-area-mode",
    peakDayId: "compare-peak-day-toggle",
    percentageGroup: `${prefix}percentage-mode`,
    fieldPrefix: prefix,
    pctRangePrefix: `${prefix}pct-range-`,
    percentageSingleId: `${prefix}percentage-mode-single`,
    percentageRangeId: `${prefix}percentage-mode-range`,
    priorityDocksFirstId: `${prefix}priority-docks-first`,
    priorityAreaRadioId: "compare-area-priority",
    priorityAreaFullId: "compare-area-full",
    runBtnId: `${prefix}run-btn`,
    iterativeRunBtnId: `${prefix}run-iterative-btn`,
    jobStatusId: `${prefix}job-status`,
    jobStatusTextId: `${prefix}job-status-text`,
    resultsId: `${prefix}results`,
    iterativeSectionId: `${prefix}iterative-section`,
    increaseResponseTimeId: `${prefix}increase-response-time`,
    increaseBudgetId: `${prefix}increase-budget`,
    responseTimeStepId: `${prefix}response-time-step`,
    budgetStepId: `${prefix}budget-step`,
    generateMapBtnId: "compare-generate-map-btn",
  };
}

function ctxField(ctx, name) {
  return $(`${ctx.fieldPrefix}${name}`);
}

function selectedRadioValue(groupName) {
  return document.querySelector(`input[name="${groupName}"]:checked`)?.value;
}

function selectedArea(ctx = optimizationContext()) {
  return selectedRadioValue(ctx.areaGroup);
}

function selectedPercentageMode(ctx = optimizationContext()) {
  return selectedRadioValue(ctx.percentageGroup) || "single";
}

function isPercentageRangeMode(ctx = optimizationContext()) {
  return selectedPercentageMode(ctx) === "range";
}

function updatePercentageModePanels(ctx = optimizationContext()) {
  const rangeMode = isPercentageRangeMode(ctx);
  const iterativeSection = $(ctx.iterativeSectionId);
  if (iterativeSection && rangeMode) {
    iterativeSection.classList.add("hidden");
  }
}

function buildPercentageRangeValues(start, end, step) {
  const values = [];
  let current = start;
  while (current <= end + 1e-9) {
    values.push(Math.round(current * 1000) / 1000);
    current += step;
  }
  return values;
}

function updateWorkspaceForSection(section) {
  activeSection = section;
  const isCompare = section === "compare";
  $("map-container").classList.toggle("hidden", isCompare);
  $("compare-workspace").classList.toggle("hidden", !isCompare);
  $("canvas-hint").classList.toggle("hidden", isCompare);
}

function switchTab(section) {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.section === section);
  });
  document.querySelectorAll(".sidebar-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `section-${section}`);
  });
  updateWorkspaceForSection(section);
  if (section === "results") {
    loadOutputs();
  }
}

function setupNavigation() {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.section));
  });
}

function setFileNameState(nameEl, state) {
  nameEl.classList.remove("selected", "uploaded");
  if (state === "selected") {
    nameEl.classList.add("selected");
  } else if (state === "uploaded") {
    nameEl.classList.add("uploaded");
  }
}

function updateFileNameFromInput(input, nameEl) {
  const file = input.files[0];
  nameEl.textContent = file?.name || "No file selected";
  setFileNameState(nameEl, file ? "selected" : null);
}

function setupFileDrop(dropId, inputId, nameId) {
  const drop = $(dropId);
  const input = $(inputId);
  const nameEl = $(nameId);

  drop.addEventListener("dragover", (e) => {
    e.preventDefault();
    drop.classList.add("dragover");
  });
  drop.addEventListener("dragleave", () => drop.classList.remove("dragover"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    drop.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      updateFileNameFromInput(input, nameEl);
    }
  });
  input.addEventListener("change", () => {
    updateFileNameFromInput(input, nameEl);
  });
}

function markUploadedFileNames() {
  [
    ["incidents-file", "incidents-file-name"],
    ["docks-file", "docks-file-name"],
    ["priority-file", "priority-file-name"],
  ].forEach(([inputId, nameId]) => {
    if ($(inputId).files[0]) {
      setFileNameState($(nameId), "uploaded");
    }
  });
}

function updatePriorityAreaOption(status, ctx = optimizationContext()) {
  const priorityRadio = $(ctx.priorityAreaRadioId);
  if (!priorityRadio) return;

  const priorityLabel = priorityRadio.closest(".radio-option");
  const priorityInfoBtn = ctx.compare
    ? $("compare-priority-info-btn")
    : $("priority-info-btn");
  const hasPriority = status.priority_docks_loaded;

  priorityRadio.disabled = !hasPriority;
  priorityLabel.classList.toggle("disabled", !hasPriority);
  if (priorityInfoBtn) {
    priorityInfoBtn.disabled = !hasPriority;
  }

  if (!hasPriority && priorityRadio.checked) {
    $(ctx.priorityAreaFullId).checked = true;
  }
}

function updatePriorityDocksFirstOption(status, ctx = optimizationContext()) {
  const toggle = $(ctx.priorityDocksFirstId);
  if (!toggle) return;

  const hasPriority = status.priority_docks_loaded;
  toggle.disabled = !hasPriority;
  toggle.closest(".toggle-row").classList.toggle("disabled", !hasPriority);

  if (!hasPriority && toggle.checked) {
    toggle.checked = false;
  }
}

async function refreshStatus() {
  try {
    const status = await api("/api/data/status");
    const dot = $("status-dot");
    const text = $("status-text");

    updatePriorityAreaOption(status, optimizationContext());
    updatePriorityAreaOption(status, optimizationContext("s1"));
    updatePriorityDocksFirstOption(status, optimizationContext());
    COMPARE_SCENARIOS.forEach(({ key }) => {
      updatePriorityDocksFirstOption(status, optimizationContext(key));
    });

    if (status.loaded) {
      dot.className = "status-dot online";
      let msg = `${status.docks_count} docks · ${status.all_incidents_count} incidents`;
      if (status.full_peak_incidents_count) {
        msg += ` · ${status.full_peak_incidents_count} peak-day (entire area)`;
      }
      if (status.priority_area_all_incidents_count) {
        msg += ` · ${status.priority_area_all_incidents_count} in priority area`;
        if (status.priority_area_peak_incidents_count) {
          msg += ` (${status.priority_area_peak_incidents_count} peak-day)`;
        }
      }
      if (status.priority_docks_loaded) {
        msg += ` · ${status.priority_docks_count} priority docks`;
      }
      text.textContent = msg;
    } else {
      dot.className = "status-dot offline";
      text.textContent = "Upload incidents and docks";
    }
  } catch {
    $("status-text").textContent = "Could not connect to server";
    $("status-dot").className = "status-dot offline";
    const emptyStatus = { priority_docks_loaded: false };
    updatePriorityAreaOption(emptyStatus, optimizationContext());
    updatePriorityAreaOption(emptyStatus, optimizationContext("s1"));
    updatePriorityDocksFirstOption(emptyStatus, optimizationContext());
    COMPARE_SCENARIOS.forEach(({ key }) => {
      updatePriorityDocksFirstOption(emptyStatus, optimizationContext(key));
    });
  }
}

function outputFileUrl(relativePath) {
  const normalized = relativePath.replace(/^\//, "");
  return `/api/outputs/file/${normalized}?v=${Date.now()}`;
}

function showMap(relativePath) {
  currentMapPath = relativePath.replace(/^\//, "");
  const frame = $("map-frame");
  const placeholder = $("map-placeholder");

  frame.src = outputFileUrl(currentMapPath);
  frame.classList.remove("hidden");
  placeholder.classList.add("hidden");
}

function clearMap() {
  currentMapPath = null;
  const frame = $("map-frame");
  const placeholder = $("map-placeholder");

  frame.src = "about:blank";
  frame.classList.add("hidden");
  placeholder.classList.remove("hidden");
}

function showCompareMap(scenarioKey, relativePath) {
  const frame = $(`cmp-${scenarioKey}-map-frame`);
  const placeholder = $(`cmp-${scenarioKey}-map-placeholder`);
  if (!frame || !placeholder) return;

  frame.src = outputFileUrl(relativePath);
  frame.classList.remove("hidden");
  placeholder.classList.add("hidden");
}

function clearCompareMap(scenarioKey) {
  const frame = $(`cmp-${scenarioKey}-map-frame`);
  const placeholder = $(`cmp-${scenarioKey}-map-placeholder`);
  if (!frame || !placeholder) return;

  frame.src = "about:blank";
  frame.classList.add("hidden");
  placeholder.classList.remove("hidden");
}

function showCompareCharts(scenarioKey, data) {
  const chartImg = $(`cmp-${scenarioKey}-chart-img`);
  const chartPlaceholder = $(`cmp-${scenarioKey}-chart-placeholder`);
  const chartSummary = $(`cmp-${scenarioKey}-chart-summary`);
  if (!chartImg || !chartPlaceholder || !chartSummary) return;

  const outputs = data.outputs || [];
  const chartPath = outputs.find((path) => path.endsWith(".png") && !path.includes("dock_efficiency"))
    || outputs.find((path) => path.endsWith(".png"));

  chartImg.classList.add("hidden");
  chartSummary.classList.add("hidden");
  chartPlaceholder.classList.remove("hidden");

  if (chartPath) {
    chartImg.src = `/api/outputs/file/${chartPath.replace(/^\//, "")}`;
    chartImg.classList.remove("hidden");
    chartPlaceholder.classList.add("hidden");
    return;
  }

  const result = data.result;
  const rangeMode = data.percentage_mode === "range";
  let summaryHtml = "<strong>Results</strong>";

  if (rangeMode) {
    const steps = data.steps || [];
    summaryHtml += `<div>${steps.length} scenarios (${data.percentage_range_start}–${data.percentage_range_end}, step ${data.percentage_range_step})</div>`;
  } else {
    summaryHtml += `
      <div>Covered: ${result.amount_incidents_covered} incidents (${result.coverage_rate}%)</div>
      <div>Docks used: ${result.amount_selected_docks} / budget ${result.k}</div>
    `;
    if (result.response_time_minutes != null) {
      summaryHtml += `<div>Response time: ${result.response_time_minutes} min</div>`;
    }
  }

  chartSummary.innerHTML = summaryHtml;
  chartSummary.classList.remove("hidden");
  chartPlaceholder.classList.add("hidden");
}

function clearCompareCharts(scenarioKey) {
  const chartImg = $(`cmp-${scenarioKey}-chart-img`);
  const chartPlaceholder = $(`cmp-${scenarioKey}-chart-placeholder`);
  const chartSummary = $(`cmp-${scenarioKey}-chart-summary`);
  if (!chartImg || !chartPlaceholder || !chartSummary) return;

  chartImg.src = "";
  chartImg.classList.add("hidden");
  chartSummary.innerHTML = "";
  chartSummary.classList.add("hidden");
  chartPlaceholder.classList.remove("hidden");
}

function resetOptimizationPanel(ctx = optimizationContext()) {
  if (activeJobPolls[ctx.key]) {
    clearInterval(activeJobPolls[ctx.key]);
    activeJobPolls[ctx.key] = null;
  }

  if (!ctx.compare) {
    clearMap();
  } else {
    clearCompareMap(ctx.key);
    clearCompareCharts(ctx.key);
  }

  const resultsEl = $(ctx.resultsId);
  if (resultsEl) {
    resultsEl.innerHTML = "";
    resultsEl.classList.add("hidden");
  }
  $(ctx.iterativeSectionId)?.classList.add("hidden");
  $(ctx.jobStatusId)?.classList.add("hidden");

  if (!ctx.compare) {
    $(ctx.priorityAreaFullId).checked = true;
    $(ctx.peakDayId).checked = false;
  }

  $(ctx.priorityDocksFirstId).checked = false;
  ctxField(ctx, "response-time").value = 2;
  ctxField(ctx, "budget").value = 8;
  $(ctx.percentageSingleId).checked = true;
  ctxField(ctx, "percentage").value = 100;
  $(`${ctx.pctRangePrefix}start`).value = 10;
  $(`${ctx.pctRangePrefix}end`).value = 100;
  $(`${ctx.pctRangePrefix}step`).value = 10;
  updatePercentageModePanels(ctx);
  $(ctx.increaseResponseTimeId).checked = false;
  $(ctx.increaseBudgetId).checked = false;
  $(ctx.responseTimeStepId).value = 1;
  $(ctx.budgetStepId).value = 1;

  $(ctx.runBtnId).disabled = false;
  $(ctx.iterativeRunBtnId).disabled = false;
  if (!ctx.compare) {
    $(ctx.generateMapBtnId).disabled = false;
  }

  if (!ctx.compare) {
    document.querySelectorAll(".tooltip-popup").forEach((el) => el.classList.add("hidden"));
    refreshStatus();
  }
}

function resetComparePanel() {
  $("compare-area-full").checked = true;
  $("compare-peak-day-toggle").checked = false;
  $("compare-generate-map-btn").disabled = false;
  COMPARE_SCENARIOS.forEach(({ key }) => resetOptimizationPanel(optimizationContext(key)));
  document.querySelectorAll("#section-compare .tooltip-popup").forEach((el) => el.classList.add("hidden"));
  refreshStatus();
}

const TRASH_ICON = `
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <polyline points="3 6 5 6 21 6"></polyline>
    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path>
    <path d="M10 11v6"></path>
    <path d="M14 11v6"></path>
    <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"></path>
  </svg>
`;

function stepMapButton(mapPath, ctx) {
  if (!mapPath) return "";
  const normalized = mapPath.replace(/^\//, "");
  return `<button type="button" class="btn ghost small step-map-btn" data-map="${normalized}" data-scenario="${ctx.key}">Map</button>`;
}

function bindStepMapButtons(container, ctx) {
  container.querySelectorAll(".step-map-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mapPath = btn.dataset.map;
      if (ctx.compare) {
        showCompareMap(ctx.key, mapPath);
      } else {
        showMap(mapPath);
      }
    });
  });
}

function renderOptimizationResults(data, ctx = optimizationContext()) {
  const container = $(ctx.resultsId);
  if (!container) return;

  const result = data.result;
  const steps = data.steps || [result];
  const rangeMode = data.percentage_mode === "range";
  const mapOutputs = (data.outputs || []).filter((path) => path.endsWith(".html"));
  const primaryMap = data.map || mapOutputs[0];

  let html = `<strong>Results</strong>`;

  if (rangeMode) {
    html += `<div>${steps.length} scenarios (${data.percentage_range_start}–${data.percentage_range_end}, step ${data.percentage_range_step})</div>`;
    steps.forEach((step, index) => {
      const targetPct = step.target_percentage ?? step.percentage_to_cover;
      const mapPath = step.map || mapOutputs[index];
      html += `
        <div class="step-item">
          <span class="step-item-text">${targetPct}% target: ${step.amount_incidents_covered} covered (${step.coverage_rate}%) · ${step.amount_selected_docks} docks</span>
          ${stepMapButton(mapPath, ctx)}
        </div>
      `;
    });
    const chartOutputs = (data.outputs || []).filter((path) => path.endsWith(".png"));
    chartOutputs.forEach((chartPath) => {
      const label = chartPath.includes("dock_efficiency")
        ? "Dock efficiency vs docks"
        : "Incidents covered vs target %";
      html += `
        <div class="step-item">
          <span class="step-item-text">${label}</span>
          <a class="btn ghost small" href="/api/outputs/file/${chartPath}" target="_blank" rel="noopener">Chart</a>
        </div>
      `;
    });
  } else {
    html += `
      <div>Covered: ${result.amount_incidents_covered} incidents (${result.coverage_rate}%)</div>
      <div>Docks used: ${result.amount_selected_docks} / budget ${result.k}</div>
    `;

    if (result.drone_speed_mph != null) {
      html += `<div>Drone speed: ${result.drone_speed_mph} mph</div>`;
    }

    if (result.response_time_minutes != null) {
      html += `<div>Response time: ${result.response_time_minutes} min</div>`;
    }

    if (steps.length > 1) {
      html += `<div class="step-item step-item-summary">${steps.length} optimization steps completed.</div>`;
      steps.forEach((step, index) => {
        const mapPath = step.map || mapOutputs[index];
        html += `
          <div class="step-item">
            <span class="step-item-text">Step ${index + 1}: ${step.amount_incidents_covered} covered · k=${step.k}${step.response_time_minutes != null ? ` · ${step.response_time_minutes} min` : ""}</span>
            ${stepMapButton(mapPath, ctx)}
          </div>
        `;
      });
    } else if (primaryMap) {
      html += `
        <div class="step-item">
          <span class="step-item-text">Optimization map</span>
          ${stepMapButton(primaryMap, ctx)}
        </div>
      `;
    }
  }

  container.innerHTML = html;
  container.classList.remove("hidden");
  bindStepMapButtons(container, ctx);

  if (!rangeMode) {
    $(ctx.iterativeSectionId)?.classList.remove("hidden");
  }
}

function buildOptimizePayload(ctx, iterative) {
  const rangeMode = isPercentageRangeMode(ctx);
  const payload = {
    area: selectedArea(ctx),
    peak_day_only: $(ctx.peakDayId).checked,
    drone_coverage_capacity: Number(ctxField(ctx, "drone-coverage-capacity").value),
    drone_speed_mph: Number(ctxField(ctx, "drone-speed").value),
    response_time_minutes: Number(ctxField(ctx, "response-time").value),
    budget: Number(ctxField(ctx, "budget").value),
    open_priority_docks_first: $(ctx.priorityDocksFirstId).checked,
    percentage_mode: selectedPercentageMode(ctx),
    iterative: iterative && !rangeMode,
    increase_budget: iterative && !rangeMode && $(ctx.increaseBudgetId).checked,
    increase_response_time: iterative && !rangeMode && $(ctx.increaseResponseTimeId).checked,
  };

  if (payload.increase_budget) {
    payload.budget_step = Number($(ctx.budgetStepId).value);
  }
  if (payload.increase_response_time) {
    payload.response_time_step = Number($(ctx.responseTimeStepId).value);
  }

  if (rangeMode) {
    payload.percentage_range_start = Number($(`${ctx.pctRangePrefix}start`).value);
    payload.percentage_range_end = Number($(`${ctx.pctRangePrefix}end`).value);
    payload.percentage_range_step = Number($(`${ctx.pctRangePrefix}step`).value);
  } else {
    payload.percentage_to_cover = Number(ctxField(ctx, "percentage").value);
  }

  return payload;
}

function validateOptimizePayload(payload, iterative) {
  if (!payload.area) {
    showToast("Select an analysis area.", "error");
    return false;
  }
  if (!Number.isFinite(payload.drone_coverage_capacity) || payload.drone_coverage_capacity < 1) {
    showToast("Drone coverage capacity must be at least 1.", "error");
    return false;
  }
  if (!Number.isFinite(payload.drone_speed_mph) || payload.drone_speed_mph <= 0) {
    showToast("Drone speed must be greater than 0.", "error");
    return false;
  }
  if (!Number.isFinite(payload.response_time_minutes) || payload.response_time_minutes <= 0) {
    showToast("Response time must be greater than 0.", "error");
    return false;
  }
  if (!Number.isFinite(payload.budget) || payload.budget < 1) {
    showToast("Budget must be at least 1.", "error");
    return false;
  }

  if (payload.percentage_mode === "range") {
    const { percentage_range_start: start, percentage_range_end: end, percentage_range_step: step } = payload;
    if (
      !Number.isFinite(start) || start < 1 || start > 100
      || !Number.isFinite(end) || end < 1 || end > 100
      || !Number.isFinite(step) || step < 1 || step > 100
    ) {
      showToast("Percentage range values must be between 1 and 100.", "error");
      return false;
    }
    if (start > end) {
      showToast("Range start must be less than or equal to end.", "error");
      return false;
    }
    const values = buildPercentageRangeValues(start, end, step);
    if (values.length < 2) {
      showToast("Range must produce at least two scenarios.", "error");
      return false;
    }
    return true;
  }

  if (
    !Number.isFinite(payload.percentage_to_cover)
    || payload.percentage_to_cover < 1
    || payload.percentage_to_cover > 100
  ) {
    showToast("Percentage to cover must be between 1 and 100.", "error");
    return false;
  }
  if (iterative && !payload.increase_budget && !payload.increase_response_time) {
    showToast("Enable at least one iterative option.", "error");
    return false;
  }
  if (iterative && payload.increase_budget) {
    if (!Number.isFinite(payload.budget_step) || payload.budget_step < 1) {
      showToast("Budget step must be at least 1.", "error");
      return false;
    }
  }
  if (iterative && payload.increase_response_time) {
    if (!Number.isFinite(payload.response_time_step) || payload.response_time_step <= 0) {
      showToast("Response time step must be greater than 0.", "error");
      return false;
    }
  }
  return true;
}

function handleOptimizationComplete(data, ctx = optimizationContext()) {
  const scenario = COMPARE_SCENARIOS.find((item) => item.key === ctx.key);
  const label = scenario ? scenario.label : "Optimization";
  showToast(`${label} completed.`);
  renderOptimizationResults(data, ctx);

  const mapPath = data.map || data.outputs?.find((output) => output.endsWith(".html"));
  if (mapPath) {
    const normalized = mapPath.replace(/^\//, "");
    if (ctx.compare) {
      showCompareMap(ctx.key, normalized);
      showCompareCharts(ctx.key, data);
    } else {
      showMap(normalized);
    }
  } else if (ctx.compare) {
    showCompareCharts(ctx.key, data);
  }

  loadOutputs();
}

async function uploadAll() {
  const incidents = $("incidents-file").files[0];
  const docks = $("docks-file").files[0];
  const priority = $("priority-file").files[0];

  const missing = [];
  if (!incidents) missing.push("incidents");
  if (!docks) missing.push("docks");

  if (missing.length) {
    showToast(`Select incidents and docks before uploading. Missing: ${missing.join(", ")}.`, "error");
    return;
  }

  const formData = new FormData();
  formData.append("incidents", incidents);
  formData.append("docks", docks);
  if (priority) {
    formData.append("priority_docks", priority);
  }

  const btn = $("upload-btn");
  btn.disabled = true;

  try {
    const result = await api("/api/data/upload", { method: "POST", body: formData });
    showToast(result.message);
    markUploadedFileNames();
    await refreshStatus();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    btn.disabled = false;
  }
}

async function generateMap(ctx = optimizationContext()) {
  const area = selectedArea(ctx);
  if (!area) return;

  const btn = $(ctx.generateMapBtnId);
  btn.disabled = true;

  try {
    const result = await api("/api/data/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        area,
        peak_day_only: $(ctx.peakDayId).checked,
      }),
    });
    showToast(result.message);

    if (ctx.compare) {
      COMPARE_SCENARIOS.forEach(({ key }) => showCompareMap(key, result.map));
    } else {
      showMap(result.map);
    }

    await refreshStatus();
    loadOutputs();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    btn.disabled = false;
  }
}

function startJobPolling(jobId, scenarioCount, ctx) {
  const statusEl = $(ctx.jobStatusId);
  statusEl.classList.remove("hidden");
  const scenarioText = scenarioCount > 1
    ? `Running ${scenarioCount} scenarios… this may take several minutes.`
    : "Running optimization… this may take several minutes.";
  $(ctx.jobStatusTextId).textContent = scenarioText;

  if (activeJobPolls[ctx.key]) clearInterval(activeJobPolls[ctx.key]);

  activeJobPolls[ctx.key] = setInterval(async () => {
    try {
      const job = await api(`/api/optimize/jobs/${jobId}`);
      if (job.status === "completed") {
        clearInterval(activeJobPolls[ctx.key]);
        activeJobPolls[ctx.key] = null;
        statusEl.classList.add("hidden");
        handleOptimizationComplete(job.result, ctx);
      } else if (job.status === "failed") {
        clearInterval(activeJobPolls[ctx.key]);
        activeJobPolls[ctx.key] = null;
        statusEl.classList.add("hidden");
        showToast(job.error || "Optimization failed.", "error");
      }
    } catch (error) {
      clearInterval(activeJobPolls[ctx.key]);
      activeJobPolls[ctx.key] = null;
      statusEl.classList.add("hidden");
      showToast(error.message, "error");
    }
  }, 2500);
}

async function runOptimization(ctx = optimizationContext(), iterative = false) {
  const payload = buildOptimizePayload(ctx, iterative);
  if (!validateOptimizePayload(payload, iterative)) {
    return;
  }

  const btn = iterative ? $(ctx.iterativeRunBtnId) : $(ctx.runBtnId);
  btn.disabled = true;
  $(ctx.runBtnId).disabled = true;
  $(ctx.iterativeRunBtnId).disabled = true;

  if (ctx.compare) {
    clearCompareMap(ctx.key);
    clearCompareCharts(ctx.key);
  } else {
    clearMap();
  }

  const statusEl = $(ctx.jobStatusId);
  if (!iterative) {
    statusEl.classList.remove("hidden");
    $(ctx.jobStatusTextId).textContent = "Running optimization…";
  }

  try {
    const result = await api("/api/optimize/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (result.job_id) {
      showToast(result.message);
      const scenarioCount = payload.percentage_mode === "range"
        ? buildPercentageRangeValues(
          payload.percentage_range_start,
          payload.percentage_range_end,
          payload.percentage_range_step,
        ).length
        : 1;
      startJobPolling(result.job_id, scenarioCount, ctx);
      return;
    }

    statusEl.classList.add("hidden");
    handleOptimizationComplete(result, ctx);
  } catch (error) {
    statusEl.classList.add("hidden");
    showToast(error.message, "error");
  } finally {
    btn.disabled = false;
    $(ctx.runBtnId).disabled = false;
    $(ctx.iterativeRunBtnId).disabled = false;
  }
}

async function deleteOutput(filePath) {
  try {
    const result = await api(`/api/outputs/file/${filePath}`, { method: "DELETE" });
    showToast(result.message);
    if (currentMapPath === filePath) {
      clearMap();
    }
    await loadOutputs();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function deleteAllOutputs() {
  if (!confirm("Delete all generated maps? This cannot be undone.")) {
    return;
  }

  const btn = $("delete-all-outputs-btn");
  btn.disabled = true;

  try {
    const result = await api("/api/outputs", { method: "DELETE" });
    showToast(result.message);
    clearMap();
    COMPARE_SCENARIOS.forEach(({ key }) => {
      clearCompareMap(key);
      clearCompareCharts(key);
    });
    await loadOutputs();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    btn.disabled = false;
  }
}

async function loadOutputs() {
  const list = $("outputs-list");
  list.innerHTML = "<p class='hint'>Loading…</p>";

  try {
    const data = await api("/api/outputs");
    const htmlFiles = data.files.filter((f) => f.path.endsWith(".html"));

    if (!htmlFiles.length) {
      list.innerHTML = "<p class='hint'>No maps generated yet.</p>";
      return;
    }

    list.innerHTML = "";
    htmlFiles.forEach((file) => {
      const item = document.createElement("div");
      item.className = "output-item";
      item.innerHTML = `
        <div class="output-item-name" title="${file.name}">
          <strong>${file.name}</strong>
        </div>
        <div class="output-actions">
          <button class="btn ghost small view-btn">View</button>
          <a class="btn ghost small" href="/api/outputs/file/${file.path}" download="${file.name}">↓</a>
          <button class="btn ghost small danger icon-btn delete-btn" title="Delete" aria-label="Delete ${file.name}">${TRASH_ICON}</button>
        </div>
      `;
      item.querySelector(".view-btn").addEventListener("click", () => {
        if (activeSection === "compare") {
          showToast("Switch to Optimization tab to view maps in the main workspace.", "error");
          return;
        }
        showMap(file.path);
      });
      item.querySelector(".delete-btn").addEventListener("click", () => {
        deleteOutput(file.path);
      });
      list.appendChild(item);
    });
  } catch (error) {
    list.innerHTML = `<p class='hint'>${error.message}</p>`;
  }
}

function setupTooltip(buttonId, tooltipId) {
  const btn = $(buttonId);
  const tooltip = $(tooltipId);
  if (!btn || !tooltip) return;

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    document.querySelectorAll(".tooltip-popup").forEach((el) => {
      if (el !== tooltip) el.classList.add("hidden");
    });
    tooltip.classList.toggle("hidden");
  });
}

function setupTooltips() {
  setupTooltip("priority-info-btn", "priority-tooltip");
  setupTooltip("peak-day-info-btn", "peak-day-tooltip");
  setupTooltip("drone-coverage-capacity-info-btn", "drone-coverage-capacity-tooltip");
  setupTooltip("drone-speed-info-btn", "drone-speed-tooltip");
  setupTooltip("response-time-info-btn", "response-time-tooltip");
  setupTooltip("budget-info-btn", "budget-tooltip");
  setupTooltip("compare-priority-info-btn", "compare-priority-tooltip");
  setupTooltip("compare-peak-day-info-btn", "compare-peak-day-tooltip");

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".info-btn") && !e.target.closest(".tooltip-popup")) {
      document.querySelectorAll(".tooltip-popup").forEach((el) => el.classList.add("hidden"));
    }
  });
}

function buildScenarioPanelHTML(key, label) {
  const p = `cmp-${key}-`;
  return `
    <div class="card optimization-card compare-scenario-card" data-scenario="${key}">
      <div class="scenario-card-header">
        <h3 class="section-title">Optimization Params</h3>
        <span class="scenario-label">${label}</span>
      </div>

      <div class="toggle-row disabled">
        <label class="toggle-label" for="${p}priority-docks-first">Open priority docks first</label>
        <label class="toggle-switch">
          <input type="checkbox" id="${p}priority-docks-first" disabled>
          <span class="toggle-slider"></span>
        </label>
      </div>

      <div class="param-row">
        <label class="param-label" for="${p}drone-coverage-capacity">Drone coverage capacity</label>
        <input type="number" id="${p}drone-coverage-capacity" class="param-input" min="1" step="1" value="10">
      </div>

      <div class="param-row">
        <label class="param-label" for="${p}drone-speed">Drone speed</label>
        <input type="number" id="${p}drone-speed" class="param-input" min="0.1" step="0.1" value="35.8">
      </div>

      <div class="param-row">
        <label class="param-label" for="${p}response-time">Response time</label>
        <input type="number" id="${p}response-time" class="param-input" min="1" step="1" value="2">
      </div>

      <div class="param-row">
        <label class="param-label" for="${p}budget">Budget</label>
        <input type="number" id="${p}budget" class="param-input" min="1" value="8">
      </div>

      <div class="percentage-block cmp-percentage-block" data-scenario="${key}">
        <span class="param-label percentage-title">Percentage to cover</span>

        <div class="radio-group inline" role="radiogroup" aria-label="Percentage mode">
          <label class="radio-option compact">
            <input type="radio" name="${p}percentage-mode" value="single" id="${p}percentage-mode-single" checked>
            <span>Single</span>
          </label>
          <label class="radio-option compact">
            <input type="radio" name="${p}percentage-mode" value="range" id="${p}percentage-mode-range">
            <span>Range</span>
          </label>
        </div>

        <div class="param-row cmp-percentage-single-panel" id="${p}percentage-single-panel">
          <label class="param-label" for="${p}percentage">Value</label>
          <input type="number" id="${p}percentage" class="param-input" min="1" max="100" value="100">
        </div>

        <div class="cmp-percentage-range-panel" id="${p}percentage-range-panel">
          <div class="param-row">
            <label class="param-label" for="${p}pct-range-start">From</label>
            <input type="number" id="${p}pct-range-start" class="param-input" min="1" max="100" value="10">
          </div>
          <div class="param-row">
            <label class="param-label" for="${p}pct-range-end">To</label>
            <input type="number" id="${p}pct-range-end" class="param-input" min="1" max="100" value="100">
          </div>
          <div class="param-row">
            <label class="param-label" for="${p}pct-range-step">Step</label>
            <input type="number" id="${p}pct-range-step" class="param-input" min="1" max="100" value="10">
          </div>
        </div>
      </div>

      <button class="btn outline full-width" id="${p}run-btn">Run</button>

      <div class="job-status hidden" id="${p}job-status">
        <span class="spinner"></span>
        <span id="${p}job-status-text">Running optimization…</span>
      </div>

      <div class="optimization-results hidden" id="${p}results"></div>

      <div class="iterative-section hidden" id="${p}iterative-section">
        <div class="iterative-option">
          <div class="toggle-row compact">
            <label class="toggle-label" for="${p}increase-response-time">Increase response time?</label>
            <label class="toggle-switch">
              <input type="checkbox" id="${p}increase-response-time">
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="param-row iterative-step-panel">
            <label class="param-label" for="${p}response-time-step">Step</label>
            <input type="number" id="${p}response-time-step" class="param-input" min="1" step="1" value="1">
          </div>
        </div>
        <div class="iterative-option">
          <div class="toggle-row compact">
            <label class="toggle-label" for="${p}increase-budget">Increase budget?</label>
            <label class="toggle-switch">
              <input type="checkbox" id="${p}increase-budget">
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="param-row iterative-step-panel">
            <label class="param-label" for="${p}budget-step">Step</label>
            <input type="number" id="${p}budget-step" class="param-input" min="1" step="1" value="1">
          </div>
        </div>
        <button class="btn outline full-width" id="${p}run-iterative-btn">Run</button>
      </div>
    </div>
  `;
}

function setupCompareScenarios() {
  const container = $("compare-scenarios-container");
  container.innerHTML = COMPARE_SCENARIOS
    .map(({ key, label }) => buildScenarioPanelHTML(key, label))
    .join("");

  COMPARE_SCENARIOS.forEach(({ key }) => {
    const ctx = optimizationContext(key);
    $(ctx.runBtnId).addEventListener("click", () => runOptimization(ctx, false));
    $(ctx.iterativeRunBtnId).addEventListener("click", () => runOptimization(ctx, true));
    document.querySelectorAll(`input[name="${ctx.percentageGroup}"]`).forEach((input) => {
      input.addEventListener("change", () => updatePercentageModePanels(ctx));
      input.addEventListener("click", () => updatePercentageModePanels(ctx));
    });
    updatePercentageModePanels(ctx);
  });
}

function bindEvents() {
  $("upload-btn").addEventListener("click", uploadAll);
  $("generate-map-btn").addEventListener("click", () => generateMap(optimizationContext()));
  $("compare-generate-map-btn").addEventListener("click", () => generateMap(optimizationContext("s1")));
  $("run-optimize-btn").addEventListener("click", () => runOptimization(optimizationContext(), false));
  $("run-iterative-btn").addEventListener("click", () => runOptimization(optimizationContext(), true));
  $("delete-all-outputs-btn").addEventListener("click", deleteAllOutputs);
  $("optimization-refresh-btn").addEventListener("click", () => resetOptimizationPanel(optimizationContext()));
  $("compare-refresh-btn").addEventListener("click", resetComparePanel);
  document.querySelectorAll('input[name="percentage-mode"]').forEach((input) => {
    input.addEventListener("change", () => updatePercentageModePanels(optimizationContext()));
    input.addEventListener("click", () => updatePercentageModePanels(optimizationContext()));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupCompareScenarios();
  setupFileDrop("incidents-drop", "incidents-file", "incidents-file-name");
  setupFileDrop("docks-drop", "docks-file", "docks-file-name");
  setupFileDrop("priority-drop", "priority-file", "priority-file-name");
  setupTooltips();
  bindEvents();
  updatePercentageModePanels(optimizationContext());
  updateWorkspaceForSection("data");
  refreshStatus();
});
