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

async function refreshStatus() {
  try {
    const status = await api("/api/data/status");
    const dot = $("status-dot");
    const text = $("status-text");

    updatePriorityAreaOption(status);

    if (status.loaded) {
      dot.className = status.analyzed ? "status-dot online" : "status-dot warning";
      if (status.analyzed) {
        const area = status.area_mode === "specific" ? "priority area" : "entire area";
        text.textContent = `${status.active_docks_count} docks, ${status.active_incidents_count} incidents (${area})`;
      } else {
        let msg = `${status.docks_count} docks, ${status.incidents_count} incidents loaded`;
        if (status.priority_docks_loaded) {
          msg += ` · ${status.priority_docks_count} priority docks`;
        }
        text.textContent = msg;
      }
    } else {
      dot.className = "status-dot offline";
      text.textContent = "No data loaded";
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

  frame.src = "";
  frame.classList.add("hidden");
  placeholder.classList.remove("hidden");
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

function showMapFromResult(result) {
  const mapPath = result.map || result.outputs?.find((o) => o.endsWith(".html"));
  if (mapPath) {
    showMap(mapPath.replace(/^\//, ""));
    switchTab("results");
  }
}

async function uploadAll() {
  const incidents = $("incidents-file").files[0];
  const docks = $("docks-file").files[0];
  const priority = $("priority-file").files[0];

  if (!incidents && !docks && !priority) {
    showToast("Select at least one file to upload.", "error");
    return;
  }

  if ((incidents || docks) && (!incidents || !docks)) {
    const missing = !incidents ? "incidents" : "docks";
    showToast(`Select both incidents and docks files, or upload only priority docks. Missing: ${missing}.`, "error");
    return;
  }

  const formData = new FormData();
  if (incidents) formData.append("incidents", incidents);
  if (docks) formData.append("docks", docks);
  if (priority) formData.append("priority_docks", priority);

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
  const area = document.querySelector('input[name="area-mode"]:checked')?.value;
  if (!area) return;

  const btn = $("generate-map-btn");
  btn.disabled = true;

  try {
    const result = await api("/api/data/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ area }),
    });
    showToast(result.message);
    showMap(result.map);
    switchTab("results");
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
        $("job-status-text").textContent = "Completed.";
        showToast("Optimization completed.");
        const htmlOutput = job.result?.outputs?.find((o) => o.endsWith(".html"));
        if (htmlOutput) showMap(htmlOutput);
        loadOutputs();
      } else if (job.status === "failed") {
        clearInterval(activeJobPoll);
        activeJobPoll = null;
        $("job-status-text").textContent = "Failed.";
        showToast(job.error || "Optimization failed.", "error");
      }
    } catch (error) {
      clearInterval(activeJobPoll);
      activeJobPoll = null;
      showToast(error.message, "error");
    }
  }, 2500);
}

async function runOptimization() {
  const payload = {
    dock_locations_quantity: Number($("optimize-k").value),
    use_specific_docks: $("optimize-priority-docks").checked,
    increase_budget: $("optimize-increase-budget").checked,
  };

  const btn = $("run-optimize-btn");
  btn.disabled = true;

  try {
    const result = await api("/api/optimize/maximize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (result.job_id) {
      showToast(result.message);
      startJobPolling(result.job_id);
      return;
    }

    showToast("Optimization completed.");
    showMapFromResult(result);
    loadOutputs();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    btn.disabled = false;
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
        <div>
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

function setupTooltip() {
  const btn = $("priority-info-btn");
  const tooltip = $("priority-tooltip");

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    tooltip.classList.toggle("hidden");
  });

  document.addEventListener("click", (e) => {
    if (!btn.contains(e.target) && !tooltip.contains(e.target)) {
      tooltip.classList.add("hidden");
    }
  });
}

function bindEvents() {
  $("upload-btn").addEventListener("click", uploadAll);
  $("generate-map-btn").addEventListener("click", generateMap);
  $("run-optimize-btn").addEventListener("click", runOptimization);
  $("delete-all-outputs-btn").addEventListener("click", deleteAllOutputs);
}

document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupFileDrop("incidents-drop", "incidents-file", "incidents-file-name");
  setupFileDrop("docks-drop", "docks-file", "docks-file-name");
  setupFileDrop("priority-drop", "priority-file", "priority-file-name");
  setupTooltip();
  bindEvents();
  refreshStatus();
});
