/* FlashWizard Web UI — Frontend */

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function $(sel, ctx = document) { return ctx.querySelector(sel); }
function $$(sel, ctx = document) { return [...ctx.querySelectorAll(sel)]; }

function openModal(id) {
  const m = $(`#${id}`);
  if (m) m.classList.add("active");
}
function closeModal(id) {
  const m = $(`#${id}`);
  if (m) m.classList.remove("active");
}

function appendLine(termEl, msg, level = "info") {
  const div = document.createElement("div");
  div.className = `line ${level}`;
  div.textContent = msg;
  termEl.appendChild(div);
  termEl.scrollTop = termEl.scrollHeight;
}

function streamTask(taskId, termEl, onDone) {
  termEl.classList.add("active");
  termEl.innerHTML = "";

  const src = new EventSource(`/api/stream/${taskId}`);
  src.onmessage = (e) => {
    if (!e.data || e.data === "{}") return;
    try {
      const data = JSON.parse(e.data);
      if (data.level === "done") {
        src.close();
        if (onDone) onDone(data.msg);
        return;
      }
      if (data.msg) appendLine(termEl, data.msg, data.level);
    } catch { /* ignore */ }
  };
  src.onerror = () => {
    src.close();
    appendLine(termEl, "Connection lost.", "error");
  };
}

async function api(url, opts = {}) {
  if (opts.body && typeof opts.body === "object") {
    opts.headers = { "Content-Type": "application/json", ...opts.headers };
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(url, opts);
  return res.json();
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", async () => {
  // Check tool status
  try {
    const status = await api("/api/status");
    const bar = $(".status-bar");
    for (const [tool, ok] of Object.entries(status)) {
      const pill = document.createElement("span");
      pill.className = `status-pill ${ok ? "ok" : "missing"}`;
      pill.textContent = tool;
      bar.appendChild(pill);
    }
  } catch { /* ignore */ }

  // Load devices for preset panel
  loadDevices();

  // Card clicks
  $$(".card[data-action]").forEach((card) => {
    card.addEventListener("click", () => {
      const action = card.dataset.action;
      openModal(`modal-${action}`);
      if (action === "logs") loadLogs();
    });
  });

  // Close buttons
  $$(".modal-close").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.closest(".modal-overlay").classList.remove("active");
    });
  });

  // Close on overlay click
  $$(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) overlay.classList.remove("active");
    });
  });
});

// ---------------------------------------------------------------------------
// Devices / presets
// ---------------------------------------------------------------------------

let devicesData = [];

async function loadDevices() {
  devicesData = await api("/api/devices");
  const list = $("#device-list");
  if (!list) return;
  list.innerHTML = "";
  devicesData.forEach((dev, i) => {
    const el = document.createElement("div");
    el.className = "device-item";
    el.dataset.index = i;
    el.innerHTML = `<div class="name">${dev.label}</div>
      <div class="meta">${dev.model} / ${dev.codename}</div>`;
    el.addEventListener("click", () => {
      $$(".device-item", list).forEach((d) => d.classList.remove("selected"));
      el.classList.add("selected");
      showDownloadOptions(dev);
    });
    list.appendChild(el);
  });
}

function showDownloadOptions(dev) {
  const container = $("#download-options");
  if (!container) return;
  const keys = [
    ["stock_url", "Stock firmware"],
    ["twrp_url", "TWRP recovery"],
    ["rom_url", "LineageOS ROM"],
    ["eos_url", "/e/OS ROM"],
    ["gapps_url", "GApps"],
  ];
  container.innerHTML = "";
  keys.forEach(([key, label]) => {
    if (!dev[key]) return;
    const lbl = document.createElement("label");
    lbl.innerHTML = `<input type="checkbox" name="dl" value="${key}" checked> ${label}`;
    container.appendChild(lbl);
  });
  container.style.display = "flex";
  container.style.flexWrap = "wrap";
  container.style.gap = "0.5rem";
  container.style.marginTop = "0.5rem";
  $("#btn-download").style.display = "inline-flex";
  $("#btn-download").dataset.deviceId = dev.id;
}

async function startDownload() {
  const btn = $("#btn-download");
  const deviceId = btn.dataset.deviceId;
  const selected = $$("#download-options input:checked").map((c) => c.value);
  if (!selected.length) return;

  btn.disabled = true;
  const term = $("#term-presets");
  const data = await api("/api/download", {
    method: "POST",
    body: { device_id: deviceId, selected },
  });
  streamTask(data.task_id, term, () => { btn.disabled = false; });
}

// ---------------------------------------------------------------------------
// Flash stock firmware
// ---------------------------------------------------------------------------

async function startFlashStock() {
  const path = $("#input-fw-zip").value.trim();
  if (!path) return alert("Enter a firmware ZIP path.");

  const btn = $("#btn-flash-stock");
  btn.disabled = true;
  const term = $("#term-flash-stock");
  const data = await api("/api/flash/stock", {
    method: "POST",
    body: { fw_zip: path },
  });
  streamTask(data.task_id, term, () => { btn.disabled = false; });
}

// ---------------------------------------------------------------------------
// Flash recovery
// ---------------------------------------------------------------------------

async function startFlashRecovery() {
  const path = $("#input-recovery-img").value.trim();
  if (!path) return alert("Enter a recovery .img path.");

  const btn = $("#btn-flash-recovery");
  btn.disabled = true;
  const term = $("#term-flash-recovery");
  const data = await api("/api/flash/recovery", {
    method: "POST",
    body: { recovery_img: path },
  });
  streamTask(data.task_id, term, () => { btn.disabled = false; });
}

// ---------------------------------------------------------------------------
// ADB sideload
// ---------------------------------------------------------------------------

async function startSideload() {
  const path = $("#input-sideload-zip").value.trim();
  const label = $("#input-sideload-label").value || "ROM";
  if (!path) return alert("Enter a ZIP file path.");

  const btn = $("#btn-sideload");
  btn.disabled = true;
  const term = $("#term-sideload");
  const data = await api("/api/sideload", {
    method: "POST",
    body: { zip_path: path, label },
  });
  streamTask(data.task_id, term, () => { btn.disabled = false; });
}

// ---------------------------------------------------------------------------
// Backup
// ---------------------------------------------------------------------------

async function startBackup() {
  const partitions = $$("#backup-parts input:checked").map((c) => c.value);
  const backupEfs = $("#backup-efs")?.checked || false;

  const btn = $("#btn-backup");
  btn.disabled = true;
  const term = $("#term-backup");
  const data = await api("/api/backup", {
    method: "POST",
    body: { partitions, backup_efs: backupEfs },
  });
  streamTask(data.task_id, term, () => { btn.disabled = false; });
}

// ---------------------------------------------------------------------------
// Detect device
// ---------------------------------------------------------------------------

async function startDetect() {
  const result = $("#detect-result");
  result.style.display = "block";
  result.innerHTML = "Detecting...";

  try {
    const data = await api("/api/detect");
    if (data.error) {
      result.innerHTML = `<span style="color:var(--yellow)">${data.error}</span>`;
      return;
    }
    let html = `<strong>Model:</strong> ${data.model}<br>
      <strong>Codename:</strong> ${data.codename}<br>`;
    if (data.match) {
      html += `<br><span style="color:var(--green)">Matched preset: ${data.match.label} (${data.match.id})</span>`;
    } else {
      html += `<br><span style="color:var(--yellow)">No matching preset found in devices.cfg</span>`;
    }
    result.innerHTML = html;
  } catch (e) {
    result.innerHTML = `<span style="color:var(--red)">Error: ${e.message}</span>`;
  }
}

// ---------------------------------------------------------------------------
// ROM updates
// ---------------------------------------------------------------------------

async function checkUpdates() {
  const btn = $("#btn-updates");
  btn.disabled = true;
  const term = $("#term-updates");
  const data = await api("/api/updates");
  streamTask(data.task_id, term, () => { btn.disabled = false; });
}

// ---------------------------------------------------------------------------
// Magisk
// ---------------------------------------------------------------------------

async function startMagisk() {
  const path = $("#input-magisk-boot").value.trim();
  if (!path) return alert("Enter a boot.img path.");

  const flashAfter = $("#magisk-flash-after")?.checked || false;
  const btn = $("#btn-magisk");
  btn.disabled = true;
  const term = $("#term-magisk");
  const data = await api("/api/magisk", {
    method: "POST",
    body: { boot_img: path, flash_after: flashAfter },
  });
  streamTask(data.task_id, term, () => { btn.disabled = false; });
}

// ---------------------------------------------------------------------------
// Full workflow
// ---------------------------------------------------------------------------

async function startWorkflow() {
  const btn = $("#btn-workflow");
  btn.disabled = true;
  const term = $("#term-workflow");
  const data = await api("/api/workflow", {
    method: "POST",
    body: {
      fw_zip: $("#wf-fw-zip").value.trim(),
      recovery_img: $("#wf-recovery").value.trim(),
      rom_zip: $("#wf-rom").value.trim(),
      gapps_zip: $("#wf-gapps").value.trim(),
    },
  });
  streamTask(data.task_id, term, () => { btn.disabled = false; });
}

// ---------------------------------------------------------------------------
// Logs viewer
// ---------------------------------------------------------------------------

async function loadLogs() {
  const list = $("#logs-list");
  list.innerHTML = "Loading...";
  const logs = await api("/api/logs");
  list.innerHTML = "";
  if (!logs.length) {
    list.innerHTML = '<div style="color:var(--text-dim); padding:0.5rem;">No logs found.</div>';
    return;
  }
  logs.forEach((log) => {
    const el = document.createElement("div");
    el.className = "device-item";
    const size = log.size > 1024 ? `${(log.size / 1024).toFixed(1)}K` : `${log.size}B`;
    el.innerHTML = `<div class="name">${log.name}</div><div class="meta">${size}</div>`;
    el.addEventListener("click", () => viewLog(log.name));
    list.appendChild(el);
  });
}

async function viewLog(name) {
  const term = $("#term-log-content");
  term.classList.add("active");
  term.innerHTML = "";
  const data = await api(`/api/logs/${encodeURIComponent(name)}`);
  if (data.error) {
    appendLine(term, data.error, "error");
    return;
  }
  data.content.split("\n").forEach((line) => {
    appendLine(term, line, "info");
  });
}

// ---------------------------------------------------------------------------
// File browser
// ---------------------------------------------------------------------------

let browserTargetInput = null;
let browserFilter = "";

function openBrowser(inputId, filter = "") {
  browserTargetInput = inputId;
  browserFilter = filter.toLowerCase();
  const current = $(`#${inputId}`).value.trim();
  const startPath = current ? current.substring(0, current.lastIndexOf("/")) || "/" : "";
  openModal("modal-browser");
  navigateTo(startPath || "");
}

async function navigateTo(path) {
  const entries = $("#browser-entries");
  entries.innerHTML = '<div style="padding:0.5rem; color:var(--text-dim);">Loading...</div>';

  const params = path ? `?path=${encodeURIComponent(path)}` : "";
  const data = await api(`/api/browse${params}`);

  if (data.error) {
    entries.innerHTML = `<div style="padding:0.5rem; color:var(--red);">${data.error}</div>`;
    return;
  }

  if (data.type === "file") {
    // File selected
    $(`#${browserTargetInput}`).value = data.path;
    closeModal("modal-browser");
    return;
  }

  $("#browser-path").value = data.path;
  entries.innerHTML = "";

  data.entries.forEach((entry) => {
    // Filter files by extension if set
    if (entry.type === "file" && browserFilter) {
      if (!entry.name.toLowerCase().endsWith(browserFilter)) return;
    }

    const el = document.createElement("div");
    el.className = "browser-entry";
    const icon = entry.type === "dir" ? "&#x1F4C1;" : "&#x1F4C4;";
    const size = entry.type === "file" && entry.size > 0
      ? (entry.size > 1048576 ? `${(entry.size / 1048576).toFixed(1)}M` : `${(entry.size / 1024).toFixed(1)}K`)
      : "";
    el.innerHTML = `<span class="icon">${icon}</span><span>${entry.name}</span><span class="size">${size}</span>`;
    el.addEventListener("click", () => {
      if (entry.type === "dir") {
        navigateTo(entry.path);
      } else {
        $(`#${browserTargetInput}`).value = entry.path;
        closeModal("modal-browser");
      }
    });
    entries.appendChild(el);
  });
}
