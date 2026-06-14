const operator = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
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

let workspaceState = null;
let selectedMarkerId = "";
let selectedActionId = "position";
let lastReceipt = loadReceipt();

function activeRole() {
  return operator.roleSelect.value;
}

function reporterId() {
  return operator.reporterId.value.trim() || "operator-alpha";
}

function deviceId() {
  return operator.deviceId.value.trim() || "operator-mini-001";
}

function requestHeaders(extra = {}) {
  return {
    "X-JINX-Role": activeRole(),
    "X-JINX-Package": "operator",
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

function formatTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "unknown" : date.toLocaleTimeString();
}

function setStatus(ok, text) {
  operator.apiStatus.classList.toggle("ok", ok);
  operator.apiStatus.classList.toggle("error", !ok);
  operator.apiStatusText.textContent = text;
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
    operator.selectionCard.textContent = "Select a map point to prep a report.";
    return;
  }
  operator.selectionCard.className = "list operator-selection";
  operator.selectionCard.innerHTML = `
    <article class="item ${escapeHTML(marker.kind)}">
      <strong>${escapeHTML(marker.label)} · ${escapeHTML(marker.kind)}</strong>
      <span>${escapeHTML(marker.summary)}</span>
      <span>status ${escapeHTML(marker.status)} · confidence ${escapeHTML(marker.confidence)}</span>
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
      <span>${escapeHTML(lastReceipt.advisory_summary || lastReceipt.summary || "Receipt recorded.")}</span>
      <span>${escapeHTML(lastReceipt.report_id || lastReceipt.local_id || "pending")} · ${escapeHTML(lastReceipt.acknowledged_at || lastReceipt.queued_at || "")}</span>
    </article>
  `;
}

function renderAdvisories(advisories) {
  document.querySelector("#advisory-count").textContent = advisories.length;
  renderList(operator.advisoryList, advisories.slice(-6).reverse(), "No advisories", (advisory) => `
    <article class="item advisory">
      <strong>${escapeHTML(advisory.summary)}</strong>
      <span>confidence ${escapeHTML(advisory.confidence)} · ${formatTime(advisory.timestamp)}</span>
    </article>
  `);
}

function renderReports(reports) {
  document.querySelector("#report-count").textContent = reports.length;
  renderList(operator.reportList, reports.slice(-6).reverse(), "No reports yet", (report) => `
    <article class="item">
      <strong>${escapeHTML(report.report_type)} · ${escapeHTML(report.review_state || "new")}</strong>
      <span>${escapeHTML(report.summary)}</span>
      <span>${escapeHTML(report.location || "unknown location")} · ${formatTime(report.timestamp)}</span>
    </article>
  `);
}

function renderBrain(messages) {
  document.querySelector("#brain-count").textContent = messages.length;
  renderList(operator.brainList, messages.slice(-5).reverse(), "No operator BRAIN thread yet", (message) => `
    <article class="item brain-chat">
      <strong>${escapeHTML(message.answer.confidence_band)} · reachback ${message.answer.core_reachback_used ? "used" : "not used"}</strong>
      <span>Q: ${escapeHTML(message.question.text)}</span>
      <span>${escapeHTML(message.answer.answer_text)}</span>
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
    const [health, workspaceDoc, brainDoc] = await Promise.all([
      getJSON("/api/health"),
      getJSON("/api/operator/workspace"),
      getJSON("/api/operator/brain-thread"),
    ]);
    setStatus(true, `${health.service} link live`);
    renderWorkspace(workspaceDoc.operator_workspace || {});
    renderBrain(brainDoc.messages || []);
    saveQueue(queueItems());
    renderReceipt();
  } catch (error) {
    setStatus(false, "Queued / offline");
    saveQueue(queueItems());
    renderReceipt();
  }
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
    } catch (error) {
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
  } catch (error) {
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

operator.refreshButton.addEventListener("click", refresh);
operator.reporterId.addEventListener("change", refresh);
operator.deviceId.addEventListener("change", refresh);
operator.roleSelect.addEventListener("change", refresh);

saveQueue(queueItems());
updateDrawerButton();
renderReceipt();
refresh();
