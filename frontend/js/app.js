const API = "";

const sections = {
  upload: {
    title: "Cargar datos",
    subtitle: "Sube archivos Excel de docks e incidentes, o usa los datos predeterminados del proyecto.",
  },
  single: {
    title: "Optimización simple",
    subtitle: "Ejecuta un modelo de optimización con parámetros personalizados.",
  },
  batch: {
    title: "Escenarios múltiples",
    subtitle: "Compara configuraciones de docks con barridos y análisis mensual.",
  },
  outputs: {
    title: "Resultados",
    subtitle: "Descarga mapas, gráficos y tablas generadas por las optimizaciones.",
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

async function refreshStatus() {
  try {
    const status = await api("/api/data/status");
    const dot = document.querySelector(".status-dot");
    const text = $("status-text");

    if (status.loaded) {
      dot.className = "status-dot online";
      text.textContent = `${status.docks_count} docks, ${status.incidents_count} incidentes cargados`;
    } else {
      dot.className = "status-dot offline";
      text.textContent = "Sin datos cargados";
    }
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

async function runSingleOptimization() {
  try {
    const result = await api("/api/optimize/single", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dock_locations_quantity: Number($("single-k").value),
        max_dock_coverage_capacity: Number($("single-capacity").value),
        generate_map: $("single-map").checked,
      }),
    });
    showToast("Optimización completada.");
    showResults(result);
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function runMinimizeDocks() {
  try {
    const result = await api("/api/optimize/minimize-docks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dock_locations_quantity: Number($("minimize-k").value),
        max_dock_coverage_capacity: Number($("minimize-capacity").value),
        generate_map: $("minimize-map").checked,
      }),
    });
    showToast("Minimización completada.");
    showResults(result);
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
        showToast("Optimización en lote completada.");
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

async function startBatchJob(endpoint, payload) {
  try {
    const result = await api(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    showToast(result.message);
    startJobPolling(result.job_id);
  } catch (error) {
    showToast(error.message, "error");
  }
}

function batchPayload() {
  return {
    k_min: Number($("batch-k-min").value),
    k_max: Number($("batch-k-max").value),
    max_dock_coverage_capacity: Number($("batch-capacity").value),
  };
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
  $("run-single-btn").addEventListener("click", runSingleOptimization);
  $("run-minimize-btn").addEventListener("click", runMinimizeDocks);
  $("run-no-fixed-btn").addEventListener("click", () => startBatchJob("/api/optimize/no-fixed", batchPayload()));
  $("run-fixed-btn").addEventListener("click", () =>
    startBatchJob("/api/optimize/fixed", {
      k_max: Number($("batch-k-max").value),
      max_dock_coverage_capacity: Number($("batch-capacity").value),
    })
  );
  $("run-compare-btn").addEventListener("click", () => startBatchJob("/api/optimize/compare-both", batchPayload()));
  $("run-monthly-btn").addEventListener("click", () =>
    startBatchJob("/api/optimize/by-month", {
      dock_locations_quantity: Number($("monthly-k").value),
      max_dock_coverage_capacity: Number($("batch-capacity").value),
    })
  );
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
