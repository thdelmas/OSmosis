/* Osmosis Web UI — Frontend */

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
  // Only auto-scroll if user is already at the bottom (within 30px)
  const atBottom = (termEl.scrollHeight - termEl.scrollTop - termEl.clientHeight) < 30;
  termEl.appendChild(div);
  if (atBottom) termEl.scrollTop = termEl.scrollHeight;
}

function streamTask(taskId, termEl, onDone, opts = {}) {
  termEl.classList.add("active");
  termEl.innerHTML = "";

  // Add abort button
  let abortControls = null;
  if (!opts.noAbort) {
    abortControls = document.createElement("div");
    abortControls.className = "terminal-controls";
    abortControls.innerHTML = `<button class="btn-abort" data-task="${taskId}">${t("btn.abort") || "Abort"}</button>`;
    abortControls.querySelector(".btn-abort").addEventListener("click", async () => {
      await api(`/api/task/${taskId}/cancel`, { method: "POST" });
      abortControls.querySelector(".btn-abort").disabled = true;
      abortControls.querySelector(".btn-abort").textContent = t("aborting") || "Aborting...";
    });
    termEl.parentElement.insertBefore(abortControls, termEl.nextSibling);
  }

  // If progress mode, hide terminal and show a progress panel instead
  let progressPanel = null;
  if (opts.progress) {
    termEl.classList.add("progress-hidden");
    progressPanel = createProgressPanel(termEl, opts.progressLabel || "");
  }

  const src = new EventSource(`/api/stream/${taskId}`);
  src.onmessage = (e) => {
    if (!e.data || e.data === "{}") return;
    try {
      const data = JSON.parse(e.data);
      if (data.level === "done") {
        src.close();
        if (abortControls) abortControls.remove();
        if (progressPanel) finalizeProgress(progressPanel, data.msg);
        if (onDone) onDone(data.msg);
        return;
      }
      if (data.msg) {
        appendLine(termEl, data.msg, data.level);
        if (progressPanel) updateProgress(progressPanel, data.msg, data.level);
      }
    } catch { /* ignore */ }
  };
  src.onerror = () => {
    src.close();
    if (abortControls) abortControls.remove();
    if (progressPanel) finalizeProgress(progressPanel, "error");
    appendLine(termEl, t("connection.lost"), "error");
  };
}

// ---------------------------------------------------------------------------
// Progress panel for download tasks
// ---------------------------------------------------------------------------

function createProgressPanel(termEl, label) {
  const panel = document.createElement("div");
  panel.className = "progress-panel";
  panel.innerHTML = `
    <div class="progress-header">
      <div class="progress-filename">${label || t("progress.downloading")}</div>
      <div class="progress-status">${t("progress.preparing")}</div>
    </div>
    <div class="progress-bar-track">
      <div class="progress-bar-fill" style="width:0%"></div>
    </div>
    <div class="progress-stats">
      <span class="progress-percent"></span>
      <span class="progress-speed"></span>
      <span class="progress-eta"></span>
      <span class="progress-size"></span>
    </div>
    <button class="btn btn-link progress-toggle-btn" type="button">${t("progress.show.terminal")}</button>
  `;
  termEl.parentElement.insertBefore(panel, termEl);

  panel.querySelector(".progress-toggle-btn").addEventListener("click", () => {
    const expanded = termEl.classList.toggle("progress-expanded");
    panel.querySelector(".progress-toggle-btn").textContent =
      expanded ? t("progress.hide.terminal") : t("progress.show.terminal");
  });

  return { el: panel, percent: 0, phase: "init" };
}

function updateProgress(pp, msg, level) {
  const panel = pp.el;
  const statusEl = panel.querySelector(".progress-status");
  const fillEl = panel.querySelector(".progress-bar-fill");
  const percentEl = panel.querySelector(".progress-percent");
  const speedEl = panel.querySelector(".progress-speed");
  const etaEl = panel.querySelector(".progress-eta");
  const sizeEl = panel.querySelector(".progress-size");
  const filenameEl = panel.querySelector(".progress-filename");

  // Detect "Downloading: filename"
  const dlMatch = msg.match(/^Downloading:\s*(.+)/i);
  if (dlMatch) {
    filenameEl.textContent = dlMatch[1];
    statusEl.textContent = t("progress.downloading");
    pp.phase = "download";
    return;
  }

  // Detect file size from wget: "Length: 206835872 (197M)"
  const sizeMatch = msg.match(/^Length:\s*\d+\s*\(([^)]+)\)/);
  if (sizeMatch) {
    sizeEl.textContent = sizeMatch[1];
    return;
  }

  // Detect wget giga progress: "32768K ........ ........ 32% 2,67M 1m52s"
  const wgetMatch = msg.match(/(\d+)%\s+([\d.,]+[KMG]?)\s+(\S+)\s*$/);
  if (wgetMatch) {
    const pct = parseInt(wgetMatch[1], 10);
    pp.percent = pct;
    fillEl.style.width = pct + "%";
    percentEl.textContent = pct + "%";
    speedEl.textContent = wgetMatch[2] + "/s";
    etaEl.textContent = wgetMatch[3];
    statusEl.textContent = t("progress.downloading");
    pp.phase = "download";
    return;
  }

  // Detect dd write progress: "DDPROGRESS:45:247 MB/s:1m30s:12345/67890"
  const ddMatch = msg.match(/^DDPROGRESS:(\d+):([^:]*):([^:]*):(.*)$/);
  if (ddMatch) {
    const pct = parseInt(ddMatch[1], 10);
    pp.percent = pct;
    fillEl.style.width = pct + "%";
    percentEl.textContent = pct + "%";
    speedEl.textContent = ddMatch[2] || "";
    etaEl.textContent = ddMatch[3] ? "ETA " + ddMatch[3] : "";
    statusEl.textContent = t("progress.writing") || "Writing to device...";
    pp.phase = "writing";
    return;
  }

  // Detect post-write verification progress: "VERIFYPROGRESS:45:12345/67890"
  const verifyMatch = msg.match(/^VERIFYPROGRESS:(\d+):/);
  if (verifyMatch) {
    const pct = parseInt(verifyMatch[1], 10);
    pp.percent = pct;
    fillEl.style.width = pct + "%";
    percentEl.textContent = pct + "%";
    speedEl.textContent = "";
    etaEl.textContent = "";
    statusEl.textContent = t("progress.verifying") || "Verifying...";
    pp.phase = "verify";
    return;
  }

  // Detect SHA256 line (means download finished, verifying)
  if (msg.startsWith("SHA256:")) {
    fillEl.style.width = "100%";
    percentEl.textContent = "100%";
    speedEl.textContent = "";
    etaEl.textContent = "";
    statusEl.textContent = t("progress.verifying");
    pp.phase = "verify";
    return;
  }

  // Detect IPFS pinning
  if (msg.includes("Pinning to IPFS")) {
    statusEl.textContent = t("progress.pinning");
    pp.phase = "pin";
    return;
  }

  // Detect "Saved to:" or success
  if (level === "success" && (msg.includes("Saved to:") || msg.includes("saved"))) {
    statusEl.textContent = t("progress.complete");
    pp.phase = "done";
    return;
  }

  // Detect errors
  if (level === "error") {
    statusEl.textContent = msg;
    statusEl.style.color = "var(--red)";
    pp.phase = "error";
    return;
  }
}

function finalizeProgress(pp, status) {
  const panel = pp.el;
  const fillEl = panel.querySelector(".progress-bar-fill");
  const statusEl = panel.querySelector(".progress-status");
  const percentEl = panel.querySelector(".progress-percent");
  const speedEl = panel.querySelector(".progress-speed");
  const etaEl = panel.querySelector(".progress-eta");

  speedEl.textContent = "";
  etaEl.textContent = "";

  if (status === "done") {
    fillEl.style.width = "100%";
    percentEl.textContent = "100%";
    statusEl.textContent = t("progress.complete");
    statusEl.style.color = "var(--green)";
    panel.classList.add("progress-done");
  } else {
    statusEl.textContent = t("progress.failed");
    statusEl.style.color = "var(--red)";
    panel.classList.add("progress-error");
    // Auto-expand terminal on error so user can see what went wrong
    const termEl = panel.nextElementSibling;
    if (termEl) {
      termEl.classList.add("progress-expanded");
      panel.querySelector(".progress-toggle-btn").textContent = t("progress.hide.terminal");
    }
  }
}

function removeProgressPanel(termEl) {
  const panel = termEl.previousElementSibling;
  if (panel && panel.classList.contains("progress-panel")) {
    panel.remove();
  }
  termEl.classList.remove("progress-hidden", "progress-expanded");
}

// ---------------------------------------------------------------------------
// Inline validation (replaces alert())
// ---------------------------------------------------------------------------

function showInlineError(inputEl, msg) {
  clearInlineError(inputEl);
  const err = document.createElement("div");
  err.className = "inline-error";
  err.textContent = msg;
  err.dataset.forInput = inputEl.id || "";
  inputEl.style.borderColor = "var(--red)";
  inputEl.parentElement.appendChild(err);
  // Auto-clear on next input
  const handler = () => { clearInlineError(inputEl); inputEl.removeEventListener("input", handler); };
  inputEl.addEventListener("input", handler);
  return false;
}

function clearInlineError(inputEl) {
  inputEl.style.borderColor = "";
  const existing = inputEl.parentElement.querySelector(".inline-error");
  if (existing) existing.remove();
}

// ---------------------------------------------------------------------------
// Confirm dialog (replaces confirm())
// ---------------------------------------------------------------------------

function showConfirm({ icon, title, body, details, confirmText, cancelText, onConfirm, onCancel, danger }) {
  const container = document.getElementById("confirm-container");
  const overlay = document.createElement("div");
  overlay.className = "confirm-overlay";
  overlay.innerHTML = `
    <div class="confirm-dialog">
      <div class="confirm-icon">${icon || "&#x26A0;"}</div>
      <div class="confirm-title">${title || "Are you sure?"}</div>
      <div class="confirm-body">${body || ""}</div>
      ${details ? `<div class="confirm-details">${details}</div>` : ""}
      <div class="confirm-actions">
        <button class="btn btn-secondary confirm-cancel">${cancelText || t("btn.cancel") || "Cancel"}</button>
        <button class="btn ${danger ? "btn-danger" : "btn-primary"} confirm-ok" style="${danger ? "background:var(--red);" : ""}">${confirmText || t("btn.confirm") || "Confirm"}</button>
      </div>
    </div>`;
  overlay.querySelector(".confirm-cancel").addEventListener("click", () => {
    overlay.remove();
    if (onCancel) onCancel();
  });
  overlay.querySelector(".confirm-ok").addEventListener("click", () => {
    overlay.remove();
    if (onConfirm) onConfirm();
  });
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) { overlay.remove(); if (onCancel) onCancel(); }
  });
  document.addEventListener("keydown", function handler(e) {
    if (e.key === "Escape") { overlay.remove(); if (onCancel) onCancel(); document.removeEventListener("keydown", handler); }
  });
  container.appendChild(overlay);
  overlay.querySelector(".confirm-ok").focus();
}

// ---------------------------------------------------------------------------
// Completion screen builder
// ---------------------------------------------------------------------------

function showCompletion(stepEl, { icon, title, subtitle, summary, actions }) {
  // Hide the terminal and other step content
  const screen = document.createElement("div");
  screen.className = "completion-screen";
  let summaryHtml = "";
  if (summary && summary.length) {
    summaryHtml = `<div class="completion-summary">${summary.map(
      (r) => `<div class="summary-row"><span class="summary-label">${r.label}</span><span class="summary-value">${r.value}</span></div>`
    ).join("")}</div>`;
  }
  let actionsHtml = "";
  if (actions && actions.length) {
    actionsHtml = `<div class="completion-actions">${actions.map(
      (a) => `<button class="btn ${a.primary ? "btn-primary" : "btn-secondary"}" data-action="${a.id}">${a.label}</button>`
    ).join("")}</div>`;
  }
  screen.innerHTML = `
    <div class="completion-icon">${icon || "&#x2705;"}</div>
    <div class="completion-title">${title || "Done!"}</div>
    <div class="completion-subtitle">${subtitle || ""}</div>
    ${summaryHtml}
    ${actionsHtml}`;

  // Bind action buttons
  if (actions) {
    actions.forEach((a) => {
      const btn = screen.querySelector(`[data-action="${a.id}"]`);
      if (btn && a.onClick) btn.addEventListener("click", a.onClick);
    });
  }

  stepEl.appendChild(screen);
  return screen;
}

// ---------------------------------------------------------------------------
// Session state persistence
// ---------------------------------------------------------------------------

function saveWizardState() {
  try {
    const state = {
      detectedDevice,
      selectedCategory,
      currentStep: $$(".wizard-step.active").map((s) => s.id)[0] || "step-category",
      mode: $("#advanced-mode").style.display === "block" ? "advanced" : "guided",
    };
    sessionStorage.setItem("fw-wizard-state", JSON.stringify(state));
  } catch {}
}

function restoreWizardState() {
  try {
    const raw = sessionStorage.getItem("fw-wizard-state");
    if (!raw) return;
    const state = JSON.parse(raw);
    if (state.detectedDevice) {
      detectedDevice = state.detectedDevice;
      const name = detectedDevice.match ? detectedDevice.match.label : (detectedDevice.display_name || detectedDevice.model || "");
      if (name) {
        const infoText = `${t("your.device")}: <strong>${name}</strong> (${detectedDevice.model})`;
        const goalInfo = $("#goal-device-info");
        const installInfo = $("#install-device-info");
        if (goalInfo) goalInfo.innerHTML = infoText;
        if (installInfo) installInfo.innerHTML = infoText;
        if (detectedDevice.match) buildOsChoices(detectedDevice.match);
        else if (detectedDevice.codename) searchAvailableRoms(detectedDevice.codename, detectedDevice.model);
      }
    }
    if (state.selectedCategory) {
      selectedCategory = state.selectedCategory;
      // Re-filter goal cards
      const goalGrid = $("#goal-grid");
      if (goalGrid) {
        $$(".goal-card[data-goal]", goalGrid).forEach((card) => {
          const categories = (card.dataset.categories || "").split(",");
          card.style.display = categories.includes(selectedCategory) ? "" : "none";
        });
      }
    }
    if (state.mode === "advanced") {
      showAdvanced();
    } else if (state.currentStep && state.currentStep !== "step-category") {
      guidedGoTo(state.currentStep);
    }
  } catch {}
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
// Tool help popover
// ---------------------------------------------------------------------------

const TOOL_INFO = {
  adb:      { desc: "status.adb.desc",      install: "sudo apt install adb" },
  heimdall: { desc: "status.heimdall.desc",  install: "sudo apt install heimdall-flash" },
  wget:     { desc: "status.wget.desc",      install: "sudo apt install wget" },
  curl:     { desc: "status.curl.desc",      install: "sudo apt install curl" },
  lz4:      { desc: "status.lz4.desc",       install: "sudo apt install lz4" },
  ipfs:     { desc: "status.ipfs.desc",      install: "https://docs.ipfs.tech/install/command-line/" },
  dnsmasq:  { desc: "status.dnsmasq.desc",  install: "sudo apt install dnsmasq" },
};

function showToolHelp(tool) {
  // Remove any existing popover
  const old = $("#tool-help-popover");
  if (old) old.remove();

  const info = TOOL_INFO[tool];
  if (!info) return;

  const pop = document.createElement("div");
  pop.id = "tool-help-popover";
  pop.innerHTML = `
    <div class="tool-help-header">
      <strong>${tool}</strong>
      <button class="tool-help-close" aria-label="Close">&times;</button>
    </div>
    <p>${t(info.desc)}</p>
    <div class="tool-help-actions">
      <button class="btn btn-primary btn-sm tool-install-btn">${t("status.install.now")}</button>
    </div>
    <div class="terminal tool-install-term"></div>`;

  pop.querySelector(".tool-help-close").addEventListener("click", () => pop.remove());

  pop.querySelector(".tool-install-btn").addEventListener("click", async () => {
    const btn = pop.querySelector(".tool-install-btn");
    const term = pop.querySelector(".tool-install-term");
    btn.disabled = true;
    btn.textContent = t("status.installing");
    term.classList.add("active");
    term.innerHTML = "";

    try {
      const data = await api("/api/install-tool", {
        method: "POST",
        body: { tool },
      });
      if (data.error) {
        appendLine(term, data.error, "error");
        btn.disabled = false;
        btn.textContent = t("status.install.now");
        return;
      }
      streamTask(data.task_id, term, async (status) => {
        if (status === "done") {
          // Refresh status pills
          await refreshStatusBar();
          // Auto-close popover after success
          setTimeout(() => pop.remove(), 1500);
        } else {
          btn.disabled = false;
          btn.textContent = t("status.install.now");
        }
      });
    } catch (e) {
      appendLine(term, String(e), "error");
      btn.disabled = false;
      btn.textContent = t("status.install.now");
    }
  });

  // Close on outside click
  setTimeout(() => {
    const handler = (e) => {
      if (!pop.contains(e.target)) { pop.remove(); document.removeEventListener("click", handler); }
    };
    document.addEventListener("click", handler);
  }, 10);

  $(".status-bar").appendChild(pop);
}

async function refreshStatusBar() {
  try {
    const status = await api("/api/status");
    const bar = $(".status-bar");
    // Remove old pills (keep popover if open)
    const popover = $("#tool-help-popover");
    bar.querySelectorAll(".status-pill").forEach((p) => p.remove());
    for (const [tool, ok] of Object.entries(status)) {
      const pill = document.createElement("span");
      pill.className = `status-pill ${ok ? "ok" : "missing"}`;
      pill.textContent = tool;
      if (!ok) {
        pill.style.cursor = "pointer";
        pill.title = t("status.tap");
        pill.addEventListener("click", () => showToolHelp(tool));
      }
      bar.insertBefore(pill, popover);
    }
  } catch { /* ignore */ }
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", async () => {
  // Check tool status and disable advanced cards for missing tools
  let toolStatus = {};
  try {
    toolStatus = await api("/api/status");
    const bar = $(".status-bar");
    for (const [tool, ok] of Object.entries(toolStatus)) {
      const pill = document.createElement("span");
      pill.className = `status-pill ${ok ? "ok" : "missing"}`;
      pill.textContent = tool;
      if (!ok) {
        pill.style.cursor = "pointer";
        pill.title = t("status.tap");
        pill.addEventListener("click", () => showToolHelp(tool));
      }
      bar.appendChild(pill);
    }
  } catch { /* ignore */ }

  // Map advanced cards to their required tools
  const cardToolDeps = {
    "flash-stock": ["heimdall"],
    "flash-recovery": ["heimdall"],
    "sideload": ["adb"],
    "detect": ["adb"],
    "backup": ["adb"],
    "workflow": ["heimdall", "adb"],
    "magisk": ["adb"],
    "updates": ["curl"],
    "bootable": [],
    "pxe": ["dnsmasq"],
    "presets": ["wget"],
    "logs": [],
    "ipfs": [],
    "diagnostics": ["adb"],
    "community": [],
    "changelog": ["curl"],
    "companion": [],
  };

  $$(".card[data-action]").forEach((card) => {
    const action = card.dataset.action;
    const deps = cardToolDeps[action] || [];
    const missing = deps.filter((d) => !toolStatus[d]);
    if (missing.length) {
      card.classList.add("card-disabled");
      const badge = document.createElement("span");
      badge.className = "card-badge badge-missing";
      badge.textContent = `${t("needs") || "Needs"} ${missing.join(", ")}`;
      card.querySelector(".card-header").appendChild(badge);
    }
  });

  // i18n: build language dropdown and apply translations
  initI18n();

  // Load devices for preset panel
  loadDevices();

  // Card clicks
  $$(".card[data-action]").forEach((card) => {
    card.addEventListener("click", () => {
      if (card.classList.contains("card-disabled")) return;
      const action = card.dataset.action;
      openModal(`modal-${action}`);
      if (action === "logs") loadLogs();
      if (action === "ipfs") loadIpfsIndex();
      if (action === "bootable") refreshBlockDevices();
      if (action === "pxe") refreshInterfaces();
      if (action === "companion") loadCompanionTools();
      if (action === "cfw-builder") initCfwBuilder();
      if (action === "registry") loadRegistry();
      if (action === "recovery-guide") loadRecoveryGuides();
      if (action === "scooter-backup") loadScooterBackups();
      if (action === "diagnostics") loadDiagnostics();
      if (action === "os-builder") { osBuilderInit(); showGuided(); guidedGoTo("step-os-builder"); return; }
      if (action === "community") {
        // Pre-fill codename if device was detected
        if (detectedDevice) {
          const input = $("#community-codename");
          if (input) input.value = detectedDevice.codename || detectedDevice.model || "";
        }
      }
      if (action === "changelog") {
        // Pre-fill codename if device was detected
        if (detectedDevice) {
          const input = $("#changelog-codename");
          if (input) input.value = detectedDevice.codename || detectedDevice.model || "";
        }
      }
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

  // Close modals on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const open = $(".modal-overlay.active");
      if (open) open.classList.remove("active");
    }
  });

  // Category cards: click + keyboard
  $$(".goal-card[data-category]").forEach((card) => {
    const cat = card.dataset.category;
    card.addEventListener("click", () => guidedPickCategory(cat));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); guidedPickCategory(cat); }
    });
  });

  // Goal cards: click + keyboard (Enter/Space)
  $$(".goal-card[data-goal]").forEach((card) => {
    const goal = card.dataset.goal;
    card.addEventListener("click", () => guidedPickGoal(goal));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        guidedPickGoal(goal);
      }
    });
  });

  // Keyboard shortcuts for guided mode
  document.addEventListener("keydown", (e) => {
    // Skip if user is typing in an input/select/textarea
    if (e.target.matches("input, select, textarea")) return;
    // Skip if a modal or confirm dialog is open
    if ($(".modal-overlay.active") || $(".confirm-overlay")) return;

    const activeStep = $(".wizard-step.active");
    if (!activeStep) return;

    // Step 2 (category): number keys to pick category
    if (activeStep.id === "step-category") {
      const cats = ["phone", "computer", "network", "car", "marine", "iot", "console", "gps", "scooter"];
      const idx = parseInt(e.key) - 1;
      if (idx >= 0 && idx < cats.length) guidedPickCategory(cats[idx]);
    }

    // Step 3 (goal): number keys to pick visible goals
    if (activeStep.id === "step-goal") {
      const visibleGoals = $$(".goal-card[data-goal]", activeStep).filter((c) => c.style.display !== "none");
      const idx = parseInt(e.key) - 1;
      if (idx >= 0 && idx < visibleGoals.length) {
        guidedPickGoal(visibleGoals[idx].dataset.goal);
      }
    }

    // Any step: Backspace or 'b' to go back
    if (e.key === "Backspace" || e.key === "b") {
      const backBtn = $(".step-nav .btn-secondary", activeStep);
      if (backBtn) backBtn.click();
    }

    // Step 1: Enter to detect
    if (activeStep.id === "step-connect" && e.key === "Enter") {
      const detectBtn = $("#btn-detect-guided");
      if (detectBtn && !detectBtn.disabled) detectBtn.click();
    }
  });

  // Restore wizard state from sessionStorage
  restoreWizardState();
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
    ["stock_url", t("dl.stock_url")],
    ["twrp_url", t("dl.twrp_url")],
    ["rom_url", t("dl.rom_url")],
    ["eos_url", t("dl.eos_url")],
    ["gapps_url", t("dl.gapps_url")],
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
  streamTask(data.task_id, term, () => { removeProgressPanel(term); btn.disabled = false; }, { progress: true });
}

// ---------------------------------------------------------------------------
// Flash stock firmware
// ---------------------------------------------------------------------------

async function startFlashStock() {
  const pathInput = $("#input-fw-zip");
  const path = pathInput.value.trim();
  if (!path) return showInlineError(pathInput, t("error.path.required") || "Please enter a firmware ZIP path.");

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
  const recInput = $("#input-recovery-img");
  const path = recInput.value.trim();
  if (!path) return showInlineError(recInput, t("error.path.required") || "Please enter a recovery .img path.");

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
  const sideInput = $("#input-sideload-zip");
  const path = sideInput.value.trim();
  const label = $("#input-sideload-label").value || "ROM";
  if (!path) return showInlineError(sideInput, t("error.path.required") || "Please enter a ZIP file path.");

  const btn = $("#btn-sideload");
  btn.disabled = true;
  const term = $("#term-sideload");
  try {
    const data = await api("/api/sideload", {
      method: "POST",
      body: { zip_path: path, label },
    });
    if (data.error) {
      term.classList.add("active");
      appendLine(term, data.error, "error");
      btn.disabled = false;
      return;
    }
    streamTask(data.task_id, term, () => { btn.disabled = false; });
  } catch (e) {
    term.classList.add("active");
    appendLine(term, String(e), "error");
    btn.disabled = false;
  }
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
    let html = `<strong>${t("model")}:</strong> ${data.model}<br>
      <strong>${t("codename")}:</strong> ${data.codename}<br>`;
    if (data.match) {
      html += `<br><span style="color:var(--green)">${t("matched.preset")}: ${data.match.label} (${data.match.id})</span>`;
    } else {
      html += `<br><span style="color:var(--yellow)">${t("no.matching.preset")}</span>`;
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
    list.innerHTML = `<div style="color:var(--text-dim); padding:0.5rem;">${t("nologs")}</div>`;
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

// ===========================================================================
// ACCESSIBILITY: Font size & theme
// ===========================================================================

const fontSizes = ["", "font-large", "font-xl"];
let fontIndex = 0;

function cycleFontSize() {
  document.body.classList.remove(...fontSizes.filter(Boolean));
  fontIndex = (fontIndex + 1) % fontSizes.length;
  if (fontSizes[fontIndex]) document.body.classList.add(fontSizes[fontIndex]);
  try { localStorage.setItem("fw-font", fontIndex); } catch {}
  // Update button to show current state
  const labels = ["Normal", "Large", "Extra large"];
  const btn = $("#btn-font-size");
  if (btn) btn.title = `Text size: ${labels[fontIndex]}`;
}

function toggleTheme() {
  const isLight = document.body.classList.toggle("theme-light");
  try { localStorage.setItem("fw-theme", isLight ? "light" : "dark"); } catch {}
  const icon = $("#theme-icon");
  if (icon) icon.innerHTML = isLight ? "&#x1F319;" : "&#x2600;";
}

// Restore preferences on load
(function restorePrefs() {
  try {
    const savedFont = parseInt(localStorage.getItem("fw-font") || "0", 10);
    if (savedFont > 0 && savedFont < fontSizes.length) {
      fontIndex = savedFont;
      document.body.classList.add(fontSizes[fontIndex]);
    }
    if (localStorage.getItem("fw-theme") === "light") {
      document.body.classList.add("theme-light");
      const icon = document.querySelector("#theme-icon");
      if (icon) icon.innerHTML = "&#x1F319;";
    }
  } catch {}
})();

// ===========================================================================
// GUIDED MODE
// ===========================================================================

let detectedDevice = null;  // stores {model, codename, match} from auto-detect
let autoRetryTimer = null;  // auto-retry polling timer

function stopAutoRetry() {
  if (autoRetryTimer) { clearInterval(autoRetryTimer); autoRetryTimer = null; }
  const indicator = $("#auto-retry-status");
  if (indicator) indicator.innerHTML = "";
}

function startAutoRetry() {
  stopAutoRetry();
  const indicator = $("#auto-retry-status");
  if (indicator) {
    indicator.innerHTML = `<div class="auto-retry-indicator"><span class="pulse-dot"></span> ${t("detect.autoretry.active") || "Scanning for device..."} <button class="btn btn-link" style="font-size:0.8rem; min-height:auto; padding:0 0.3rem;" onclick="stopAutoRetry()">${t("btn.stop") || "Stop"}</button></div>`;
  }
  autoRetryTimer = setInterval(async () => {
    try {
      const data = await api("/api/detect");
      if (!data.error) {
        stopAutoRetry();
        if (data.multiple) {
          // Multiple devices found — stop and let user pick
          guidedDetect();
        } else {
          const btn = $("#btn-detect-guided");
          if (btn) btnLoading(btn, false);
          guidedSelectDevice(data);
        }
      }
    } catch {}
  }, 5000);
}

function showAdvanced() {
  stopAutoRetry();
  $("#guided-mode").style.display = "none";
  $("#advanced-mode").style.display = "block";
  saveWizardState();
}

function showGuided() {
  $("#advanced-mode").style.display = "none";
  $("#guided-mode").style.display = "block";
  saveWizardState();
}

// Progress bar update
const stepProgress = {
  "step-category": 1,
  "step-connect": 2,
  "step-goal": 3,
  "step-install": 4,
  "step-backup": 4,
  "step-fix": 4,
};

let selectedCategory = null;  // stores the device category

// Flow-specific labels for step 4
const stepFlowLabels = {
  "step-install": t("step.install.short") || "Install",
  "step-backup": t("step.backup.short") || "Backup",
  "step-fix": t("step.fix.short") || "Fix",
};

function updateProgressBar(stepId) {
  const totalSteps = 4;
  const current = stepProgress[stepId] || 1;
  for (let i = 1; i <= totalSteps; i++) {
    const dot = $(`#prog-${i}`);
    const label = dot?.parentElement?.querySelector(".progress-label");
    if (!dot) continue;
    dot.classList.remove("active", "done");
    if (label) label.classList.remove("active", "done");
    if (i < current) {
      dot.classList.add("done");
      dot.innerHTML = "&#x2713;";
      if (label) label.classList.add("done");
    } else if (i === current) {
      dot.classList.add("active");
      dot.textContent = i;
      if (label) label.classList.add("active");
    } else {
      dot.textContent = i;
    }
  }
  // Update step 4 label to show specific flow name
  const step4Label = $(`#prog-4`)?.parentElement?.querySelector(".progress-label");
  if (step4Label) {
    step4Label.textContent = stepFlowLabels[stepId] || (t("step.go") || "Go!");
  }
  // Update connecting lines
  for (let i = 1; i <= totalSteps - 1; i++) {
    const line = $(`#prog-line-${i}`);
    if (line) {
      line.classList.toggle("done", i < current);
    }
  }
}

function guidedGoTo(stepId) {
  $$(".wizard-step").forEach((s) => {
    s.classList.remove("active");
    s.classList.remove("task-active");
  });
  // Remove any leftover completion screens
  $$(".completion-screen").forEach((c) => c.remove());
  const step = $(`#${stepId}`);
  if (step) step.classList.add("active");
  updateProgressBar(stepId);
  saveWizardState();
}

function btnLoading(btn, loading) {
  if (loading) {
    btn.classList.add("btn-loading");
    btn.disabled = true;
  } else {
    btn.classList.remove("btn-loading");
    btn.disabled = false;
  }
}

async function guidedDetect() {
  const btn = $("#btn-detect-guided");
  const step = $("#step-connect");
  const status = $("#guided-detect-status");

  btnLoading(btn, true);
  step.classList.add("detecting");
  status.style.display = "block";
  status.className = "detect-box";
  status.innerHTML = `<div style="font-size:1.2rem;">&#x1F50D;</div>${t("detect.searching")}`;

  try {
    const data = await api("/api/detect");

    if (data.error) {
      btnLoading(btn, false);
      status.className = "detect-box not-found";

      const isUsbNoAdb = data.error === "usb_no_adb";

      const title = isUsbNoAdb ? t("detect.usb_no_adb.title") : t("detect.notfound.title");
      const hint = isUsbNoAdb ? t("detect.usb_no_adb.hint") : t("detect.no_device.hint");

      // Show USB device names so the user can confirm it's the right device
      let usbNamesHtml = "";
      if (isUsbNoAdb && data.usb_devices && data.usb_devices.length) {
        const names = data.usb_devices.map(
          (d) => `<strong>${d.name}</strong>`
        ).join(", ");
        usbNamesHtml = `<p style="margin-top:0.5rem; font-size:0.95rem;">${t("detect.usb_seen")}: ${names}</p>`;
      }

      const steps = isUsbNoAdb
        ? [t("detect.step2"), t("detect.step3"), t("detect.step4"), t("detect.step5"), t("detect.step6"), t("detect.step7")]
        : [t("detect.step1"), t("detect.step2"), t("detect.step3"), t("detect.step4"), t("detect.step5"), t("detect.step6"), t("detect.step7")];

      const stepsHtml = steps.map((s, i) => `<li>${s}</li>`).join("");

      status.innerHTML = `
        <p><strong>${title}</strong></p>
        ${usbNamesHtml}
        <p class="muted-hint" style="margin-top:0.4rem;">${hint}</p>
        <ol class="detect-steps" style="text-align:left; margin:0.8rem 0; padding-left:1.4rem; line-height:1.7;">${stepsHtml}</ol>
        <div class="continue-btn">
          <button class="btn btn-primary" onclick="guidedDetect()">${t("detect.tryagain")}</button>
          <button class="btn btn-secondary" style="margin-left:0.5rem;" onclick="startAutoRetry()">${t("detect.autoretry") || "Auto-retry every 5s"}</button>
          <button class="btn btn-secondary" style="margin-left:0.5rem;" onclick="guidedGoTo('step-goal')">${t("detect.continue.without")}</button>
        </div>
        <div id="auto-retry-status"></div>`;
      return;
    }

    // --- Multiple devices: let the user pick ---
    if (data.multiple) {
      btnLoading(btn, false);
      status.className = "detect-box found";
      const cardsHtml = data.devices.map((d, i) => {
        const name = d.match ? d.match.label : d.display_name;
        const matchBadge = d.match
          ? `<span style="color:var(--green); font-size:0.8rem;">${t("detect.found.known")}</span>`
          : "";
        return `<div class="device-pick-card" tabindex="0" onclick="guidedPickDevice(${i})" onkeydown="if(event.key==='Enter')guidedPickDevice(${i})">
          <div class="device-name">${name}</div>
          <p class="text-dim" style="margin:0.2rem 0;">${d.model} / ${d.codename}</p>
          ${matchBadge}
        </div>`;
      }).join("");

      // Store for later selection
      window._multiDevices = data.devices;

      status.innerHTML = `
        <p><strong>${t("detect.multiple.title")}</strong></p>
        <p class="muted-hint" style="margin-top:0.3rem;">${t("detect.multiple.hint")}</p>
        <div class="device-pick-grid" style="display:flex; flex-direction:column; gap:0.5rem; margin:0.8rem 0;">${cardsHtml}</div>`;
      return;
    }

    // --- Single device detected ---
    btnLoading(btn, false);
    guidedSelectDevice(data);

  } catch (e) {
    btnLoading(btn, false);
    status.className = "detect-box not-found";
    status.innerHTML = `<p style="color:var(--red);">${t("detect.error")}: ${e.message}</p>
      <div class="continue-btn"><button class="btn btn-secondary" onclick="guidedGoTo('step-goal')">${t("detect.continue.anyway")}</button></div>`;
  }
}

function guidedPickDevice(index) {
  const d = window._multiDevices[index];
  guidedSelectDevice(d);
}

function guidedSelectDevice(data) {
    stopAutoRetry();
    const status = $("#guided-detect-status");
    detectedDevice = data;
    const name = data.match ? data.match.label : (data.display_name || data.model || data.codename || "Unknown device");

    status.className = "detect-box found";
    status.innerHTML = `
      <div class="device-name">${name}</div>
      <p class="text-dim">${data.model} / ${data.codename}</p>
      ${data.match ? `<p style="color:var(--green); font-size:0.85rem; margin-top:0.4rem;">${t("detect.found.known")}</p>` : `<p style="color:var(--yellow); font-size:0.85rem; margin-top:0.4rem;">${t("detect.found.unknown")}</p>`}
      <div class="continue-btn">
        <button class="btn btn-large btn-primary" onclick="guidedAutoCategory()">
          ${t("detect.continue")} &rarr;
        </button>
      </div>`;

    // Pre-fill device info on next steps
    const infoText = `${t("your.device")}: <strong>${name}</strong> (${data.model})`;
    const goalInfo = $("#goal-device-info");
    const installInfo = $("#install-device-info");
    if (goalInfo) goalInfo.innerHTML = infoText;
    if (installInfo) installInfo.innerHTML = infoText;

    // Build OS choices from preset, or auto-search for available ROMs
    if (data.match) {
      buildOsChoices(data.match);
    } else if (data.codename) {
      searchAvailableRoms(data.codename, data.model);
    }
}

function buildOsChoices(preset) {
  const grid = $("#os-choices");
  grid.innerHTML = "";

  const choices = [
    { key: "rom_url", name: t("os.lineage.name"), desc: t("os.lineage.desc"), icon: "&#x1F4F1;" },
    { key: "eos_url", name: t("os.eos.name"), desc: t("os.eos.desc"), icon: "&#x1F512;" },
  ];

  choices.forEach((os) => {
    if (!preset[os.key]) return;
    const card = document.createElement("div");
    card.className = "os-card";
    card.dataset.key = os.key;
    card.dataset.url = preset[os.key];
    card.innerHTML = `<div style="font-size:1.5rem;">${os.icon}</div>
      <div class="os-name">${os.name}</div>
      <div class="os-desc">${os.desc}</div>`;
    card.addEventListener("click", () => {
      $$(".os-card", grid).forEach((c) => c.classList.remove("selected"));
      card.classList.add("selected");
    });
    grid.appendChild(card);
  });
}

async function searchAvailableRoms(codename, model) {
  const grid = $("#os-choices");
  grid.innerHTML = `<div class="rom-searching">
    <span class="searching-icon">&#x1F50D;</span>
    <p>${t("romfinder.searching")}<span class="searching-dots"></span></p>
    <div class="rom-skeleton-row">
      <div class="rom-skeleton-card"></div>
      <div class="rom-skeleton-card"></div>
      <div class="rom-skeleton-card"></div>
    </div>
  </div>`;

  // Remove any previous header/notes from earlier searches
  grid.parentElement.querySelectorAll(".romfinder-header, .rom-twrp-note, .rom-search-links").forEach((el) => el.remove());

  try {
    const params = model ? `?model=${encodeURIComponent(model)}` : "";
    const data = await api(`/api/romfinder/${encodeURIComponent(codename)}${params}`);

    grid.innerHTML = "";

    const meta = {
      lineageos:    { icon: "&#x1F4F1;", desc: t("os.lineage.desc") },
      eos:          { icon: "&#x1F512;", desc: t("os.eos.desc") },
      twrp:         { icon: "&#x1F6E0;", desc: t("romfinder.twrp.desc") },
      postmarketos: { icon: "&#x1F427;", desc: t("os.postmarketos.desc") },
      replicant:    { icon: "&#x1F513;", desc: t("os.replicant.desc") },
      ubports:      { icon: "&#x1F4BB;", desc: t("os.ubports.desc") },
    };

    const roms = (data.roms || []).filter((r) => r.id !== "twrp");
    const twrp = (data.roms || []).find((r) => r.id === "twrp");

    if (roms.length) {
      // Show a header above the cards
      const header = document.createElement("p");
      header.className = "text-dim romfinder-header";
      header.style.marginBottom = "0.5rem";
      header.innerHTML = t("romfinder.found");
      grid.before(header);

      roms.forEach((rom) => {
        const m = meta[rom.id] || { icon: "&#x1F4E6;", desc: "" };
        const card = document.createElement("div");
        card.className = "os-card";
        card.dataset.romId = rom.id;
        card.dataset.downloadUrl = rom.download_url || "";
        card.dataset.pageUrl = rom.page_url || "";
        card.dataset.filename = rom.filename || "";
        card.dataset.romName = rom.name || "";
        card.dataset.version = rom.version || "";
        if (rom.ipfs_cid) card.dataset.ipfsCid = rom.ipfs_cid;
        if (rom.install_method) card.dataset.installMethod = rom.install_method;
        if (rom.recovery_url) card.dataset.recoveryUrl = rom.recovery_url;
        if (rom.file_size) card.dataset.fileSize = rom.file_size;

        const versionHtml = rom.version && rom.version !== "pmbootstrap"
          ? `<div class="os-version">${t("romfinder.version")} ${rom.version}</div>` : "";
        const sizeHtml = rom.file_size
          ? `<div class="os-version" style="opacity:0.7;">${(rom.file_size / (1024*1024)).toFixed(0)} MB</div>` : "";
        const ipfsBadge = rom.ipfs_cid ? `<div class="os-ipfs-badge" style="color:var(--cyan); font-size:0.75rem; margin-top:0.2rem;" title="CID: ${rom.ipfs_cid}">&#x1F310; ${t("romfinder.ipfs.pinned")} <span class="ipfs-peer-count" data-cid="${rom.ipfs_cid}"></span></div>` : "";
        let sourceLabel;
        if (rom.source === "community-ipfs") {
          sourceLabel = `<div style="color:var(--magenta); font-size:0.75rem;">&#x1F310; Community IPFS</div>`;
        } else if (rom.source === "ipfs") {
          sourceLabel = `<div style="color:var(--cyan); font-size:0.75rem;">&#x1F310; ${t("romfinder.ipfs.source")}</div>`;
        } else if (rom.install_method === "pmbootstrap") {
          sourceLabel = `<div class="os-available" style="color:var(--yellow); font-size:0.8rem; margin-top:0.3rem;">&#x1F6E0; ${t("romfinder.requires.build")}</div>`;
        } else if (rom.download_url) {
          sourceLabel = `<div class="os-available" style="color:var(--green); font-size:0.8rem; margin-top:0.3rem;">&#x2714; ${t("romfinder.available")}</div>`;
        } else if (rom.page_url) {
          sourceLabel = `<div class="os-available" style="color:var(--accent); font-size:0.8rem; margin-top:0.3rem;">&#x2197; ${t("romfinder.visit.project")}</div>`;
        } else {
          sourceLabel = "";
        }

        card.innerHTML = `<div style="font-size:1.5rem;">${m.icon}</div>
          <div class="os-name">${rom.name}</div>
          <div class="os-desc">${m.desc}</div>
          ${versionHtml}
          ${sizeHtml}
          ${sourceLabel}
          ${ipfsBadge}`;
        card.addEventListener("click", () => {
          $$(".os-card", grid).forEach((c) => c.classList.remove("selected"));
          card.classList.add("selected");
          // Show/hide Download & Flash button
          const dfBtn = $("#btn-download-flash");
          if (dfBtn) {
            dfBtn.style.display = (rom.download_url || rom.ipfs_cid) ? "inline-flex" : "none";
          }
        });
        grid.appendChild(card);
      });
    }

    // Show TWRP as informational note if found
    if (twrp) {
      const note = document.createElement("div");
      note.className = "rom-twrp-note";
      note.innerHTML = `<span style="font-size:1rem;">&#x1F6E0;</span>
        <span>${t("romfinder.twrp.available")}</span>
        <a href="${twrp.page_url}" target="_blank" rel="noopener" style="color:var(--accent); margin-left:0.3rem;">${t("romfinder.twrp.link")}</a>`;
      grid.after(note);
    }

    // Always show search links to help the user find ROMs
    if (data.search_links && data.search_links.length) {
      const linksDiv = document.createElement("div");
      linksDiv.className = "rom-search-links";

      const hasAutoResults = roms.length > 0;
      const intro = hasAutoResults ? t("romfinder.search.also") : t("romfinder.search.try");

      let linksHtml = `<p style="margin-bottom:0.5rem;">${intro}</p><div class="search-link-grid">`;
      data.search_links.forEach((link) => {
        linksHtml += `<a href="${link.url}" target="_blank" rel="noopener" class="search-link-card">
          <span class="search-link-name">${link.name}</span>
          <span class="search-link-arrow">&rarr;</span>
        </a>`;
      });
      linksHtml += `</div>`;
      linksDiv.innerHTML = linksHtml;

      // Insert after grid (and after twrp note if present)
      const insertAfter = grid.parentElement.querySelector(".rom-twrp-note") || grid;
      insertAfter.after(linksDiv);
    }

    // Lazily load IPFS peer counts for pinned ROMs
    setTimeout(ipfsLoadPeerCounts, 100);

    // If no installable ROM was found, explain clearly why
    if (!roms.length) {
      const deviceName = detectedDevice?.display_name || detectedDevice?.model || codename;
      grid.innerHTML = `<div class="rom-not-found">
        <div style="font-size:1.5rem; margin-bottom:0.5rem;">&#x1F4F1;</div>
        <p><strong>${t("romfinder.norom.title")}</strong></p>
        <p style="margin-top:0.4rem;">${t("romfinder.norom.explain").replace("{device}", deviceName)}</p>
        <p class="text-dim" style="margin-top:0.5rem; font-size:0.85rem;">${t("romfinder.norom.reassure")}</p>
      </div>`;
    }

  } catch (e) {
    grid.innerHTML = `<div class="rom-not-found">
      <p style="color:var(--red);">${t("romfinder.error")}</p>
    </div>`;
  }
}

function guidedPickCategory(category) {
  selectedCategory = category;

  // OS builder skips connect and goal — go straight there
  if (category === "build-os") {
    osBuilderInit();
    guidedGoTo("step-os-builder");
    saveWizardState();
    return;
  }

  // Filter goal cards based on selected category
  const goalGrid = $("#goal-grid");
  if (goalGrid) {
    $$(".goal-card[data-goal]", goalGrid).forEach((card) => {
      const categories = (card.dataset.categories || "").split(",");
      card.style.display = categories.includes(category) ? "" : "none";
    });
  }

  guidedGoTo("step-connect");
  saveWizardState();
}

function guidedAutoCategory() {
  // Category is already selected (step 1), proceed to goals
  guidedGoTo("step-goal");
}

function guidedPickGoal(goal) {
  if (goal === "install") guidedGoTo("step-install");
  else if (goal === "backup") guidedGoTo("step-backup");
  else if (goal === "fix") guidedGoTo("step-fix");
  else if (goal === "bootable") openModal("modal-bootable");
  else if (goal === "pxe") openModal("modal-pxe");
  else if (goal === "scooter-flash" || goal === "scooter-restore") { scooterInit(); guidedGoTo("step-scooter"); }
  else if (goal === "scooter-info") { scooterInit(); guidedGoTo("step-scooter"); }
  else if (goal === "os-builder") { osBuilderInit(); guidedGoTo("step-os-builder"); }
}

function setTaskActive(stepEl, active) {
  if (active) {
    stepEl.classList.add("task-active");
  } else {
    stepEl.classList.remove("task-active");
  }
}

async function guidedStartInstall() {
  const btn = $("#btn-guided-install");
  const step = $("#step-install");
  const term = $("#term-guided-install");

  // Determine what to install
  const selectedOs = $(".os-card.selected");
  let romZip = $("#guided-rom-zip").value.trim();
  let gappsZip = $("#guided-gapps-zip").value.trim();

  // Build a description of what will be installed
  const osName = selectedOs ? (selectedOs.querySelector(".os-name")?.textContent || "Selected OS") : (romZip ? romZip.split("/").pop() : "");
  const deviceName = detectedDevice ? (detectedDevice.match?.label || detectedDevice.display_name || detectedDevice.model || "your device") : "your device";

  // Show confirmation dialog
  const proceed = await new Promise((resolve) => {
    showConfirm({
      icon: "&#x1F680;",
      title: t("confirm.install.title") || "Ready to install?",
      body: t("confirm.install.body") || "This will install a new operating system on your device. Existing data may be erased.",
      details: `<strong>${t("device") || "Device"}:</strong> ${deviceName}<br><strong>${t("os") || "OS"}:</strong> ${osName || "Manual ROM"}${gappsZip ? `<br><strong>GApps:</strong> ${gappsZip.split("/").pop()}` : ""}`,
      confirmText: t("confirm.install.btn") || "Start installation",
      onConfirm: () => resolve(true),
      onCancel: () => resolve(false),
    });
  });
  if (!proceed) return;

  btnLoading(btn, true);

  // If an OS card is selected and no manual ROM, use the preset or romfinder download flow
  if (selectedOs && !romZip) {
    // Preset flow (card has data-key from devices.cfg)
    if (selectedOs.dataset.key && detectedDevice?.match) {
      const key = selectedOs.dataset.key;
      const deviceId = detectedDevice.match.id;
      const selected = [key];
      if (key === "rom_url") selected.push("twrp_url");

      term.classList.add("active");
      term.innerHTML = "";
      setTaskActive(step, true);
      appendLine(term, t("romfinder.downloading"), "info");

      const dlData = await api("/api/download", {
        method: "POST",
        body: { device_id: deviceId, selected },
      });
      streamTask(dlData.task_id, term, (status) => {
        if (status === "done") {
          appendLine(term, "", "info");
          appendLine(term, t("romfinder.dl.done"), "success");
        }
        btnLoading(btn, false);
        setTaskActive(step, false);
      }, { progress: true });
      return;
    }

    // ROM finder flow (card has data-download-url or ipfs-cid from /api/romfinder)
    if (selectedOs.dataset.downloadUrl || selectedOs.dataset.ipfsCid) {
      const url = selectedOs.dataset.downloadUrl;
      const filename = selectedOs.dataset.filename || "rom.zip";
      const romName = selectedOs.querySelector(".os-name")?.textContent || "ROM";
      const pageUrl = selectedOs.dataset.pageUrl || "";
      const ipfsCid = selectedOs.dataset.ipfsCid || "";
      const recoveryUrl = selectedOs.dataset.recoveryUrl || "";

      term.classList.add("active");
      term.innerHTML = "";
      setTaskActive(step, true);
      const source = ipfsCid && !url ? "IPFS" : "";
      appendLine(term, `${t("romfinder.downloading")} ${romName}${source ? " from IPFS" : ""}...`, "info");

      const codename = detectedDevice?.codename || "unknown";
      const dlData = await api("/api/romfinder/download", {
        method: "POST",
        body: {
          url, filename, codename, ipfs_cid: ipfsCid,
          rom_id: selectedOs.dataset.romId || "",
          rom_name: selectedOs.dataset.romName || romName,
          version: selectedOs.dataset.version || "",
        },
      });
      if (dlData.error) {
        appendLine(term, dlData.error, "error");
        if (pageUrl) {
          appendLine(term, "", "info");
          appendLine(term, `${t("romfinder.dl.manual")}: ${pageUrl}`, "info");
        }
        btnLoading(btn, false);
        setTaskActive(step, false);
      } else {
        const romDest = dlData.dest;
        streamTask(dlData.task_id, term, async (status) => {
          if (status !== "done") {
            btnLoading(btn, false);
            setTaskActive(step, false);
            return;
          }

          // Remove progress panel before next phase
          removeProgressPanel(term);

          // If a recovery image URL is available, download it too
          let recoveryDest = null;
          if (recoveryUrl) {
            appendLine(term, "", "info");
            appendLine(term, t("install.downloading.recovery"), "info");
            const recFilename = recoveryUrl.split("/").pop() || "recovery.img";
            const recData = await api("/api/romfinder/download", {
              method: "POST",
              body: {
                url: recoveryUrl, filename: recFilename, codename,
                rom_id: (selectedOs.dataset.romId || "") + "_recovery",
                rom_name: romName + " Recovery",
                version: selectedOs.dataset.version || "",
              },
            });
            if (!recData.error) {
              recoveryDest = recData.dest;
              const recStatus = await new Promise((resolve) => {
                streamTask(recData.task_id, term, resolve, { progress: true, progressLabel: romName + " Recovery" });
              });
              removeProgressPanel(term);
              if (recStatus !== "done") {
                recoveryDest = null;
              }
            }
          }

          // Show post-download installation actions
          appendLine(term, "", "info");
          appendLine(term, t("romfinder.dl.done"), "success");
          appendLine(term, "", "info");
          guidedShowInstallActions(term, btn, step, romDest, recoveryDest);
        }, { progress: true, progressLabel: romName });
      }
      return;
    }

    // postmarketOS pmbootstrap flow
    if (selectedOs.dataset.installMethod === "pmbootstrap") {
      const romName = selectedOs.querySelector(".os-name")?.textContent || "postmarketOS";
      term.classList.add("active");
      term.innerHTML = "";
      setTaskActive(step, true);
      appendLine(term, `${t("romfinder.pmbootstrap.starting")} ${romName}...`, "info");

      const codename = detectedDevice?.codename || "unknown";
      const pmData = await api("/api/pmbootstrap", {
        method: "POST",
        body: { codename },
      });
      if (pmData.error) {
        appendLine(term, pmData.error, "error");
        btnLoading(btn, false);
        setTaskActive(step, false);
      } else {
        streamTask(pmData.task_id, term, () => {
          btnLoading(btn, false);
          setTaskActive(step, false);
        });
      }
      return;
    }

    // ROM finder card with page_url only (no direct download)
    if (selectedOs.dataset.pageUrl) {
      const pageUrl = selectedOs.dataset.pageUrl;
      const romName = selectedOs.querySelector(".os-name")?.textContent || "ROM";
      term.classList.add("active");
      term.innerHTML = "";
      setTaskActive(step, true);
      appendLine(term, `${t("romfinder.dl.visit")} ${romName}:`, "info");
      appendLine(term, "", "info");

      // Make the URL a clickable link
      const linkDiv = document.createElement("div");
      linkDiv.className = "line";
      const a = document.createElement("a");
      a.href = pageUrl;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = pageUrl;
      a.style.cssText = "color:var(--accent); font-size:calc(1rem * var(--font-scale)); word-break:break-all;";
      linkDiv.appendChild(a);
      term.appendChild(linkDiv);

      appendLine(term, "", "info");
      appendLine(term, t("romfinder.dl.visit.hint"), "info");
      btnLoading(btn, false);
      return;
    }
  }

  // Manual install via workflow API
  if (!romZip) {
    const romInput = $("#guided-rom-zip");
    showInlineError(romInput, t("error.select.os") || "Please select an OS or choose a ROM file manually.");
    btnLoading(btn, false);
    return;
  }

  const data = await api("/api/workflow", {
    method: "POST",
    body: {
      fw_zip: "",
      recovery_img: "",
      rom_zip: romZip,
      gapps_zip: gappsZip,
    },
  });
  setTaskActive(step, true);
  streamTask(data.task_id, term, (status) => {
    btnLoading(btn, false);
    setTaskActive(step, false);
    if (status === "done") {
      const deviceName = detectedDevice ? (detectedDevice.match?.label || detectedDevice.display_name || detectedDevice.model || "") : "";
      showCompletion(step, {
        icon: "&#x1F389;",
        title: t("complete.install.title") || "Installation complete!",
        subtitle: t("complete.install.subtitle") || "Your new operating system has been installed. Reboot your device from recovery to start using it.",
        summary: [
          ...(deviceName ? [{ label: t("device") || "Device", value: deviceName }] : []),
          { label: "ROM", value: romZip.split("/").pop() },
          ...(gappsZip ? [{ label: "GApps", value: gappsZip.split("/").pop() }] : []),
        ],
        actions: [
          { id: "start-over", label: t("btn.startover") || "Start over", primary: true, onClick: () => guidedGoTo("step-category") },
        ],
      });
    }
  });
}

async function guidedStartBackup() {
  const btn = $("#btn-guided-backup");
  const step = $("#step-backup");
  btnLoading(btn, true);
  const term = $("#term-guided-backup");

  const partitions = [];
  if ($("#guided-bk-boot").checked) partitions.push("boot");
  if ($("#guided-bk-recovery").checked) partitions.push("recovery");
  const backupEfs = $("#guided-bk-efs").checked;

  setTaskActive(step, true);
  const data = await api("/api/backup", {
    method: "POST",
    body: { partitions, backup_efs: backupEfs },
  });
  streamTask(data.task_id, term, (status) => {
    btnLoading(btn, false);
    setTaskActive(step, false);
    if (status === "done") {
      const deviceName = detectedDevice ? (detectedDevice.match?.label || detectedDevice.display_name || detectedDevice.model || "") : "";
      showCompletion(step, {
        icon: "&#x2705;",
        title: t("complete.backup.title") || "Backup complete!",
        subtitle: t("complete.backup.subtitle") || "Your device partitions have been saved safely.",
        summary: [
          ...(deviceName ? [{ label: t("device") || "Device", value: deviceName }] : []),
          { label: t("partitions") || "Partitions", value: partitions.join(", ") + (backupEfs ? ", EFS" : "") },
          { label: t("location") || "Location", value: "~/.osmosis/backups/" },
        ],
        actions: [
          { id: "start-over", label: t("btn.startover") || "Start over", onClick: () => guidedGoTo("step-category") },
          { id: "install", label: t("btn.install.now") || "Install an OS now", primary: true, onClick: () => guidedGoTo("step-install") },
        ],
      });
    }
  });
}

async function guidedStartFix() {
  const btn = $("#btn-guided-fix");
  const step = $("#step-fix");
  const term = $("#term-guided-fix");

  let fwZip = $("#guided-fix-fw").value.trim();
  const deviceName = detectedDevice ? (detectedDevice.match?.label || detectedDevice.display_name || detectedDevice.model || "your device") : "your device";

  // Show confirmation dialog
  const proceed = await new Promise((resolve) => {
    showConfirm({
      icon: "&#x26A0;",
      title: t("confirm.fix.title") || "Restore factory software?",
      body: t("confirm.fix.body") || "This will erase everything on the device and restore factory software. All apps, photos, and data will be deleted.",
      details: `<strong>${t("device") || "Device"}:</strong> ${deviceName}${fwZip ? `<br><strong>${t("firmware") || "Firmware"}:</strong> ${fwZip.split("/").pop()}` : ""}`,
      confirmText: t("confirm.fix.btn") || "Erase and restore",
      danger: true,
      onConfirm: () => resolve(true),
      onCancel: () => resolve(false),
    });
  });
  if (!proceed) return;

  btnLoading(btn, true);

  // If no firmware provided but we have a preset, download it first
  if (!fwZip && detectedDevice?.match?.stock_url) {
    term.classList.add("active");
    term.innerHTML = "";
    setTaskActive(step, true);
    appendLine(term, "Downloading factory firmware for your device...", "info");

    const dlData = await api("/api/download", {
      method: "POST",
      body: { device_id: detectedDevice.match.id, selected: ["stock_url"] },
    });
    streamTask(dlData.task_id, term, (status) => {
      removeProgressPanel(term);
      btnLoading(btn, false);
      setTaskActive(step, false);
      if (status === "done") {
        showCompletion(step, {
          icon: "&#x2705;",
          title: t("complete.fix.dl.title") || "Firmware downloaded!",
          subtitle: t("complete.fix.dl.subtitle") || "Factory firmware is ready. The next step is to flash it to your device.",
          summary: [
            { label: t("device") || "Device", value: deviceName },
          ],
          actions: [
            { id: "start-over", label: t("btn.startover") || "Start over", primary: true, onClick: () => guidedGoTo("step-category") },
          ],
        });
      }
    }, { progress: true, progressLabel: t("progress.downloading") });
    return;
  }

  if (!fwZip) {
    const fixInput = $("#guided-fix-fw");
    showInlineError(fixInput, t("error.select.firmware") || "Please select a firmware file, or connect your device so we can find one for you.");
    btnLoading(btn, false);
    return;
  }

  setTaskActive(step, true);
  const data = await api("/api/flash/stock", {
    method: "POST",
    body: { fw_zip: fwZip },
  });
  streamTask(data.task_id, term, (status) => {
    btnLoading(btn, false);
    setTaskActive(step, false);
    if (status === "done") {
      showCompletion(step, {
        icon: "&#x2705;",
        title: t("complete.fix.title") || "Device restored!",
        subtitle: t("complete.fix.subtitle") || "Factory software has been restored. Your device should boot normally now.",
        summary: [
          { label: t("device") || "Device", value: deviceName },
          { label: t("firmware") || "Firmware", value: fwZip.split("/").pop() },
        ],
        actions: [
          { id: "start-over", label: t("btn.startover") || "Start over", primary: true, onClick: () => guidedGoTo("step-category") },
        ],
      });
    }
  });
}

// ---------------------------------------------------------------------------
// Post-download installation actions
// ---------------------------------------------------------------------------

function guidedShowInstallActions(term, btn, step, romPath, recoveryPath) {
  appendLine(term, t("install.next.steps"), "info");

  if (recoveryPath) {
    appendLine(term, "", "info");
    appendLine(term, t("install.step.recovery"), "info");
    appendLine(term, t("install.step.recovery.hint"), "info");
  }
  appendLine(term, "", "info");
  appendLine(term, recoveryPath ? t("install.step.sideload.after") : t("install.step.sideload"), "info");
  appendLine(term, t("install.step.sideload.hint"), "info");
  appendLine(term, "", "info");

  const actionsDiv = document.createElement("div");
  actionsDiv.style.cssText = "display:flex; gap:0.5rem; flex-wrap:wrap; margin:0.5rem 0;";

  if (recoveryPath) {
    const recBtn = document.createElement("button");
    recBtn.className = "btn btn-secondary";
    recBtn.textContent = t("install.btn.flash.recovery");
    recBtn.addEventListener("click", async () => {
      recBtn.disabled = true;
      appendLine(term, "", "info");
      appendLine(term, t("install.flashing.recovery"), "info");
      appendLine(term, t("install.download.mode.hint"), "warn");
      const data = await api("/api/flash/recovery", {
        method: "POST",
        body: { recovery_img: recoveryPath },
      });
      if (data.error) {
        appendLine(term, data.error, "error");
        recBtn.disabled = false;
      } else {
        streamTask(data.task_id, term, () => { recBtn.disabled = false; });
      }
    });
    actionsDiv.appendChild(recBtn);
  }

  const sideloadBtn = document.createElement("button");
  sideloadBtn.className = "btn btn-primary";
  sideloadBtn.textContent = t("install.btn.sideload");
  sideloadBtn.addEventListener("click", async () => {
    sideloadBtn.disabled = true;
    appendLine(term, "", "info");
    appendLine(term, t("install.sideloading"), "info");
    appendLine(term, t("install.sideload.mode.hint"), "warn");
    try {
      const data = await api("/api/sideload", {
        method: "POST",
        body: { zip_path: romPath, label: "ROM" },
      });
      if (data.error) {
        appendLine(term, data.error, "error");
        sideloadBtn.disabled = false;
      } else {
      streamTask(data.task_id, term, (status) => {
        sideloadBtn.disabled = false;
        btnLoading(btn, false);
        setTaskActive(step, false);
        if (status === "done") {
          const deviceName = detectedDevice ? (detectedDevice.match?.label || detectedDevice.display_name || detectedDevice.model || "") : "";
          showCompletion(step, {
            icon: "&#x1F389;",
            title: t("complete.install.title") || "Installation complete!",
            subtitle: t("complete.install.subtitle") || "Your new operating system has been installed. Reboot your device from recovery to start using it.",
            summary: [
              ...(deviceName ? [{ label: t("device") || "Device", value: deviceName }] : []),
              { label: t("os") || "OS", value: romPath.split("/").pop() },
            ],
            actions: [
              { id: "start-over", label: t("btn.startover") || "Start over", primary: true, onClick: () => guidedGoTo("step-category") },
            ],
          });
        }
      });
      }
    } catch (e) {
      appendLine(term, String(e), "error");
      sideloadBtn.disabled = false;
    }
  });
  actionsDiv.appendChild(sideloadBtn);

  term.appendChild(actionsDiv);
  term.scrollTop = term.scrollHeight;
}

// ===========================================================================
// IPFS Storage
// ===========================================================================

// ---------------------------------------------------------------------------
// Bootable device creation
// ---------------------------------------------------------------------------

async function refreshBlockDevices() {
  const sel = $("#input-bootable-device");
  if (!sel) return;
  sel.innerHTML = '<option value="">Scanning...</option>';
  try {
    const devices = await api("/api/blockdevices");
    sel.innerHTML = "";
    if (!devices.length) {
      sel.innerHTML = '<option value="">No removable devices found</option>';
      return;
    }
    devices.forEach((dev) => {
      const opt = document.createElement("option");
      opt.value = dev.path;
      opt.dataset.sizeBytes = dev.size_bytes || 0;
      opt.dataset.largeDrive = dev.large_drive ? "1" : "0";
      const mounted = dev.mounted ? " (MOUNTED)" : "";
      const large = dev.large_drive ? " [LARGE >128GB]" : "";
      opt.textContent = `${dev.path} — ${dev.model} (${dev.size})${mounted}${large}`;
      sel.appendChild(opt);
    });
  } catch {
    sel.innerHTML = '<option value="">Error scanning devices</option>';
  }
}

async function startBootable() {
  const imgInput = $("#input-bootable-image");
  const imagePath = imgInput.value.trim();
  const targetDevice = $("#input-bootable-device").value;
  const skipVerify = $("#input-bootable-skip-verify")?.checked || false;

  if (!imagePath) return showInlineError(imgInput, t("error.select.image") || "Please select an image file.");
  if (!targetDevice) return showInlineError($("#input-bootable-device"), t("error.select.device") || "Please select a target device.");

  // Extra warning for large drives (>128 GB)
  const selectedOpt = $("#input-bootable-device").selectedOptions[0];
  const isLarge = selectedOpt?.dataset?.largeDrive === "1";
  const confirmBody = isLarge
    ? (t("confirm.erase.body.large") || "WARNING: The selected drive is larger than 128 GB. Double-check this is the correct device! This will permanently erase all data.")
    : (t("confirm.erase.body") || "This will permanently erase all data on the target device.");

  showConfirm({
    icon: "&#x26A0;",
    title: t("confirm.erase.title") || "Erase all data?",
    body: confirmBody,
    details: `<strong>${t("target") || "Target"}:</strong> ${targetDevice}<br><strong>${t("image") || "Image"}:</strong> ${imagePath}`,
    confirmText: t("confirm.erase.btn") || "Erase and write",
    danger: true,
    onConfirm: async () => {
      const btn = $("#btn-bootable");
      btn.disabled = true;
      const term = $("#term-bootable");
      const data = await api("/api/bootable", {
        method: "POST",
        body: { image_path: imagePath, target_device: targetDevice, skip_verify: skipVerify },
      });
      if (data.error) {
        term.classList.add("active");
        term.innerHTML = "";
        appendLine(term, data.error, "error");
        btn.disabled = false;
        return;
      }
      streamTask(data.task_id, term, () => { removeProgressPanel(term); btn.disabled = false; }, { progress: true, progressLabel: imagePath.split("/").pop() });
    },
  });
}

// ---------------------------------------------------------------------------
// PXE Boot Server
// ---------------------------------------------------------------------------

async function refreshInterfaces() {
  const sel = $("#input-pxe-interface");
  if (!sel) return;
  sel.innerHTML = '<option value="">Scanning...</option>';
  try {
    const ifaces = await api("/api/interfaces");
    sel.innerHTML = "";
    if (!ifaces.length) {
      sel.innerHTML = '<option value="">No interfaces found</option>';
      return;
    }
    ifaces.forEach((iface) => {
      const opt = document.createElement("option");
      opt.value = iface.name;
      opt.textContent = `${iface.name} (${iface.state})`;
      sel.appendChild(opt);
    });
  } catch {
    sel.innerHTML = '<option value="">Error listing interfaces</option>';
  }
}

async function startPxe() {
  const iface = $("#input-pxe-interface").value;
  if (!iface) return showInlineError($("#input-pxe-interface"), t("error.select.interface") || "Please select a network interface.");

  const imagePath = $("#input-pxe-image").value.trim();
  const mode = $("#input-pxe-mode").value;
  const serverIp = $("#input-pxe-ip").value.trim();

  const btn = $("#btn-pxe-start");
  const stopBtn = $("#btn-pxe-stop");
  btn.disabled = true;
  stopBtn.style.display = "inline-flex";
  const term = $("#term-pxe");

  const data = await api("/api/pxe/start", {
    method: "POST",
    body: { interface: iface, image_path: imagePath, mode, server_ip: serverIp },
  });
  if (data.error) {
    alert(data.error);
    btn.disabled = false;
    stopBtn.style.display = "none";
    return;
  }
  streamTask(data.task_id, term, () => {
    btn.disabled = false;
    stopBtn.style.display = "none";
  });
}

async function stopPxe() {
  await api("/api/pxe/stop", { method: "POST" });
  const stopBtn = $("#btn-pxe-stop");
  stopBtn.style.display = "none";
  const btn = $("#btn-pxe-start");
  btn.disabled = false;
  appendLine($("#term-pxe"), "Stop signal sent.", "info");
}

// ===========================================================================
// IPFS Storage
// ===========================================================================

async function loadIpfsIndex() {
  const statusEl = $("#ipfs-status-info");
  const listEl = $("#ipfs-index-list");
  const emptyEl = $("#ipfs-empty");

  statusEl.textContent = t("ipfs.checking");
  listEl.innerHTML = "";

  try {
    const status = await api("/api/ipfs/status");
    if (!status.available) {
      statusEl.innerHTML = `<span style="color:var(--red);">${t("ipfs.unavailable")}</span>`;
      emptyEl.style.display = "none";
      return;
    }
    statusEl.innerHTML = `<span style="color:var(--green);">${t("ipfs.connected")}</span> &mdash; ${status.peer_id ? status.peer_id.slice(0, 16) + "..." : ""} (${status.agent || ""})`;
    ipfsLoadExtras();
  } catch {
    statusEl.innerHTML = `<span style="color:var(--red);">${t("ipfs.unavailable")}</span>`;
    return;
  }

  try {
    const items = await api("/api/ipfs/index");
    if (!items.length) {
      emptyEl.style.display = "block";
      return;
    }
    emptyEl.style.display = "none";
    items.forEach((item) => {
      const el = document.createElement("div");
      el.className = "device-item";
      const sizeMB = (item.size / (1024 * 1024)).toFixed(1);
      const date = item.pinned_at ? new Date(item.pinned_at).toLocaleDateString() : "";
      el.innerHTML = `<div class="name">${item.rom_name || item.filename} ${item.version ? "v" + item.version : ""}</div>
        <div class="meta">${item.codename} &mdash; ${sizeMB} MB &mdash; ${date}</div>
        <div class="meta" style="font-family:var(--font-mono); font-size:0.75rem; opacity:0.7; word-break:break-all;">${item.cid}</div>
        <button class="btn btn-secondary btn-sm ipfs-unpin-btn" style="margin-top:0.3rem;" data-key="${item.key}">${t("ipfs.unpin")}</button>`;
      el.querySelector(".ipfs-unpin-btn").addEventListener("click", (e) => {
        e.stopPropagation();
        showConfirm({
          icon: "&#x1F5D1;",
          title: t("ipfs.unpin.title") || "Unpin from IPFS?",
          body: t("ipfs.unpin.confirm") || "This will remove the file from your local IPFS node.",
          details: `<strong>CID:</strong> ${item.cid.slice(0, 24)}...`,
          confirmText: t("ipfs.unpin") || "Unpin",
          danger: true,
          onConfirm: async () => {
            await api("/api/ipfs/unpin", { method: "POST", body: { key: item.key } });
            loadIpfsIndex();
          },
        });
      });
      listEl.appendChild(el);
    });
  } catch { /* ignore */ }
}

async function ipfsFetch() {
  const cid = $("#ipfs-fetch-cid").value.trim();
  const codename = $("#ipfs-fetch-codename").value.trim() || "unknown";
  const filename = $("#ipfs-fetch-filename").value.trim() || "rom.zip";
  const term = $("#term-ipfs");
  const btn = $("#btn-ipfs-fetch");

  if (!cid) return showInlineError($("#ipfs-fetch-cid"), t("ipfs.fetch.nocid") || "Please enter an IPFS CID.");

  btnLoading(btn, true);
  try {
    const data = await api("/api/ipfs/fetch", {
      method: "POST",
      body: { cid, codename, filename },
    });
    if (data.error) {
      term.classList.add("active");
      term.innerHTML = "";
      appendLine(term, data.error, "error");
      btnLoading(btn, false);
      return;
    }
    streamTask(data.task_id, term, () => {
      btnLoading(btn, false);
      loadIpfsIndex();
    });
  } catch (e) {
    term.classList.add("active");
    term.innerHTML = "";
    appendLine(term, String(e), "error");
    btnLoading(btn, false);
  }
}

function ipfsLoadPeerCounts() {
  document.querySelectorAll(".ipfs-peer-count[data-cid]").forEach(async (el) => {
    const cid = el.dataset.cid;
    if (!cid || el.dataset.loaded) return;
    el.dataset.loaded = "1";
    try {
      const data = await api(`/api/ipfs/providers/${encodeURIComponent(cid)}`);
      if (data.count > 0) {
        el.textContent = `(${data.count} peer${data.count > 1 ? "s" : ""})`;
      }
    } catch { /* non-critical */ }
  });
}

async function ipfsLoadExtras() {
  // Load health check + remote pinning status after main index loads
  const bar = $("#ipfs-health-bar");
  const healthText = $("#ipfs-health-text");
  const remoteText = $("#ipfs-remote-pin-text");
  const backupBtn = $("#btn-ipfs-backup-sync");

  try {
    const [health, remote] = await Promise.all([
      api("/api/ipfs/health").catch(() => null),
      api("/api/ipfs/remote-pin/status").catch(() => null),
    ]);

    if (health && typeof health.total === "number") {
      bar.style.display = "block";
      if (health.stale && health.stale.length > 0) {
        healthText.innerHTML = `<span style="color:var(--yellow);">Pins: ${health.healthy}/${health.total} healthy, ${health.stale.length} stale</span>`;
      } else {
        healthText.innerHTML = `<span style="color:var(--green);">Pins: ${health.total} healthy</span>`;
      }
    }

    if (remote) {
      bar.style.display = "block";
      remoteText.innerHTML = remote.configured
        ? `<span style="color:var(--green);">Remote pinning: active</span>`
        : `<span style="color:var(--dim);">Remote pinning: not configured</span>`;
    }
  } catch { /* non-critical */ }

  // Show backup sync button if IPFS is available
  if (backupBtn) backupBtn.style.display = "inline-flex";
}

async function ipfsHealthCheck() {
  const btn = $("#btn-ipfs-health");
  const bar = $("#ipfs-health-bar");
  const healthText = $("#ipfs-health-text");
  btnLoading(btn, true);
  try {
    const health = await api("/api/ipfs/health");
    bar.style.display = "block";
    if (health.stale && health.stale.length > 0) {
      healthText.innerHTML = `<span style="color:var(--yellow);">Pins: ${health.healthy}/${health.total} healthy, ${health.stale.length} stale</span>`;
      const names = health.stale.map(s => s.filename || s.key).join(", ");
      healthText.innerHTML += `<br><span style="font-size:0.8rem; color:var(--yellow);">Stale: ${names}</span>`;
    } else {
      healthText.innerHTML = `<span style="color:var(--green);">All ${health.total} pins healthy</span>`;
    }
  } catch (e) {
    healthText.innerHTML = `<span style="color:var(--red);">Health check failed</span>`;
  }
  btnLoading(btn, false);
}

async function ipfsExportManifest() {
  const btn = $("#btn-ipfs-export");
  btnLoading(btn, true);
  try {
    const data = await api("/api/ipfs/manifest/export");
    const blob = new Blob([JSON.stringify({ manifest: data.manifest, sha256: data.sha256 }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "osmosis-ipfs-manifest.json";
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert("Export failed: " + String(e));
  }
  btnLoading(btn, false);
}

async function ipfsImportManifest(input) {
  const file = input.files[0];
  if (!file) return;
  input.value = "";
  try {
    const text = await file.text();
    const payload = JSON.parse(text);
    const result = await api("/api/ipfs/manifest/import", { method: "POST", body: payload });
    if (result.error) {
      alert("Import failed: " + result.error);
    } else {
      alert(`Imported ${result.imported} entries (${result.skipped} skipped).`);
      loadIpfsIndex();
    }
  } catch (e) {
    alert("Import failed: " + String(e));
  }
}

async function ipfsBackupSync() {
  const term = $("#term-ipfs");
  try {
    const backups = await api("/api/scooter/backups");
    if (!backups || !backups.length) {
      term.classList.add("active");
      term.innerHTML = "";
      appendLine(term, "No backups found to sync.", "warn");
      return;
    }
    const latest = backups[0];
    const data = await api("/api/backup/ipfs-sync", { method: "POST", body: { backup_name: latest.name } });
    if (data.error) {
      term.classList.add("active");
      term.innerHTML = "";
      appendLine(term, data.error, "error");
      return;
    }
    streamTask(data.task_id, term, () => loadIpfsIndex());
  } catch (e) {
    term.classList.add("active");
    term.innerHTML = "";
    appendLine(term, String(e), "error");
  }
}

// ===========================================================================
// DEVICE DIAGNOSTICS
// ===========================================================================

async function loadDiagnostics() {
  const btn = $("#btn-diagnostics");
  const content = $("#diagnostics-content");
  const errorEl = $("#diagnostics-error");
  const grid = $("#diag-grid");
  const header = $("#diag-device-header");

  btnLoading(btn, true);
  content.style.display = "none";
  errorEl.style.display = "none";

  try {
    const data = await api("/api/diagnostics");
    if (data.error) {
      errorEl.style.display = "block";
      errorEl.innerHTML = `<div class="detect-box not-found"><p>${data.error === "no_device" ? (t("diag.nodevice") || "No device connected. Connect via USB with debugging enabled.") : data.error}</p></div>`;
      btnLoading(btn, false);
      return;
    }

    content.style.display = "block";

    // Device header
    header.innerHTML = `
      <div class="diag-device-name">${data.display_name}</div>
      <div class="diag-device-meta">${data.model} / ${data.codename} &mdash; ${data.rom_name}</div>`;

    // Build diagnostics grid
    const battIcon = data.battery.level > 80 ? "&#x1F50B;" : (data.battery.level > 20 ? "&#x1FAAB;" : "&#x1FAB6;");
    const blColor = data.bootloader === "unlocked" ? "var(--green)" : (data.bootloader === "locked" ? "var(--red)" : "var(--yellow)");

    // Storage
    let storageHtml = "";
    if (data.storage && data.storage.total) {
      const totalGB = (data.storage.total / (1024 * 1024 * 1024)).toFixed(1);
      const usedGB = (data.storage.used / (1024 * 1024 * 1024)).toFixed(1);
      const freeGB = (data.storage.free / (1024 * 1024 * 1024)).toFixed(1);
      const pct = Math.round((data.storage.used / data.storage.total) * 100);
      storageHtml = `
        <div class="diag-bar-track"><div class="diag-bar-fill" style="width:${pct}%;"></div></div>
        <div class="diag-stat-row"><span>${usedGB} GB used</span><span>${freeGB} GB free</span><span>${totalGB} GB total</span></div>`;
    } else {
      storageHtml = `<div class="text-dim">Unable to read storage info</div>`;
    }

    // Uptime
    let uptimeStr = "";
    if (data.uptime_seconds > 0) {
      const h = Math.floor(data.uptime_seconds / 3600);
      const m = Math.floor((data.uptime_seconds % 3600) / 60);
      uptimeStr = h > 0 ? `${h}h ${m}m` : `${m}m`;
    }

    grid.innerHTML = `
      <div class="diag-card">
        <div class="diag-card-header"><span class="diag-icon">${battIcon}</span> ${t("diag.battery") || "Battery"}</div>
        <div class="diag-big-number">${data.battery.level}%</div>
        <div class="diag-stat-row"><span>${t("diag.health") || "Health"}: ${data.battery.health}</span></div>
        <div class="diag-stat-row"><span>${t("diag.temp") || "Temp"}: ${data.battery.temperature}&deg;C</span><span>${data.battery.voltage}V</span></div>
        <div class="diag-stat-row"><span>${t("diag.status") || "Status"}: ${data.battery.status}</span></div>
        ${data.battery.technology ? `<div class="diag-stat-row"><span>${data.battery.technology}</span></div>` : ""}
      </div>

      <div class="diag-card">
        <div class="diag-card-header"><span class="diag-icon">&#x1F4BE;</span> ${t("diag.storage") || "Storage"}</div>
        ${storageHtml}
      </div>

      <div class="diag-card">
        <div class="diag-card-header"><span class="diag-icon">&#x1F4F1;</span> ${t("diag.system") || "System"}</div>
        <div class="diag-stat-row"><span>Android ${data.os.android_version}</span><span>SDK ${data.os.sdk}</span></div>
        <div class="diag-stat-row"><span>${t("diag.security") || "Security"}: ${data.os.security_patch || "N/A"}</span></div>
        <div class="diag-stat-row"><span>${t("diag.build") || "Build"}: ${data.os.build_id || "N/A"}</span></div>
        ${uptimeStr ? `<div class="diag-stat-row"><span>${t("diag.uptime") || "Uptime"}: ${uptimeStr}</span></div>` : ""}
      </div>

      <div class="diag-card">
        <div class="diag-card-header"><span class="diag-icon">&#x1F513;</span> ${t("diag.security.title") || "Security & Root"}</div>
        <div class="diag-stat-row">
          <span>${t("diag.bootloader") || "Bootloader"}:</span>
          <span style="color:${blColor}; font-weight:600;">${data.bootloader}</span>
        </div>
        <div class="diag-stat-row">
          <span>${t("diag.root") || "Root"}:</span>
          <span style="color:${data.has_root ? "var(--green)" : "var(--text-dim)"};">${data.has_root ? "Yes" : "No"}</span>
        </div>
        <div class="diag-stat-row">
          <span>Magisk:</span>
          <span style="color:${data.has_magisk ? "var(--green)" : "var(--text-dim)"};">${data.has_magisk ? "Installed" : "Not installed"}</span>
        </div>
      </div>`;

    btnLoading(btn, false);
  } catch (e) {
    errorEl.style.display = "block";
    errorEl.innerHTML = `<div class="detect-box not-found"><p style="color:var(--red);">Error: ${e.message}</p></div>`;
    btnLoading(btn, false);
  }
}


// ===========================================================================
// UNIFIED DOWNLOAD + FLASH
// ===========================================================================

async function downloadAndFlash(opts) {
  const { url, filename, codename, ipfsCid, romId, romName, version, flashMethod, recoveryUrl, termEl, onDone } = opts;

  termEl.classList.add("active");
  termEl.innerHTML = "";
  appendLine(termEl, `Starting download + flash: ${romName || filename}`, "info");

  try {
    const data = await api("/api/download-and-flash", {
      method: "POST",
      body: {
        url, filename, codename,
        ipfs_cid: ipfsCid || "",
        rom_id: romId || "",
        rom_name: romName || "",
        version: version || "",
        flash_method: flashMethod || "sideload",
        recovery_url: recoveryUrl || "",
      },
    });
    if (data.error) {
      appendLine(termEl, data.error, "error");
      if (onDone) onDone("error");
      return;
    }
    streamTask(data.task_id, termEl, (status) => {
      if (onDone) onDone(status);
    }, { progress: true, progressLabel: romName || filename });
  } catch (e) {
    appendLine(termEl, String(e), "error");
    if (onDone) onDone("error");
  }
}


// ===========================================================================
// COMMUNITY LINKS
// ===========================================================================

async function loadCommunity() {
  const input = $("#community-codename");
  const codename = input.value.trim();
  if (!codename) return showInlineError(input, "Enter a device codename or model.");

  const container = $("#community-links");
  container.innerHTML = `<div class="text-dim" style="padding:1rem;">Loading...</div>`;

  try {
    const data = await api(`/api/community/${encodeURIComponent(codename)}`);
    container.innerHTML = "";

    const iconMap = {
      forum: "&#x1F4AC;",
      wiki: "&#x1F4D6;",
      device: "&#x1F4F1;",
      repair: "&#x1F527;",
      specs: "&#x1F4CA;",
      firmware: "&#x1F4E6;",
    };

    (data.links || []).forEach((link) => {
      const card = document.createElement("a");
      card.className = "community-card";
      card.href = link.device_url || link.url;
      card.target = "_blank";
      card.rel = "noopener";
      card.innerHTML = `
        <div class="community-icon">${iconMap[link.icon] || "&#x1F517;"}</div>
        <div class="community-info">
          <div class="community-name">${link.name}</div>
          <div class="community-desc">${link.desc || ""}</div>
        </div>
        <div class="community-arrow">&rarr;</div>`;
      container.appendChild(card);
    });
  } catch (e) {
    container.innerHTML = `<div style="color:var(--red); padding:1rem;">Error: ${e.message}</div>`;
  }
}


// ===========================================================================
// VERSION / CHANGELOG TRACKER
// ===========================================================================

async function loadChangelog() {
  const input = $("#changelog-codename");
  const codename = input.value.trim();
  if (!codename) return showInlineError(input, "Enter a device codename.");

  const container = $("#changelog-content");
  container.innerHTML = `<div class="text-dim" style="padding:1rem;">Checking for updates...</div>`;

  try {
    const data = await api(`/api/changelog/${encodeURIComponent(codename)}`);
    container.innerHTML = "";

    if (!data.changelogs || !data.changelogs.length) {
      container.innerHTML = `<div class="text-dim" style="padding:1rem;">${t("changelog.none") || "No version history found for this device."}</div>`;
      return;
    }

    data.changelogs.forEach((cl) => {
      const section = document.createElement("div");
      section.className = "changelog-section";

      const updateBadge = cl.update_available
        ? `<span class="changelog-update-badge">${t("changelog.update") || "Update available!"}</span>` : "";

      let buildsHtml = "";
      (cl.builds || []).forEach((b, i) => {
        const isLatest = i === 0;
        const isCurrent = cl.installed && b.version === cl.installed;
        let badge = "";
        if (isLatest) badge = `<span class="changelog-badge latest">${t("changelog.latest") || "Latest"}</span>`;
        if (isCurrent) badge += `<span class="changelog-badge current">${t("changelog.installed") || "Installed"}</span>`;
        const sizeStr = b.size ? ` &mdash; ${(b.size / (1024 * 1024)).toFixed(0)} MB` : "";

        buildsHtml += `
          <div class="changelog-entry ${isLatest ? "changelog-latest" : ""} ${isCurrent ? "changelog-current" : ""}">
            <div class="changelog-entry-header">
              <span class="changelog-version">${b.version || b.filename}</span>
              ${badge}
              <span class="changelog-date">${b.date || ""}${sizeStr}</span>
            </div>
            ${b.download_url ? `<a href="${b.download_url}" class="changelog-dl-link" target="_blank" rel="noopener">${t("btn.download") || "Download"} &darr;</a>` : ""}
          </div>`;
      });

      section.innerHTML = `
        <div class="changelog-header">
          <h3>${cl.rom_name}</h3>
          ${updateBadge}
        </div>
        <div class="changelog-builds">${buildsHtml}</div>`;
      container.appendChild(section);
    });
  } catch (e) {
    container.innerHTML = `<div style="color:var(--red); padding:1rem;">Error: ${e.message}</div>`;
  }
}


// ===========================================================================
// COMPANION TOOLS
// ===========================================================================

async function loadCompanionTools() {
  const container = $("#companion-tools-list");
  container.innerHTML = `<div class="text-dim" style="padding:1rem;">Loading...</div>`;

  try {
    const tools = await api("/api/companion-tools");
    container.innerHTML = "";

    const iconMap = {
      terminal: "&#x1F4BB;",
      root: "&#x1F9EA;",
      flash: "&#x26A1;",
      tools: "&#x1F527;",
    };

    const platformLabels = {
      android: "Android",
      windows: "Windows",
      cross: "All platforms",
    };

    tools.forEach((tool) => {
      const card = document.createElement("div");
      card.className = "companion-card";
      card.innerHTML = `
        <div class="companion-icon">${iconMap[tool.icon] || "&#x1F4E6;"}</div>
        <div class="companion-info">
          <div class="companion-name">${tool.name}</div>
          <div class="companion-desc">${tool.desc}</div>
          <div class="companion-platform">${platformLabels[tool.platform] || tool.platform}</div>
        </div>
        <div class="companion-action">
          ${tool.action === "download"
            ? `<a href="${tool.url}" class="btn btn-primary btn-sm" download>${t("btn.download") || "Download"}</a>`
            : `<a href="${tool.url}" class="btn btn-secondary btn-sm" target="_blank" rel="noopener">${t("btn.visit") || "Visit"} &rarr;</a>`
          }
        </div>`;
      container.appendChild(card);
    });
  } catch (e) {
    container.innerHTML = `<div style="color:var(--red); padding:1rem;">Error: ${e.message}</div>`;
  }
}


// ===========================================================================
// GUIDED DOWNLOAD + FLASH (one-click)
// ===========================================================================

async function guidedDownloadAndFlash() {
  const selectedOs = $(".os-card.selected");
  if (!selectedOs) return;

  const btn = $("#btn-download-flash");
  const installBtn = $("#btn-guided-install");
  const step = $("#step-install");
  const term = $("#term-guided-install");

  const url = selectedOs.dataset.downloadUrl || "";
  const filename = selectedOs.dataset.filename || "rom.zip";
  const romName = selectedOs.querySelector(".os-name")?.textContent || "ROM";
  const ipfsCid = selectedOs.dataset.ipfsCid || "";
  const recoveryUrl = selectedOs.dataset.recoveryUrl || "";
  const codename = detectedDevice?.codename || "unknown";
  const deviceName = detectedDevice ? (detectedDevice.match?.label || detectedDevice.display_name || detectedDevice.model || "your device") : "your device";

  // Confirm
  const proceed = await new Promise((resolve) => {
    showConfirm({
      icon: "&#x26A1;",
      title: t("confirm.downloadflash.title") || "Download and flash?",
      body: t("confirm.downloadflash.body") || "This will download the ROM and flash it to your device in one step.",
      details: `<strong>${t("device") || "Device"}:</strong> ${deviceName}<br><strong>${t("os") || "OS"}:</strong> ${romName}`,
      confirmText: t("confirm.downloadflash.btn") || "Download & Flash",
      onConfirm: () => resolve(true),
      onCancel: () => resolve(false),
    });
  });
  if (!proceed) return;

  btnLoading(btn, true);
  btnLoading(installBtn, true);
  setTaskActive(step, true);

  downloadAndFlash({
    url, filename, codename, ipfsCid,
    romId: selectedOs.dataset.romId || "",
    romName: selectedOs.dataset.romName || romName,
    version: selectedOs.dataset.version || "",
    flashMethod: "sideload",
    recoveryUrl,
    termEl: term,
    onDone: (status) => {
      btnLoading(btn, false);
      btnLoading(installBtn, false);
      setTaskActive(step, false);
      if (status === "done") {
        showCompletion(step, {
          icon: "&#x1F389;",
          title: t("complete.install.title") || "Installation complete!",
          subtitle: t("complete.install.subtitle") || "Your new operating system has been installed. Reboot your device from recovery to start using it.",
          summary: [
            { label: t("device") || "Device", value: deviceName },
            { label: t("os") || "OS", value: romName },
          ],
          actions: [
            { id: "configure", label: t("btn.configure") || "Configure", onClick: () => openConfigurator() },
            { id: "start-over", label: t("btn.startover") || "Start over", primary: true, onClick: () => guidedGoTo("step-category") },
          ],
        });
      }
    },
  });
}

// ===========================================================================
// ROM CONFIGURATOR
// ===========================================================================

function openConfigurator() {
  openModal("modal-configurator");
}

async function applyRomConfig() {
  const btn = $("#btn-apply-config");
  const term = $("#term-configurator");
  btnLoading(btn, true);

  const debloat = $$("#config-debloat input:checked").map((c) => c.value);
  const privacy = {
    disable_analytics: $("#cfg-analytics")?.checked || false,
    disable_location_history: $("#cfg-location")?.checked || false,
    disable_backup: $("#cfg-backup")?.checked || false,
  };
  const display = {
    dark_mode: $("#cfg-darkmode")?.checked || false,
    font_scale: $("#cfg-fontscale")?.value || "",
  };
  const locale = $("#cfg-locale")?.value.trim() || "";
  const timezone = $("#cfg-timezone")?.value.trim() || "";

  try {
    const data = await api("/api/configure-rom", {
      method: "POST",
      body: { debloat, privacy, display, locale, timezone },
    });
    if (data.error) {
      term.classList.add("active");
      term.innerHTML = "";
      appendLine(term, data.error, "error");
      btnLoading(btn, false);
      return;
    }
    streamTask(data.task_id, term, () => { btnLoading(btn, false); });
  } catch (e) {
    term.classList.add("active");
    term.innerHTML = "";
    appendLine(term, String(e), "error");
    btnLoading(btn, false);
  }
}


// ===========================================================================
// i18n initialization
// ===========================================================================

function initI18n() {
  // Build language dropdown
  const dropdown = document.getElementById("lang-dropdown");
  if (dropdown) {
    dropdown.innerHTML = "";
    for (const [code, label] of Object.entries(LANGS)) {
      const btn = document.createElement("button");
      btn.textContent = label;
      btn.className = code === currentLang ? "active" : "";
      btn.addEventListener("click", () => {
        setLang(code);
        dropdown.classList.remove("open");
        // Re-render dynamic content
        if (devicesData.length) loadDevices();
        // Update active class
        dropdown.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
      });
      dropdown.appendChild(btn);
    }
  }
  // Set initial label
  const sel = document.getElementById("lang-current");
  if (sel) sel.textContent = LANGS[currentLang];
  // Apply translations to static elements
  applyI18n();
  // Close dropdown on outside click
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".lang-switcher")) {
      const dd = document.getElementById("lang-dropdown");
      if (dd) dd.classList.remove("open");
    }
  });
}

// ---------------------------------------------------------------------------
// Scooter functions
// ---------------------------------------------------------------------------

let scooterAddress = null;

async function scooterInit() {
  // Check tools and populate model selector
  try {
    const tools = await api("/api/scooter/tools");
    const el = $("#scooter-tools-status");
    if (el) {
      const items = [];
      items.push(`Bluetooth (bleak): ${tools.bleak ? "OK" : "Not installed — run: pip install bleak"}`);
      items.push(`ST-Link: ${tools.stlink ? "OK" : "Not found"}`);
      el.style.display = "block";
      el.innerHTML = items.map(i => `<div class="line ${i.includes("OK") ? "success" : "warn"}">${i}</div>`).join("");
    }
  } catch { /* ignore */ }

  // Populate scooter model dropdown
  try {
    const scooters = await api("/api/scooters");
    const sel = $("#scooter-model-select");
    if (sel && scooters.length) {
      // Keep the first "auto" option, remove old dynamic options
      while (sel.options.length > 1) sel.remove(1);
      let currentBrand = "";
      for (const s of scooters) {
        if (s.brand !== currentBrand) {
          const grp = document.createElement("optgroup");
          grp.label = s.brand;
          sel.appendChild(grp);
          currentBrand = s.brand;
        }
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = `${s.label} (${s.flash_method})${s.shfw_supported === "yes" ? " [SHFW]" : ""}`;
        sel.appendChild(opt);
      }
    }
  } catch { /* ignore */ }
}

async function scooterScan() {
  const btn = $("#btn-scooter-scan");
  const term = $("#term-scooter");
  const resultDiv = $("#scooter-scan-results");
  const listDiv = $("#scooter-device-list");

  if (btn) { btn.disabled = true; btn.querySelector("span:last-child").textContent = "Scanning..."; }

  try {
    const res = await api("/api/scooter/scan");
    if (res.task_id) {
      streamTask(res.task_id, term, (status) => {
        if (btn) { btn.disabled = false; btn.querySelector("span:last-child").textContent = t("btn.scooter.scan") || "Scan for scooters (Bluetooth)"; }
      }, { noAbort: true });

      // Poll for scan results after a delay
      setTimeout(async () => {
        try {
          // Read the terminal output for device data
          const lines = $$("#term-scooter .line.data");
          if (lines.length && resultDiv && listDiv) {
            const last = lines[lines.length - 1];
            const devices = JSON.parse(last.textContent);
            if (devices.length) {
              resultDiv.style.display = "block";
              listDiv.innerHTML = devices.map(d => `
                <div class="goal-card" role="button" tabindex="0" onclick="scooterConnect('${d.address}', '${d.name}')">
                  <div class="goal-icon">&#x1F6F4;</div>
                  <h3>${d.name || "Unknown scooter"}</h3>
                  <p>${d.address} (RSSI: ${d.rssi || "?"})</p>
                </div>
              `).join("");
            }
          }
        } catch { /* ignore */ }
      }, 8000);
    }
  } catch (e) {
    appendLine(term, `Scan error: ${e.message || e}`, "error");
    if (btn) { btn.disabled = false; btn.querySelector("span:last-child").textContent = t("btn.scooter.scan") || "Scan for scooters (Bluetooth)"; }
  }
}

async function scooterConnect(address, name) {
  scooterAddress = address;
  const infoPanel = $("#scooter-info-panel");
  const detailsDiv = $("#scooter-info-details");
  const flashOpts = $("#scooter-flash-options");

  if (infoPanel) infoPanel.style.display = "flex";
  if (detailsDiv) detailsDiv.innerHTML = `Connecting to ${name} (${address})...`;

  try {
    const info = await api(`/api/scooter/info/${encodeURIComponent(address)}`);
    if (info.error) {
      if (detailsDiv) detailsDiv.innerHTML = `<span class="text-error">${info.error}</span>`;
      return;
    }
    if (detailsDiv) {
      detailsDiv.innerHTML = `
        <table class="info-table">
          <tr><td>Model</td><td>${info.model || "Unknown"}</td></tr>
          <tr><td>Serial</td><td>${info.serial || "—"}</td></tr>
          <tr><td>UID</td><td><code>${info.uid || "—"}</code></td></tr>
          <tr><td>DRV/ESC</td><td>${info.fw_drv || "—"}</td></tr>
          <tr><td>BLE</td><td>${info.fw_ble || "—"}</td></tr>
          <tr><td>BMS</td><td>${info.fw_bms || "—"}</td></tr>
          <tr><td>MCU</td><td>${info.fw_mcu || "—"}</td></tr>
          <tr><td>VCU</td><td>${info.fw_vcu || "—"}</td></tr>
        </table>
      `;
    }
    if (flashOpts) flashOpts.style.display = "block";
  } catch (e) {
    if (detailsDiv) detailsDiv.innerHTML = `<span class="text-error">Connection failed: ${e.message || e}</span>`;
  }
}

async function scooterFlash() {
  if (!scooterAddress) { alert("No scooter connected. Scan and select a scooter first."); return; }

  const fwPath = ($("#scooter-fw-path") || {}).value || "";
  const component = ($("#scooter-component") || {}).value || "esc";
  const modelId = ($("#scooter-model-select") || {}).value || "";
  const term = $("#term-scooter");
  const btn = $("#btn-scooter-flash");

  if (btn) btn.disabled = true;

  try {
    let res;
    if (fwPath) {
      res = await api("/api/scooter/flash", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address: scooterAddress, fw_path: fwPath, component }),
      });
    } else {
      res = await api("/api/scooter/flash-cfw", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address: scooterAddress, scooter_id: modelId, options: {} }),
      });
    }
    if (res.task_id) {
      streamTask(res.task_id, term, (status) => {
        if (btn) btn.disabled = false;
      }, { progress: true, progressLabel: "Flashing scooter firmware" });
    } else if (res.error) {
      appendLine(term, res.error, "error");
      if (btn) btn.disabled = false;
    }
  } catch (e) {
    appendLine(term, `Flash error: ${e.message || e}`, "error");
    if (btn) btn.disabled = false;
  }
}


// ---------------------------------------------------------------------------
// Safety: Pre-flight checklist
// ---------------------------------------------------------------------------

function updatePreflightFields() {
  const type = $("#preflight-type").value;
  $("#preflight-phone-fields").style.display = type === "phone" ? "" : "none";
  $("#preflight-scooter-fields").style.display = type === "scooter" ? "" : "none";
}

if ($("#preflight-type")) {
  $("#preflight-type").addEventListener("change", updatePreflightFields);
}

async function runPreflight() {
  const type = $("#preflight-type").value;
  let url, body;
  if (type === "phone") {
    url = "/api/preflight/phone";
    body = { fw_path: $("#preflight-fw-path").value };
  } else {
    url = "/api/preflight/scooter";
    body = {
      address: $("#preflight-ble-address").value,
      fw_path: $("#preflight-fw-path").value,
    };
  }

  const res = await api(url, { method: "POST", body });
  const resultsEl = $("#preflight-results");
  const summaryEl = $("#preflight-summary");
  const checksEl = $("#preflight-checks");
  resultsEl.style.display = "";
  checksEl.innerHTML = "";

  if (res.passed) {
    summaryEl.textContent = `All required checks passed (${res.passed_count}/${res.total})`;
    summaryEl.style.color = "var(--accent, #00c896)";
  } else {
    summaryEl.textContent = `Some checks failed (${res.passed_count}/${res.total} passed)`;
    summaryEl.style.color = "var(--danger, #e74c3c)";
  }

  for (const check of res.checks) {
    const div = document.createElement("div");
    div.className = "device-item";
    const icon = check.passed ? "\u2705" : (check.required ? "\u274C" : "\u26A0\uFE0F");
    const reqTag = check.required ? "" : " <span style='opacity:0.5'>(optional)</span>";
    div.innerHTML = `
      <div style="display:flex;align-items:center;gap:0.75rem;">
        <span style="font-size:1.3em;">${icon}</span>
        <div>
          <strong>${check.label}</strong>${reqTag}<br>
          <span class="text-dim">${check.detail}</span>
        </div>
      </div>`;
    checksEl.appendChild(div);
  }
}


// ---------------------------------------------------------------------------
// Safety: Firmware registry
// ---------------------------------------------------------------------------

async function loadRegistry() {
  const container = $("#registry-entries");
  container.innerHTML = "<em>Loading...</em>";
  const entries = await api("/api/registry");
  container.innerHTML = "";

  if (!entries.length) {
    container.innerHTML = "<p class='muted-hint'>No firmware has been registered yet. Entries are created automatically when you flash.</p>";
    return;
  }

  for (const entry of entries) {
    const div = document.createElement("div");
    div.className = "device-item";
    const date = entry.flashed_at ? new Date(entry.flashed_at).toLocaleString() : "unknown";
    div.innerHTML = `
      <div>
        <strong>${entry.filename}</strong>
        ${entry.device_label ? `<span class="text-dim"> \u2014 ${entry.device_label}</span>` : ""}
        <br>
        <span class="text-dim" style="font-family:monospace;font-size:0.8em;">${entry.sha256}</span><br>
        <span class="text-dim">${entry.component || ""} \u2022 ${entry.flash_method || ""} \u2022 ${date}</span>
        ${entry.version ? `<br><span class="text-dim">Version: ${entry.version}</span>` : ""}
      </div>`;
    container.appendChild(div);
  }
}

async function verifyFirmware() {
  const path = prompt("Enter the path to a firmware file to verify:");
  if (!path) return;
  const resultEl = $("#registry-verify-result");
  resultEl.style.display = "";
  resultEl.innerHTML = "<em>Verifying...</em>";

  const res = await api("/api/registry/verify", { method: "POST", body: { fw_path: path } });
  if (res.error) {
    resultEl.innerHTML = `<span style="color:var(--danger)">\u274C ${res.error}</span>`;
    return;
  }

  if (res.known) {
    const m = res.matches[0];
    resultEl.innerHTML = `
      <div style="color:var(--accent,#00c896);">
        <strong>\u2705 Known firmware</strong><br>
        <span style="font-family:monospace;font-size:0.85em;">${res.sha256}</span><br>
        Previously flashed as: ${m.filename} (${m.component || "unknown"}, ${m.flash_method || "unknown"})<br>
        ${m.device_label ? `Device: ${m.device_label}` : ""}
      </div>`;
  } else {
    resultEl.innerHTML = `
      <div style="color:var(--warning,#f39c12);">
        <strong>\u26A0\uFE0F Unknown firmware</strong><br>
        <span style="font-family:monospace;font-size:0.85em;">${res.sha256}</span><br>
        This file has never been flashed by Osmosis before.
        <br>File: ${res.filename} (${(res.size / 1024 / 1024).toFixed(1)} MB)
      </div>`;
  }
}


// ---------------------------------------------------------------------------
// Safety: Recovery guides
// ---------------------------------------------------------------------------

async function loadRecoveryGuides() {
  const listEl = $("#recovery-guide-list");
  const contentEl = $("#recovery-guide-content");
  contentEl.style.display = "none";
  listEl.style.display = "";
  listEl.innerHTML = "<em>Loading...</em>";

  const guides = await api("/api/recovery");
  listEl.innerHTML = "";

  const icons = { samsung: "\uD83D\uDCF1", scooter: "\uD83D\uDEF4", bootable: "\uD83D\uDCBF" };
  for (const g of guides) {
    const card = document.createElement("div");
    card.className = "card";
    card.style.cursor = "pointer";
    card.innerHTML = `
      <div class="card-header">
        <div class="card-icon">${icons[g.id] || "\uD83D\uDEDF"}</div>
        <h3>${g.title}</h3>
      </div>
      <p>${g.step_count} steps</p>`;
    card.addEventListener("click", () => showRecoveryGuide(g.id));
    listEl.appendChild(card);
  }
}

async function showRecoveryGuide(guideId) {
  const listEl = $("#recovery-guide-list");
  const contentEl = $("#recovery-guide-content");

  const guide = await api(`/api/recovery/${guideId}`);
  if (guide.error) return;

  listEl.style.display = "none";
  contentEl.style.display = "";
  contentEl.innerHTML = "";

  const backBtn = document.createElement("button");
  backBtn.className = "btn btn-secondary";
  backBtn.innerHTML = "\u2190 Back to guides";
  backBtn.addEventListener("click", () => {
    contentEl.style.display = "none";
    listEl.style.display = "";
  });
  contentEl.appendChild(backBtn);

  const h2 = document.createElement("h2");
  h2.textContent = guide.title;
  h2.style.margin = "1rem 0 0.5rem";
  contentEl.appendChild(h2);

  for (const step of guide.steps) {
    const div = document.createElement("div");
    div.style.cssText = "margin:1rem 0;padding:1rem;border-radius:8px;background:var(--card-bg,#1a1f2e);";
    let html = `<h3 style="margin:0 0 0.5rem;">${step.title}</h3>`;
    html += `<p style="margin:0;">${step.description}</p>`;
    if (step.warning) {
      html += `<p style="margin:0.5rem 0 0;padding:0.5rem;border-radius:4px;background:rgba(231,76,60,0.15);color:#e74c3c;"><strong>Warning:</strong> ${step.warning}</p>`;
    }
    div.innerHTML = html;
    contentEl.appendChild(div);
  }
}


// ---------------------------------------------------------------------------
// Safety: Scooter backup
// ---------------------------------------------------------------------------

async function startScooterBackup() {
  const address = $("#scooter-backup-address").value.trim();
  if (!address) {
    alert("Enter a BLE address first. Use the scooter scan to find your scooter.");
    return;
  }

  const term = $("#term-scooter-backup");
  const res = await api("/api/scooter/backup", { method: "POST", body: { address } });

  if (res.task_id) {
    streamTask(res.task_id, term, () => loadScooterBackups(), {
      progress: true,
      progressLabel: "Backing up scooter firmware",
    });
  } else if (res.error) {
    appendLine(term, res.error, "error");
  }
}

async function loadScooterBackups() {
  const container = $("#scooter-backup-list");
  if (!container) return;
  container.innerHTML = "<em>Loading...</em>";
  const backups = await api("/api/scooter/backups");
  container.innerHTML = "";

  if (!backups.length) {
    container.innerHTML = "<p class='muted-hint'>No scooter backups yet.</p>";
    return;
  }

  for (const b of backups) {
    const div = document.createElement("div");
    div.className = "device-item";
    div.innerHTML = `
      <div>
        <strong>${b.model}</strong> <span class="text-dim">(${b.serial})</span><br>
        <span class="text-dim">DRV: ${b.drv_version || "?"} \u2022 ${b.has_firmware_dump ? "\u2705 Full dump" : "\u2139\uFE0F Info only"}</span><br>
        <span class="text-dim" style="font-size:0.85em;">${b.name}</span>
      </div>`;
    container.appendChild(div);
  }
}


// ---------------------------------------------------------------------------
// Scooter Dashboard
// ---------------------------------------------------------------------------

let _dashEventSource = null;
const _DASH_ACTIONS = { speed_mode: 0x75, lock: 0x70, tail_light: 0x73 };

function dashboardConnect() {
  const address = $("#dash-ble-address").value.trim();
  if (!address) return;

  const status = $("#dash-status");
  status.textContent = "Connecting...";
  $("#dash-telemetry").style.display = "none";
  $("#btn-dash-connect").style.display = "none";
  $("#btn-dash-disconnect").style.display = "inline-flex";

  if (_dashEventSource) _dashEventSource.close();
  _dashEventSource = new EventSource(`/api/scooter/telemetry-stream/${encodeURIComponent(address)}`);

  _dashEventSource.onmessage = (e) => {
    try {
      const d = JSON.parse(e.data);
      if (d.error) {
        status.innerHTML = `<span style="color:var(--red);">${d.error}</span>`;
        dashboardDisconnect();
        return;
      }
      status.innerHTML = `<span style="color:var(--green);">Connected</span>`;
      $("#dash-telemetry").style.display = "block";
      $("#dash-speed").textContent = d.speed_kmh.toFixed(1);
      $("#dash-battery").textContent = d.battery_percent;
      $("#dash-temp").textContent = d.temperature_c.toFixed(1);
      $("#dash-mode").textContent = d.speed_mode;
      $("#dash-voltage").textContent = d.battery_voltage.toFixed(1);
      $("#dash-current").textContent = d.battery_current_a.toFixed(1);
      $("#dash-odo").textContent = d.odometer_km.toFixed(1);
      $("#dash-trip").textContent = d.trip_km.toFixed(2);
      $("#dash-avg-speed").textContent = d.avg_speed_kmh.toFixed(1);
      const mins = Math.floor(d.uptime_seconds / 60);
      const secs = d.uptime_seconds % 60;
      $("#dash-uptime").textContent = `${mins}m ${secs}s`;
      $("#dash-error").textContent = d.error_code || "None";
      $("#dash-lock").textContent = d.locked ? "Locked" : "Unlocked";
    } catch { /* ignore parse errors */ }
  };

  _dashEventSource.onerror = () => {
    status.innerHTML = `<span style="color:var(--red);">Connection lost</span>`;
    dashboardDisconnect();
  };
}

function dashboardDisconnect() {
  if (_dashEventSource) {
    _dashEventSource.close();
    _dashEventSource = null;
  }
  $("#btn-dash-connect").style.display = "inline-flex";
  $("#btn-dash-disconnect").style.display = "none";
}

async function dashAction(name, value) {
  const address = $("#dash-ble-address").value.trim();
  if (!address) return;
  const reg = _DASH_ACTIONS[name];
  if (reg === undefined) return;
  try {
    await api("/api/scooter/register/write", {
      method: "POST",
      body: { address, register: reg, value: [value] },
    });
  } catch (e) {
    console.error("Dashboard action failed:", e);
  }
}


// ---------------------------------------------------------------------------
// CFW Builder
// ---------------------------------------------------------------------------

let _cfwPatches = [];
let _cfwLastResult = null;

async function initCfwBuilder() {
  const sel = $("#cfw-scooter-id");
  if (sel.options.length > 1) return; // already loaded

  const families = await api("/api/cfw/families");
  // Also load scooter presets for labels
  const scooters = await api("/api/scooters");
  const labelMap = {};
  for (const s of scooters) labelMap[s.id] = s.label;

  for (const fam of families) {
    const opt = document.createElement("option");
    opt.value = fam.id;
    opt.textContent = labelMap[fam.id] || fam.id;
    sel.appendChild(opt);
  }
}

async function loadCfwPatches() {
  const scooterId = $("#cfw-scooter-id").value;
  const container = $("#cfw-patches-list");
  const wrapper = $("#cfw-patches-container");

  if (!scooterId) {
    wrapper.style.display = "none";
    return;
  }

  const patches = await api(`/api/cfw/patches/${scooterId}`);
  if (patches.error) {
    container.innerHTML = `<p style="color:var(--danger)">${patches.error}</p>`;
    wrapper.style.display = "";
    return;
  }

  _cfwPatches = patches;
  container.innerHTML = "";
  wrapper.style.display = "";

  const categories = {};
  for (const p of patches) {
    if (!categories[p.category]) categories[p.category] = [];
    categories[p.category].push(p);
  }

  for (const [cat, catPatches] of Object.entries(categories)) {
    const catTitle = document.createElement("h4");
    catTitle.textContent = cat.charAt(0).toUpperCase() + cat.slice(1);
    catTitle.style.cssText = "margin:0.75rem 0 0.25rem; text-transform:capitalize; opacity:0.7;";
    container.appendChild(catTitle);

    for (const patch of catPatches) {
      const card = document.createElement("div");
      card.style.cssText = "margin:0.5rem 0;padding:0.75rem;border-radius:8px;background:var(--card-bg,#1a1f2e);";
      card.dataset.patchId = patch.id;

      let html = `
        <label style="display:flex;align-items:center;gap:0.5rem;cursor:pointer;font-weight:bold;">
          <input type="checkbox" class="cfw-patch-toggle" data-patch="${patch.id}">
          ${patch.label}
        </label>
        <p class="text-dim" style="margin:0.25rem 0 0.5rem;font-size:0.9em;">${patch.description}</p>`;

      if (patch.warning) {
        html += `<p style="font-size:0.85em;color:var(--warning,#f39c12);margin:0 0 0.5rem;">${patch.warning}</p>`;
      }

      html += `<div class="cfw-params" data-patch="${patch.id}" style="display:none;">`;
      for (const param of patch.params) {
        html += `<div class="form-group" style="margin:0.25rem 0;">`;
        html += `<label style="font-size:0.9em;">${param.label}`;
        if (param.unit) html += ` <span class="text-dim">(${param.unit})</span>`;
        html += `</label>`;

        if (param.type === "bool") {
          html += `<select class="cfw-param" data-patch="${patch.id}" data-param="${param.id}">
            <option value="false" ${!param.default ? "selected" : ""}>Off</option>
            <option value="true" ${param.default ? "selected" : ""}>On</option>
          </select>`;
        } else if (param.type === "select" && param.options) {
          html += `<select class="cfw-param" data-patch="${patch.id}" data-param="${param.id}">`;
          for (const opt of param.options) {
            html += `<option value="${opt.value}" ${opt.value === param.default ? "selected" : ""}>${opt.label}</option>`;
          }
          html += `</select>`;
        } else {
          html += `<input type="number" class="cfw-param" data-patch="${patch.id}" data-param="${param.id}"
            value="${param.default}" min="${param.min || ""}" max="${param.max || ""}" step="${param.step || 1}">`;
        }

        if (param.warning) {
          html += `<span class="text-dim" style="font-size:0.8em;">${param.warning}</span>`;
        }
        html += `</div>`;
      }
      html += `</div>`;

      card.innerHTML = html;
      container.appendChild(card);
    }
  }

  // Toggle params visibility when patch checkbox changes
  $$(".cfw-patch-toggle").forEach(cb => {
    cb.addEventListener("change", () => {
      const params = $(`.cfw-params[data-patch="${cb.dataset.patch}"]`);
      if (params) params.style.display = cb.checked ? "" : "none";
    });
  });
}

function _gatherCfwConfig() {
  const config = {};
  $$(".cfw-patch-toggle:checked").forEach(cb => {
    const patchId = cb.dataset.patch;
    config[patchId] = {};
    $$(`.cfw-param[data-patch="${patchId}"]`).forEach(input => {
      let val = input.value;
      if (input.type === "number") val = parseFloat(val);
      else if (val === "true") val = true;
      else if (val === "false") val = false;
      config[patchId][input.dataset.param] = val;
    });
  });
  return config;
}

async function buildCfw() {
  const scooterId = $("#cfw-scooter-id").value;
  const fwPath = $("#cfw-fw-path").value;
  const config = _gatherCfwConfig();

  if (!scooterId) return alert("Select a scooter model.");
  if (!fwPath) return alert("Select a stock firmware file.");
  if (!Object.keys(config).length) return alert("Enable at least one patch.");

  const res = await api("/api/cfw/build", {
    method: "POST",
    body: { scooter_id: scooterId, fw_path: fwPath, config },
  });

  if (res.error) {
    alert(res.error);
    return;
  }

  _cfwLastResult = res;
  const resultEl = $("#cfw-result");
  resultEl.style.display = "";

  // Info
  const infoEl = $("#cfw-result-info");
  infoEl.innerHTML = `
    <strong>Patches applied:</strong> ${res.patches_applied.join(", ")}<br>
    <strong>Size:</strong> ${(res.size / 1024).toFixed(1)} KB<br>
    <strong>SHA256:</strong> <span style="font-family:monospace;font-size:0.85em;">${res.patched_sha256}</span>
    ${res.warnings.length ? `<br><strong style="color:var(--warning)">Warnings:</strong> ${res.warnings.join("; ")}` : ""}
  `;

  // Diff
  const diffEl = $("#cfw-result-diff");
  diffEl.innerHTML = "";
  for (const d of res.diff) {
    const div = document.createElement("div");
    div.className = "device-item";
    div.innerHTML = `
      <span style="font-family:monospace;">${d.offset}</span>
      <span class="text-dim">${d.original}</span> &rarr;
      <span style="color:var(--accent,#00c896)">${d.patched}</span>
      <span class="text-dim"> \u2014 ${d.description}</span>`;
    diffEl.appendChild(div);
  }
}

async function downloadCfw() {
  if (!_cfwLastResult || !_cfwLastResult.zip_path) return;
  // Trigger download via hidden form
  const a = document.createElement("a");
  a.href = `/api/cfw/download`;
  a.style.display = "none";
  // Use fetch + blob for POST download
  const res = await fetch("/api/cfw/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ zip_path: _cfwLastResult.zip_path }),
  });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  a.href = url;
  a.download = _cfwLastResult.zip_path.split("/").pop();
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function flashCfw() {
  if (!_cfwLastResult || !_cfwLastResult.fw_path) return;
  const address = prompt("Enter scooter BLE address (XX:XX:XX:XX:XX:XX):");
  if (!address) return;

  const scooterId = $("#cfw-scooter-id").value;
  const config = _gatherCfwConfig();
  const fwPath = $("#cfw-fw-path").value;
  const term = $("#term-cfw-flash");

  const res = await api("/api/cfw/build-and-flash", {
    method: "POST",
    body: { scooter_id: scooterId, fw_path: fwPath, config, address },
  });

  if (res.task_id) {
    streamTask(res.task_id, term, () => {}, {
      progress: true,
      progressLabel: "Building and flashing CFW",
    });
  } else if (res.error) {
    appendLine(term, res.error, "error");
  }
}

function saveCfwConfig() {
  const scooterId = $("#cfw-scooter-id").value;
  if (!scooterId) return alert("Select a scooter first.");
  const config = _gatherCfwConfig();
  const data = JSON.stringify({ scooter_id: scooterId, config }, null, 2);
  const blob = new Blob([data], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `osmosis-cfw-${scooterId}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
}

function loadCfwConfig() {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".json";
  input.addEventListener("change", async () => {
    const file = input.files[0];
    if (!file) return;
    const text = await file.text();
    try {
      const data = JSON.parse(text);
      if (data.scooter_id) {
        $("#cfw-scooter-id").value = data.scooter_id;
        await loadCfwPatches();
      }
      if (data.config) {
        // Apply config to UI
        for (const [patchId, params] of Object.entries(data.config)) {
          const toggle = $(`.cfw-patch-toggle[data-patch="${patchId}"]`);
          if (toggle) {
            toggle.checked = true;
            toggle.dispatchEvent(new Event("change"));
          }
          for (const [paramId, value] of Object.entries(params)) {
            const input = $(`.cfw-param[data-patch="${patchId}"][data-param="${paramId}"]`);
            if (input) input.value = value;
          }
        }
      }
    } catch (e) {
      alert("Invalid config file: " + e.message);
    }
  });
  input.click();
}


// ---------------------------------------------------------------------------
// OS Builder
// ---------------------------------------------------------------------------

let osBuilderOptions = null;

async function osBuilderInit() {
  if (osBuilderOptions) {
    osUpdateDropdowns();
    return;
  }
  try {
    const res = await api("/api/os-builder/options");
    osBuilderOptions = await res.json();
    osUpdateDropdowns();
    osBindBaseCards();
    osBindNetworkToggle();
    osBindEstimate();
  } catch (e) {
    console.error("Failed to load OS builder options", e);
  }
}

function osGetSelectedBase() {
  const active = $(".os-base-card.active");
  return active ? active.dataset.osBase : "debian";
}

function osUpdateDropdowns() {
  const base = osGetSelectedBase();
  const info = osBuilderOptions.bases[base];

  // Suite
  const suiteEl = $("#os-suite");
  suiteEl.innerHTML = "";
  if (info.suites.length === 0) {
    suiteEl.innerHTML = '<option value="">Rolling release</option>';
  } else {
    for (const s of info.suites) {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      if (s === info.default_suite) opt.selected = true;
      suiteEl.appendChild(opt);
    }
  }

  // Architecture
  const archEl = $("#os-arch");
  archEl.innerHTML = "";
  for (const a of info.arch) {
    const opt = document.createElement("option");
    opt.value = a;
    opt.textContent = a;
    archEl.appendChild(opt);
  }

  // Target devices
  const targetEl = $("#os-target");
  targetEl.innerHTML = "";
  for (const d of osBuilderOptions.target_devices) {
    const opt = document.createElement("option");
    opt.value = d.id;
    opt.textContent = d.label;
    targetEl.appendChild(opt);
  }

  // Desktop environments
  const desktopEl = $("#os-desktop");
  desktopEl.innerHTML = "";
  for (const d of osBuilderOptions.desktops) {
    const opt = document.createElement("option");
    opt.value = d.id;
    opt.textContent = d.label;
    desktopEl.appendChild(opt);
  }

  // Output formats
  const outputEl = $("#os-output");
  outputEl.innerHTML = "";
  for (const f of osBuilderOptions.output_formats) {
    const opt = document.createElement("option");
    opt.value = f.id;
    opt.textContent = `${f.label} — ${f.desc}`;
    outputEl.appendChild(opt);
  }
}

function osBindBaseCards() {
  $$(".os-base-card").forEach((card) => {
    card.addEventListener("click", () => {
      $$(".os-base-card").forEach((c) => c.classList.remove("active"));
      card.classList.add("active");
      osUpdateDropdowns();
      osUpdateEstimate();
    });
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); card.click(); }
    });
  });
}

function osBindNetworkToggle() {
  const netSel = $("#os-network");
  if (!netSel) return;
  netSel.addEventListener("change", () => {
    const isStatic = netSel.value === "static";
    const ipGroup = $("#os-static-ip-group");
    const extraGroup = $("#os-static-extra");
    if (ipGroup) ipGroup.style.display = isStatic ? "" : "none";
    if (extraGroup) extraGroup.style.display = isStatic ? "" : "none";
  });
}

function osBindEstimate() {
  // Recalculate estimate when key fields change
  for (const id of ["os-desktop", "os-packages", "os-output"]) {
    const el = $(`#${id}`);
    if (el) el.addEventListener("change", osUpdateEstimate);
    if (el) el.addEventListener("input", osUpdateEstimate);
  }
}

async function osUpdateEstimate() {
  const profile = osCollectProfile();
  try {
    const res = await api("/api/os-builder/estimate", {
      method: "POST",
      body: profile,
    });
    const data = await res.json();
    const panel = $("#os-size-estimate");
    const text = $("#os-size-estimate-text");
    if (panel && text) {
      panel.style.display = "";
      text.innerHTML = `
        <strong>Estimated size:</strong> ~${data.total_mb} MB
        (base: ${data.base_mb} MB, desktop: ${data.desktop_mb} MB, packages: ${data.packages_mb} MB)<br>
        <strong>Recommended image size:</strong> ${data.recommended_image_mb} MB
      `;
      // Auto-update image size suggestion
      const imgSize = $("#os-image-size");
      if (imgSize && parseInt(imgSize.value) < data.recommended_image_mb) {
        imgSize.value = data.recommended_image_mb;
      }
    }
  } catch {}
}

function osCollectProfile() {
  const sshKeys = ($("#os-ssh-keys")?.value || "").split("\n").filter((k) => k.trim());
  const dns = ($("#os-dns")?.value || "1.1.1.1, 9.9.9.9").split(",").map((d) => d.trim()).filter(Boolean);
  const extraPkgs = ($("#os-packages")?.value || "").split(/\s+/).filter(Boolean);

  return {
    name: $("#os-name")?.value || "my-os",
    base: osGetSelectedBase(),
    suite: $("#os-suite")?.value || "",
    arch: $("#os-arch")?.value || "amd64",
    target_device: $("#os-target")?.value || "generic-x86_64",
    output_format: $("#os-output")?.value || "img",
    image_size_mb: parseInt($("#os-image-size")?.value || "4096"),
    hostname: $("#os-hostname")?.value || "osmosis",
    locale: $("#os-locale")?.value || "en_US.UTF-8",
    timezone: $("#os-timezone")?.value || "UTC",
    keyboard_layout: $("#os-keyboard")?.value || "us",
    username: $("#os-username")?.value || "user",
    password: $("#os-password")?.value || "",
    ssh_keys: sshKeys,
    extra_packages: extraPkgs,
    desktop: $("#os-desktop")?.value || "none",
    network: $("#os-network")?.value || "dhcp",
    static_ip: $("#os-static-ip")?.value || "",
    gateway: $("#os-gateway")?.value || "",
    dns: dns,
    firewall: $("#os-firewall")?.value || "none",
    disk_layout: $("#os-disk-layout")?.value || "auto",
    image_size_mb: parseInt($("#os-image-size")?.value || "4096"),
    post_install_script: $("#os-post-install")?.value || "",
    ipfs_publish: $("#os-ipfs-publish")?.checked || false,
  };
}

async function osBuildStart() {
  const profile = osCollectProfile();
  const btn = $("#btn-os-build");
  if (btn) btn.disabled = true;

  try {
    const res = await api("/api/os-builder/build", {
      method: "POST",
      body: profile,
    });
    const data = await res.json();
    if (data.error) {
      alert("Build error: " + data.error);
      if (btn) btn.disabled = false;
      return;
    }
    streamTask(data.task_id, $("#term-os-build"), (status) => {
      if (btn) btn.disabled = false;
      if (status === "done") {
        appendLine($("#term-os-build"), "Build complete! Check ~/Osmosis-downloads/os-builds/", "success");
      }
    });
  } catch (e) {
    alert("Failed to start build: " + e.message);
    if (btn) btn.disabled = false;
  }
}

async function osPreviewConfig() {
  const profile = osCollectProfile();
  try {
    const res = await api("/api/os-builder/preview", {
      method: "POST",
      body: profile,
    });
    const data = await res.json();
    if (data.error) {
      alert("Preview error: " + data.error);
      return;
    }
    const previewEl = $("#os-config-preview");
    const labelEl = $("#os-preview-label");
    const contentEl = $("#os-preview-content");
    if (previewEl && labelEl && contentEl) {
      previewEl.style.display = "";
      labelEl.textContent = `Generated ${data.type}: ${data.filename}`;
      contentEl.textContent = data.content;
    }
  } catch (e) {
    alert("Failed to preview config: " + e.message);
  }
}

async function osSaveProfile() {
  const profile = osCollectProfile();
  try {
    const res = await api("/api/os-builder/profiles", {
      method: "POST",
      body: profile,
    });
    const data = await res.json();
    if (data.error) {
      alert("Save error: " + data.error);
      return;
    }
    alert(`Profile saved: ${data.path}`);
  } catch (e) {
    alert("Failed to save profile: " + e.message);
  }
}

async function osLoadProfile() {
  try {
    const res = await api("/api/os-builder/profiles");
    const profiles = await res.json();
    if (!profiles.length) {
      alert("No saved profiles found.");
      return;
    }
    const names = profiles.map((p) => p.name);
    const choice = prompt("Available profiles:\n" + names.map((n, i) => `${i + 1}. ${n}`).join("\n") + "\n\nEnter profile name:");
    if (!choice) return;

    const profileRes = await api(`/api/os-builder/profiles/${encodeURIComponent(choice)}`);
    const profile = await profileRes.json();
    if (profile.error) {
      alert("Load error: " + profile.error);
      return;
    }
    osApplyProfile(profile);
  } catch (e) {
    alert("Failed to load profile: " + e.message);
  }
}

function osApplyProfile(p) {
  // Select base card
  $$(".os-base-card").forEach((c) => c.classList.remove("active"));
  const baseCard = $(`.os-base-card[data-os-base="${p.base}"]`);
  if (baseCard) baseCard.classList.add("active");
  osUpdateDropdowns();

  // Fill form fields
  const fields = {
    "os-name": p.name,
    "os-suite": p.suite,
    "os-arch": p.arch,
    "os-target": p.target_device,
    "os-hostname": p.hostname,
    "os-username": p.username,
    "os-password": p.password || "",
    "os-locale": p.locale,
    "os-timezone": p.timezone,
    "os-keyboard": p.keyboard_layout,
    "os-desktop": p.desktop,
    "os-output": p.output_format,
    "os-packages": (p.extra_packages || []).join(" "),
    "os-network": p.network,
    "os-static-ip": p.static_ip || "",
    "os-gateway": p.gateway || "",
    "os-dns": (p.dns || []).join(", "),
    "os-firewall": p.firewall,
    "os-disk-layout": p.disk_layout,
    "os-image-size": p.image_size_mb,
    "os-post-install": p.post_install_script || "",
  };
  for (const [id, val] of Object.entries(fields)) {
    const el = $(`#${id}`);
    if (el) el.value = val;
  }
  if (p.ssh_keys) {
    const el = $("#os-ssh-keys");
    if (el) el.value = (p.ssh_keys || []).join("\n");
  }
  // Trigger network toggle
  const netSel = $("#os-network");
  if (netSel) netSel.dispatchEvent(new Event("change"));

  osUpdateEstimate();
}
