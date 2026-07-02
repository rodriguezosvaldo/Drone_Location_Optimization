const API = "";

let activeJobPoll = null;
let currentMapPath = null;

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

function switchTab(section) {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.section === section);
  });
  document.querySelectorAll(".sidebar-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `section-${section}`);
  });
  if (section === "results") {
    loadOutputs();
  }
}

function setupNavigation() {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.section));
  });
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
      nameEl.textContent = e.dataTransfer.files[0].name;
    }
  });
  input.addEventListener("change", () => {
    nameEl.textContent = input.files[0]?.name || "No file selected";
  });
}

function selectedArea() {
  return document.querySelector('input[name="area-mode"]:checked')?.value;
}

function updatePriorityAreaOption(status) {
  const priorityRadio = $("area-priority");
  const priorityLabel = priorityRadio.closest(".radio-option");
  const hasPriority = status.priority_docks_loaded;

  priorityRadio.disabled = !hasPriority;
  priorityLabel.classList.toggle("disabled", !hasPriority);

  if (!hasPriority && priorityRadio.checked) {
    $("area-full").checked = true;
  }
}

function updatePriorityDocksFirstOption(status) {
  const toggle = $("priority-docks-first-toggle");
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

    updatePriorityAreaOption(status);
    updatePriorityDocksFirstOption(status);

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
      text.textContent = "Upload incidents, docks, and priority docks";
    }
  } catch {
    $("status-text").textContent = "Could not connect to server";
    $("status-dot").className = "status-dot offline";
  }
}

function showMap(relativePath) {
  currentMapPath = relativePath;
  const frame = $("map-frame");
  const placeholder = $("map-placeholder");

  frame.src = `/api/outputs/file/${relativePath}`;
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

function resetOptimizationPanel() {
  if (activeJobPoll) {
    clearInterval(activeJobPoll);
    activeJobPoll = null;
  }

  clearMap();

  $("optimization-results").innerHTML = "";
  $("optimization-results").classList.add("hidden");
  $("iterative-section").classList.add("hidden");
  $("job-status").classList.add("hidden");

  $("area-full").checked = true;
  $("peak-day-toggle").checked = false;
  $("priority-docks-first-toggle").checked = false;
  $("optimize-budget").value = 4;
  $("optimize-percentage").value = 100;
  $("increase-response-time-toggle").checked = false;
  $("increase-budget-toggle").checked = false;

  $("run-optimize-btn").disabled = false;
  $("run-iterative-btn").disabled = false;
  $("generate-map-btn").disabled = false;

  document.querySelectorAll(".tooltip-popup").forEach((el) => el.classList.add("hidden"));
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

function renderOptimizationResults(data) {
  const container = $("optimization-results");
  const result = data.result;
  const steps = data.steps || [result];

  let html = `
    <strong>Results</strong>
    <div>Covered: ${result.amount_incidents_covered} incidents (${result.coverage_rate}%)</div>
    <div>Docks used: ${result.amount_selected_docks} / budget ${result.k}</div>
  `;

  if (result.response_time_minutes != null) {
    html += `<div>Response time: ${result.response_time_minutes} min</div>`;
  }

  if (steps.length > 1) {
    html += `<div class="step-item">${steps.length} optimization steps completed.</div>`;
    steps.forEach((step, index) => {
      html += `
        <div class="step-item">
          Step ${index + 1}: ${step.amount_incidents_covered} covered · k=${step.k}
          ${step.response_time_minutes != null ? ` · ${step.response_time_minutes} min` : ""}
        </div>
      `;
    });
  }

  container.innerHTML = html;
  container.classList.remove("hidden");
  $("iterative-section").classList.remove("hidden");
}

function buildOptimizePayload(iterative) {
  return {
    area: selectedArea(),
    peak_day_only: $("peak-day-toggle").checked,
    budget: Number($("optimize-budget").value),
    open_priority_docks_first: $("priority-docks-first-toggle").checked,
    percentage_to_cover: Number($("optimize-percentage").value),
    iterative,
    increase_budget: iterative && $("increase-budget-toggle").checked,
    increase_response_time: iterative && $("increase-response-time-toggle").checked,
  };
}

function validateOptimizePayload(payload, iterative) {
  if (!payload.area) {
    showToast("Select an analysis area.", "error");
    return false;
  }
  if (!Number.isFinite(payload.budget) || payload.budget < 1) {
    showToast("Budget must be at least 1.", "error");
    return false;
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
  return true;
}

function handleOptimizationComplete(data) {
  showToast("Optimization completed.");
  renderOptimizationResults(data);
  const mapPath = data.map || data.outputs?.find((output) => output.endsWith(".html"));
  if (mapPath) {
    showMap(mapPath.replace(/^\//, ""));
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
  if (!priority) missing.push("priority docks");

  if (missing.length) {
    showToast(`Select all three files before uploading. Missing: ${missing.join(", ")}.`, "error");
    return;
  }

  const formData = new FormData();
  formData.append("incidents", incidents);
  formData.append("docks", docks);
  formData.append("priority_docks", priority);

  const btn = $("upload-btn");
  btn.disabled = true;

  try {
    const result = await api("/api/data/upload", { method: "POST", body: formData });
    showToast(result.message);
    await refreshStatus();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    btn.disabled = false;
  }
}

async function generateMap() {
  const area = selectedArea();
  if (!area) return;

  const btn = $("generate-map-btn");
  btn.disabled = true;

  try {
    const result = await api("/api/data/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        area,
        peak_day_only: $("peak-day-toggle").checked,
      }),
    });
    showToast(result.message);
    showMap(result.map);
    await refreshStatus();
    loadOutputs();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    btn.disabled = false;
  }
}

function startJobPolling(jobId) {
  const statusEl = $("job-status");
  statusEl.classList.remove("hidden");
  $("job-status-text").textContent = "Running optimization… this may take several minutes.";

  if (activeJobPoll) clearInterval(activeJobPoll);

  activeJobPoll = setInterval(async () => {
    try {
      const job = await api(`/api/optimize/jobs/${jobId}`);
      if (job.status === "completed") {
        clearInterval(activeJobPoll);
        activeJobPoll = null;
        statusEl.classList.add("hidden");
        handleOptimizationComplete(job.result);
      } else if (job.status === "failed") {
        clearInterval(activeJobPoll);
        activeJobPoll = null;
        statusEl.classList.add("hidden");
        showToast(job.error || "Optimization failed.", "error");
      }
    } catch (error) {
      clearInterval(activeJobPoll);
      activeJobPoll = null;
      statusEl.classList.add("hidden");
      showToast(error.message, "error");
    }
  }, 2500);
}

async function runOptimization(iterative = false) {
  const payload = buildOptimizePayload(iterative);
  if (!validateOptimizePayload(payload, iterative)) {
    return;
  }

  const btn = iterative ? $("run-iterative-btn") : $("run-optimize-btn");
  btn.disabled = true;
  $("run-optimize-btn").disabled = true;
  $("run-iterative-btn").disabled = true;

  const statusEl = $("job-status");
  if (!iterative) {
    statusEl.classList.remove("hidden");
    $("job-status-text").textContent = "Running optimization…";
  }

  try {
    const result = await api("/api/optimize/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (result.job_id) {
      showToast(result.message);
      startJobPolling(result.job_id);
      return;
    }

    statusEl.classList.add("hidden");
    handleOptimizationComplete(result);
  } catch (error) {
    statusEl.classList.add("hidden");
    showToast(error.message, "error");
  } finally {
    btn.disabled = false;
    $("run-optimize-btn").disabled = false;
    $("run-iterative-btn").disabled = false;
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
  setupTooltip("budget-info-btn", "budget-tooltip");

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".info-btn") && !e.target.closest(".tooltip-popup")) {
      document.querySelectorAll(".tooltip-popup").forEach((el) => el.classList.add("hidden"));
    }
  });
}

function bindEvents() {
  $("upload-btn").addEventListener("click", uploadAll);
  $("generate-map-btn").addEventListener("click", generateMap);
  $("run-optimize-btn").addEventListener("click", () => runOptimization(false));
  $("run-iterative-btn").addEventListener("click", () => runOptimization(true));
  $("delete-all-outputs-btn").addEventListener("click", deleteAllOutputs);
  $("optimization-refresh-btn").addEventListener("click", resetOptimizationPanel);
}

document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupFileDrop("incidents-drop", "incidents-file", "incidents-file-name");
  setupFileDrop("docks-drop", "docks-file", "docks-file-name");
  setupFileDrop("priority-drop", "priority-file", "priority-file-name");
  setupTooltips();
  bindEvents();
  refreshStatus();
});
