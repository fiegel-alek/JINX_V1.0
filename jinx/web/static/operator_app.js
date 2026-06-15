const operator = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
  usernameInput: document.querySelector("#username-input"),
  sessionButton: document.querySelector("#session-button"),
  clearSessionButton: document.querySelector("#clear-session-button"),
  sessionSummary: document.querySelector("#session-summary"),
  reporterId: document.querySelector("#reporter-id"),
  deviceId: document.querySelector("#device-id"),
  roleSelect: document.querySelector("#role-select"),
  syncState: document.querySelector("#sync-state"),
  refreshButton: document.querySelector("#refresh-button"),
  drawer: document.querySelector("#action-drawer"),
  drawerToggle: document.querySelector("#drawer-toggle"),
  actionGrid: document.querySelector("#action-grid"),
  selectedActionLabel: document.querySelector("#selected-action-label"),
  operatorMap: document.querySelector("#operator-map"),
  selectionCard: document.querySelector("#selection-card"),
  advisoryList: document.querySelector("#advisory-list"),
  reportList: document.querySelector("#report-list"),
  brainList: document.querySelector("#brain-list"),
  reportForm: document.querySelector("#report-form"),
  brainChatForm: document.querySelector("#brain-chat-form"),
  receiptCard: document.querySelector("#receipt-card"),
  syncQueueButton: document.querySelector("#sync-queue-button"),
};

const QUEUE_KEY = "jinx-operator-mini-queue-v1";
const RECEIPT_KEY = "jinx-operator-mini-receipt-v1";
const SESSION_KEY = "jinx-operator-session-token";
const PACKAGE_NAME = "operator";
const USERNAME_BY_ROLE = {
  operator: "operator-alpha",
  system_administrator: "systemadministrator",
};

let workspaceState = null;
let selectedMarkerId = "";
let selectedActionId = "position";
let lastReceipt = loadReceipt();

function activeRole() {
  return operator.roleSelect.value;
}

function activeSessionToken() {
  return localStorage.getItem(SESSION_KEY) || "";
}

function suggestedUsername() {
  return USERNAME_BY_ROLE[activeRole()] || "operator-alpha";
}

function syncSuggestedUsername(force = false) {
  if (operator.usernameInput.readOnly) return;
  const current = operator.usernameInput.value.trim();
  if (force || !current || Object.values(USERNAME_BY_ROLE).includes(current)) {
    operator.usernameInput.value = suggestedUsername();
  }
}

function activeUsername() {
  return operator.usernameInput.value.trim() || suggestedUsername();
}

function reporterId() {
  return operator.reporterId.value.trim() || "operator-alpha";
}

function deviceId() {
  return operator.deviceId.value.trim() || "operator-mini-001";
}

function requestHeaders(extra = {}) {
  const sessionToken = activeSessionToken();
  return sessionToken
    ? {
      "X-JINX-Role": activeRole(),
      "X-JINX-Package": PACKAGE_NAME,
      "X-JINX-Session": sessionToken,
      "X-JINX-Reporter": reporterId(),
      "X-JINX-Device": deviceId(),
      ...extra,
    }
    : {
      "X-JINX-Role": activeRole(),
      "X-JINX-Package": PACKAGE_NAME,
      "X-JINX-Reporter": reporterId(),
      "X-JINX-Device": deviceId(),
      ...extra,
    };
}

async function getJSON(url) {
  const response = await fetch(url, { headers: requestHeaders() });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `${response.status} ${response.statusText}`);
  return body;
}

async function postJSON(url, payload = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: requestHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `${response.status} ${response.statusText}`);
  return body;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function pairGrid(pairs) {
  const rows = pairs.filter(([, value]) => value !== undefined && value !== null && String(value) !== "");
  if (!rows.length) return "";
  return `
    <div class="data-pair-grid">
      ${rows.map(([label, value]) => `
        <div class="data-pair">
          <span class="data-pair-label">${escapeHTML(label)}</span>
          <span class="data-pair-value">${escapeHTML(value)}</span>
        </div>
      `).join("")}
    </div>
  `;
}

function formatTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "unknown" : date.toLocaleTimeString();
}

function setStatus(ok, text) {
  operator.apiStatus.classList.toggle("ok", ok);
  operator.apiStatus.classList.toggle("error", !ok);
  operator.apiStatusText.textContent = text;
}

function renderSession(sessionDoc, entitlements) {
  const session = sessionDoc.session || null;
  if (!session && activeSessionToken()) {
    localStorage.removeItem(SESSION_KEY);
  }
  if (session) {
    const role = String((session.roles || [])[0] || activeRole());
    if (operator.roleSelect.querySelector(`option[value="${role}"]`)) {
      operator.roleSelect.value = role;
    }
    operator.roleSelect.disabled = true;
    operator.usernameInput.readOnly = true;
    operator.reporterId.readOnly = true;
    operator.deviceId.readOnly = true;
    operator.usernameInput.value = session.username || activeUsername();
    operator.reporterId.value = session.reporter_id || reporterId();
    operator.deviceId.value = session.device_id || deviceId();
    operator.sessionSummary.className = "list";
    operator.sessionSummary.innerHTML = `
      <article class="item advisory">
        <strong>${escapeHTML(session.display_name || session.username)}</strong>
        <span>${escapeHTML(role)} · package ${escapeHTML(session.package || PACKAGE_NAME)} · session ${escapeHTML(session.id || "unknown")}</span>
        <span>license ${entitlements.license_active ? "active" : "inactive"} · reporter ${escapeHTML(session.reporter_id || "operator-alpha")} · device ${escapeHTML(session.device_id || "operator-mini-001")}</span>
      </article>
    `;
    return;
  }

  operator.roleSelect.disabled = false;
  operator.usernameInput.readOnly = false;
  operator.reporterId.readOnly = false;
  operator.deviceId.readOnly = false;
  syncSuggestedUsername(true);
  operator.sessionSummary.className = "list empty";
  operator.sessionSummary.textContent = entitlements.license_active
    ? `No active session. ${entitlements.label || "Operator package"} is running in local header mode.`
    : `${entitlements.label || "Operator package"} license is inactive.`;
}

function renderList(container, records, emptyText, renderer) {
  if (!records || records.length === 0) {
    container.className = "list empty";
    container.textContent = emptyText;
    return;
  }
  container.className = "list operator-list";
  container.innerHTML = records.map(renderer).join("");
}

function queueItems() {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveQueue(items) {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(items));
  document.querySelector("#queue-count").textContent = items.length;
  operator.syncState.value = items.length ? "Queued" : "Live";
}

function loadReceipt() {
  try {
    return JSON.parse(localStorage.getItem(RECEIPT_KEY) || "null");
  } catch {
    return null;
  }
}

function saveReceipt(receipt) {
  lastReceipt = receipt;
  localStorage.setItem(RECEIPT_KEY, JSON.stringify(receipt));
}

function quickActions() {
  return (workspaceState && workspaceState.quick_actions) || [
    { id: "position", label: "Position", report_type: "position_update", template: "Position update from {reporter_id} near {location}." },
    { id: "hazard", label: "Hazard", report_type: "hazard", template: "Hazard observed near {location}. Human review recommended." },
    { id: "contact", label: "Contact", report_type: "observation", template: "Possible contact or threat activity observed near {location}. Confidence limited pending review." },
    { id: "delay", label: "Delay", report_type: "status_update", template: "Movement delay reported near {location}." },
    { id: "comms", label: "Comms", report_type: "communications_check", template: "Communications issue reported near {location}." },
    { id: "medevac", label: "Medevac", report_type: "medical", template: "Medical event or medevac support may be required near {location}." },
    { id: "logistics", label: "Logistics", report_type: "logistics", template: "Logistics support issue reported near {location}." },
    { id: "unknown", label: "Unknown", report_type: "unknown_requires_review", template: "Unknown field report requiring human review near {location}." },
  ];
}

function activeAction() {
  return quickActions().find((action) => action.id === selectedActionId) || quickActions()[0];
}

function currentLocation() {
  return operator.reportForm.elements.location.value.trim()
    || (workspaceState && workspaceState.local_cop && workspaceState.local_cop.focus_label)
    || "Local operator area";
}

function actionSummaryTemplate(action, location) {
  return (action.template || "")
    .replaceAll("{reporter_id}", reporterId())
    .replaceAll("{location}", location || "Local operator area");
}

function updateDrawerButton() {
  operator.drawerToggle.textContent = operator.drawer.open ? "Close Action Menu" : "Open Action Menu";
}

function setSelectedAction(actionId, preserveSummary = false) {
  selectedActionId = actionId;
  const action = activeAction();
  operator.reportForm.elements.report_type.value = action.report_type;
  operator.selectedActionLabel.textContent = action.label;
  if (!preserveSummary) {
    operator.reportForm.elements.summary.value = actionSummaryTemplate(action, currentLocation());
  }
  renderActionGrid();
}

function renderActionGrid() {
  operator.actionGrid.innerHTML = quickActions().map((action) => `
    <button
      type="button"
      class="${action.id === selectedActionId ? "is-selected" : ""}"
      data-action-id="${escapeHTML(action.id)}"
    >${escapeHTML(action.label)}</button>
  `).join("");
}

function renderSelection(marker) {
  if (!marker) {
    operator.selectionCard.className = "list empty";
    operator.selectionCard.textContent = "Tap a local point to start a report.";
    return;
  }
  operator.selectionCard.className = "list operator-selection";
  operator.selectionCard.innerHTML = `
    <article class="item ${escapeHTML(marker.kind)}">
      <strong>${escapeHTML(marker.label)}</strong>
      <span class="item-caption">Current local focus for the next field update</span>
      <span>${escapeHTML(marker.summary)}</span>
      ${pairGrid([
        ["Type", marker.kind],
        ["Status", marker.status],
        ["Confidence", marker.confidence],
      ])}
    </article>
  `;
}

function renderMap(localCop) {
  operator.operatorMap.querySelectorAll(".operator-marker").forEach((marker) => marker.remove());
  const markers = (localCop && localCop.markers) || [];
  markers.forEach((marker) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `operator-marker ${marker.kind}${marker.id === selectedMarkerId ? " selected" : ""}`;
    button.style.left = `${marker.left_percent}%`;
    button.style.top = `${marker.top_percent}%`;
    button.title = `${marker.label}: ${marker.summary}`;
    button.dataset.markerId = marker.id;
    operator.operatorMap.appendChild(button);
  });
  const marker = markers.find((item) => item.id === selectedMarkerId) || markers[0] || null;
  if (marker) {
    selectedMarkerId = marker.id;
    renderSelection(marker);
  } else {
    renderSelection(null);
  }
}

function renderReceipt() {
  if (!lastReceipt) {
    operator.receiptCard.className = "list empty";
    operator.receiptCard.textContent = "No submission receipt yet";
    return;
  }
  operator.receiptCard.className = "list";
  operator.receiptCard.innerHTML = `
    <article class="item advisory">
      <strong>${escapeHTML(lastReceipt.status || "queued_for_human_review")}</strong>
      <span class="item-caption">Latest operator submission result</span>
      <span>${escapeHTML(lastReceipt.advisory_summary || lastReceipt.summary || "Receipt recorded.")}</span>
      ${pairGrid([
        ["Report", lastReceipt.report_id || lastReceipt.local_id || "pending"],
        ["Time", lastReceipt.acknowledged_at || lastReceipt.queued_at || ""],
      ])}
    </article>
  `;
}

function renderAdvisories(advisories) {
  document.querySelector("#advisory-count").textContent = advisories.length;
  renderList(operator.advisoryList, advisories.slice(-6).reverse(), "No advisories", (advisory) => `
    <article class="item advisory">
      <strong>${escapeHTML(advisory.summary)}</strong>
      <span class="item-caption">Local advisory returned for operator awareness</span>
      ${pairGrid([
        ["Confidence", advisory.confidence],
        ["Time", formatTime(advisory.timestamp)],
      ])}
    </article>
  `);
}

function renderReports(reports) {
  document.querySelector("#report-count").textContent = reports.length;
  renderList(operator.reportList, reports.slice(-6).reverse(), "No reports yet", (report) => `
    <article class="item">
      <strong>${escapeHTML(report.report_type)}</strong>
      <span class="item-caption">Field report status: ${escapeHTML(report.review_state || "new")}</span>
      <span>${escapeHTML(report.summary)}</span>
      ${pairGrid([
        ["Review state", report.review_state || "new"],
        ["Location", report.location || "unknown location"],
        ["Time", formatTime(report.timestamp)],
      ])}
    </article>
  `);
}

function renderBrain(messages) {
  document.querySelector("#brain-count").textContent = messages.length;
  renderList(operator.brainList, messages.slice(-5).reverse(), "No operator BRAIN thread yet", (message) => `
    <article class="item brain-chat">
      <strong>${escapeHTML(message.answer.confidence_band)} confidence</strong>
      <span class="item-caption">BRAIN reachback for field use</span>
      <span>Q: ${escapeHTML(message.question.text)}</span>
      <span>${escapeHTML(message.answer.answer_text)}</span>
      ${pairGrid([
        ["Reachback", message.answer.core_reachback_used ? "Used" : "Not used"],
        ["References", (message.answer.references || []).join(", ") || "none"],
      ])}
    </article>
  `);
}

function renderWorkspace(workspace) {
  workspaceState = workspace;
  const localCop = workspace.local_cop || { markers: [] };
  document.querySelector("#focus-label").textContent = localCop.focus_label || "Local operator area";
  document.querySelector("#workspace-status").textContent = workspace.status || "ready";
  document.querySelector("#mission-label").textContent = (workspace.mission && workspace.mission.mission_statement) || "No mission context";
  renderMap(localCop);
  renderAdvisories(workspace.advisory_inbox || []);
  renderReports(workspace.recent_reports || []);
  renderActionGrid();
  if (!operator.reportForm.elements.location.value || operator.reportForm.elements.location.value === "Local operator area") {
    operator.reportForm.elements.location.value = localCop.focus_label || "Local operator area";
  }
  setSelectedAction(selectedActionId, true);
}

async function refresh() {
  try {
    const [health, entitlements, sessionDoc, workspaceDoc, brainDoc] = await Promise.all([
      getJSON("/api/health"),
      getJSON("/api/entitlements"),
      getJSON("/api/auth/session"),
      getJSON("/api/operator/workspace"),
      getJSON("/api/operator/brain-thread"),
    ]);
    renderSession(sessionDoc, entitlements);
    setStatus(true, `${health.service} link live`);
    renderWorkspace(workspaceDoc.operator_workspace || {});
    renderBrain(brainDoc.messages || []);
    saveQueue(queueItems());
    renderReceipt();
  } catch (error) {
    setStatus(false, error.message || "Queued / offline");
    saveQueue(queueItems());
    renderReceipt();
  }
}

async function connectSession() {
  const response = await postJSON("/api/auth/login", {
    username: activeUsername(),
    package: PACKAGE_NAME,
    reporter_id: reporterId(),
    device_id: deviceId(),
  });
  localStorage.setItem(SESSION_KEY, response.session.id);
}

async function clearSession() {
  if (activeSessionToken()) {
    try {
      await postJSON("/api/auth/logout", {});
    } catch {
      // Best-effort sign-out for the local synthetic session.
    }
  }
  localStorage.removeItem(SESSION_KEY);
}

async function queueReport(payload) {
  const queued = queueItems();
  const entry = {
    local_id: `queued-${Date.now()}`,
    queued_at: new Date().toISOString(),
    summary: payload.summary,
    ...payload,
  };
  queued.push(entry);
  saveQueue(queued);
  saveReceipt({
    local_id: entry.local_id,
    queued_at: entry.queued_at,
    status: "queued_local_sync_pending",
    advisory_summary: "Report queued locally. Sync when the link is available.",
    summary: entry.summary,
  });
  renderReceipt();
}

async function syncQueuedReports() {
  const queued = queueItems();
  if (!queued.length) {
    operator.syncState.value = "Live";
    return;
  }
  const remaining = [];
  for (const entry of queued) {
    try {
      const response = await postJSON("/api/operator/report", {
        report_type: entry.report_type,
        location: entry.location,
        summary: entry.summary,
      });
      saveReceipt(response);
    } catch {
      remaining.push(entry);
    }
  }
  saveQueue(remaining);
  renderReceipt();
}

operator.drawerToggle.addEventListener("click", () => {
  operator.drawer.open = !operator.drawer.open;
  updateDrawerButton();
});

operator.drawer.addEventListener("toggle", updateDrawerButton);

operator.actionGrid.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action-id]");
  if (!button) return;
  setSelectedAction(button.dataset.actionId);
});

operator.operatorMap.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-marker-id]");
  if (!button || !workspaceState || !workspaceState.local_cop) return;
  selectedMarkerId = button.dataset.markerId;
  const marker = (workspaceState.local_cop.markers || []).find((item) => item.id === selectedMarkerId);
  renderMap(workspaceState.local_cop);
  renderSelection(marker);
  operator.reportForm.elements.location.value = workspaceState.local_cop.focus_label || currentLocation();
  operator.drawer.open = true;
  updateDrawerButton();
  operator.reportForm.elements.summary.value = actionSummaryTemplate(activeAction(), currentLocation());
});

operator.reportForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    report_type: operator.reportForm.elements.report_type.value,
    location: operator.reportForm.elements.location.value,
    summary: operator.reportForm.elements.summary.value,
  };
  try {
    const response = await postJSON("/api/operator/report", payload);
    saveReceipt(response);
    renderReceipt();
    await syncQueuedReports();
    await refresh();
  } catch {
    await queueReport(payload);
  }
});

operator.syncQueueButton.addEventListener("click", async () => {
  await syncQueuedReports();
  await refresh();
});

operator.brainChatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(operator.brainChatForm).entries());
  payload.user_id = reporterId();
  payload.role = activeRole();
  await postJSON("/api/brain/chat", payload);
  await refresh();
});

operator.sessionButton.addEventListener("click", async () => {
  try {
    await connectSession();
    await refresh();
  } catch (error) {
    setStatus(false, error.message || "Session denied");
  }
});

operator.clearSessionButton.addEventListener("click", async () => {
  await clearSession();
  syncSuggestedUsername(true);
  await refresh();
});

operator.refreshButton.addEventListener("click", refresh);
operator.reporterId.addEventListener("change", refresh);
operator.deviceId.addEventListener("change", refresh);
operator.roleSelect.addEventListener("change", async () => {
  syncSuggestedUsername(true);
  await refresh();
});

saveQueue(queueItems());
syncSuggestedUsername(true);
updateDrawerButton();
renderReceipt();
refresh();
