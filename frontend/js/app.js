const API = "";

const sections = {
  upload: {
    title: "Cargar datos",
    subtitle: "Sube archivos Excel o usa los datos predeterminados del proyecto.",
  },
  area: {
    title: "Área de análisis",
    subtitle: "Selecciona si analizar toda el área o solo la zona MetroSafe (como el menú principal del CLI).",
  },
  optimize: {
    title: "Optimización",
    subtitle: "Maximiza incidentes cubiertos con restricción de presupuesto k, igual que el menú de optimización del CLI.",
  },
  outputs: {
    title: "Resultados",
    subtitle: "Mapas y gráficos generados por el análisis y las optimizaciones.",
  },
};

let activeJobPoll = null;

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

function showResults(data) {
  $("results-json").textContent = JSON.stringify(data, null, 2);
  $("results-panel").classList.remove("hidden");
}

function hideResults() {
  $("results-panel").classList.add("hidden");
}

function updateAreaSummary(status) {
  const card = $("area-summary-card");
  const text = $("area-summary-text");

  if (!status.analyzed) {
    card.classList.add("hidden");
    return;
  }

  const areaLabel = status.area_mode === "specific" ? "Área MetroSafe específica" : "Área completa";
  text.textContent = `${areaLabel}: ${status.active_docks_count} docks, ${status.active_incidents_count} incidentes (día pico).`;
  card.classList.remove("hidden");
}

async function refreshStatus() {
  try {
    const status = await api("/api/data/status");
    const dot = document.querySelector(".status-dot");
    const text = $("status-text");

    if (status.loaded) {
      dot.className = status.analyzed ? "status-dot online" : "status-dot warning";
      if (status.analyzed) {
        const area = status.area_mode === "specific" ? "área MetroSafe" : "área completa";
        text.textContent = `${status.active_docks_count} docks, ${status.active_incidents_count} incidentes (${area})`;
      } else {
        text.textContent = `${status.docks_count} docks, ${status.incidents_count} incidentes — selecciona área`;
      }
    } else {
      dot.className = "status-dot offline";
      text.textContent = "Sin datos cargados";
    }

    updateAreaSummary(status);
  } catch {
    $("status-text").textContent = "No se pudo conectar al servidor";
  }
}

function setupNavigation() {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const section = btn.dataset.section;
      document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      $(`section-${section}`).classList.add("active");
      $("page-title").textContent = sections[section].title;
      $("page-subtitle").textContent = sections[section].subtitle;
      if (section === "outputs") loadOutputs();
    });
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
    nameEl.textContent = input.files[0]?.name || "Ningún archivo seleccionado";
  });
}

async function uploadFile(endpoint, inputId) {
  const input = $(inputId);
  if (!input.files.length) {
    showToast("Selecciona un archivo primero.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", input.files[0]);

  try {
    const result = await api(endpoint, { method: "POST", body: formData });
    showToast(result.message);
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function loadData() {
  const useDefaults = document.querySelector('input[name="data-source"]:checked').value === "defaults";
  try {
    const result = await api("/api/data/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ use_defaults: useDefaults }),
    });
    showToast(result.message);
    showResults(result);
    await refreshStatus();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function analyzeArea(area) {
  try {
    const result = await api("/api/data/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ area }),
    });
    showToast(result.message);
    showResults(result);
    await refreshStatus();
    loadOutputs();
  } catch (error) {
    showToast(error.message, "error");
  }
}

function startJobPolling(jobId) {
  $("job-panel").classList.remove("hidden");
  $("job-status-text").textContent = "En ejecución... puede tardar varios minutos.";

  if (activeJobPoll) clearInterval(activeJobPoll);

  activeJobPoll = setInterval(async () => {
    try {
      const job = await api(`/api/optimize/jobs/${jobId}`);
      if (job.status === "completed") {
        clearInterval(activeJobPoll);
        activeJobPoll = null;
        $("job-status-text").textContent = "Completado.";
        showToast("Optimización completada.");
        showResults(job.result);
        loadOutputs();
      } else if (job.status === "failed") {
        clearInterval(activeJobPoll);
        activeJobPoll = null;
        $("job-status-text").textContent = "Error.";
        showToast(job.error || "La optimización falló.", "error");
      }
    } catch (error) {
      clearInterval(activeJobPoll);
      activeJobPoll = null;
      showToast(error.message, "error");
    }
  }, 2500);
}

async function runOptimization(useSpecificDocks) {
  const kInput = useSpecificDocks ? $("specific-k") : $("maximize-k");
  const budgetInput = useSpecificDocks ? $("specific-increase-budget") : $("maximize-increase-budget");

  const payload = {
    dock_locations_quantity: Number(kInput.value),
    use_specific_docks: useSpecificDocks,
    increase_budget: budgetInput.checked,
  };

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

    showToast("Optimización completada.");
    showResults(result);
    loadOutputs();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function loadOutputs() {
  const list = $("outputs-list");
  list.innerHTML = "<p class='hint'>Cargando...</p>";

  try {
    const data = await api("/api/outputs");
    if (!data.files.length) {
      list.innerHTML = "<p class='hint'>No hay archivos generados todavía.</p>";
      return;
    }

    list.innerHTML = "";
    data.files.forEach((file) => {
      const item = document.createElement("div");
      item.className = "output-item";
      item.innerHTML = `
        <div>
          <strong>${file.name}</strong><br>
          <span>${file.path}</span>
        </div>
        <div class="output-actions">
          <button class="btn secondary preview-btn">Ver</button>
          <a class="btn secondary" href="/api/outputs/file/${file.path}" download="${file.name}">Descargar</a>
        </div>
      `;
      item.querySelector(".preview-btn").addEventListener("click", () => previewFile(file));
      list.appendChild(item);
    });
  } catch (error) {
    list.innerHTML = `<p class='hint'>${error.message}</p>`;
  }
}

function previewFile(file) {
  const preview = $("preview-content");
  const card = $("preview-card");
  const url = `/api/outputs/file/${file.path}`;

  if (file.path.endsWith(".html")) {
    preview.innerHTML = `<iframe src="${url}" title="${file.name}"></iframe>`;
  } else if (file.path.endsWith(".png") || file.path.endsWith(".jpg") || file.path.endsWith(".jpeg")) {
    preview.innerHTML = `<img src="${url}" alt="${file.name}">`;
  } else {
    preview.innerHTML = `<p class="hint">Vista previa no disponible. Usa descargar.</p>`;
  }

  card.classList.remove("hidden");
}

function bindEvents() {
  $("upload-docks-btn").addEventListener("click", () => uploadFile("/api/data/upload/docks", "docks-file"));
  $("upload-incidents-btn").addEventListener("click", () => uploadFile("/api/data/upload/incidents", "incidents-file"));
  $("load-data-btn").addEventListener("click", loadData);
  $("analyze-full-btn").addEventListener("click", () => analyzeArea("full"));
  $("analyze-specific-btn").addEventListener("click", () => analyzeArea("specific"));
  $("run-maximize-btn").addEventListener("click", () => runOptimization(false));
  $("run-specific-btn").addEventListener("click", () => runOptimization(true));
  $("refresh-outputs-btn").addEventListener("click", loadOutputs);
  $("close-results-btn").addEventListener("click", hideResults);
}

document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupFileDrop("docks-drop", "docks-file", "docks-file-name");
  setupFileDrop("incidents-drop", "incidents-file", "incidents-file-name");
  bindEvents();
  refreshStatus();
});
