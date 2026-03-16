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
