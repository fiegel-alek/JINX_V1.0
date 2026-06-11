const els = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
  copName: document.querySelector("#cop-name"),
  copMap: document.querySelector("#cop-map"),
  trackList: document.querySelector("#track-list"),
  trackCount: document.querySelector("#track-count"),
  reportList: document.querySelector("#report-list"),
  advisoryList: document.querySelector("#advisory-list"),
  eventList: document.querySelector("#event-list"),
  moduleList: document.querySelector("#module-list"),
  activityList: document.querySelector("#activity-list"),
  reportForm: document.querySelector("#report-form"),
  commandForm: document.querySelector("#command-form"),
  refreshButton: document.querySelector("#refresh-button"),
  demoButton: document.querySelector("#demo-button"),
  roleSelect: document.querySelector("#role-select"),
  metrics: {
    tracks: document.querySelector("#metric-tracks"),
    reports: document.querySelector("#metric-reports"),
    reviewQueue: document.querySelector("#metric-review-queue"),
    advisories: document.querySelector("#metric-advisories"),
    events: document.querySelector("#metric-events"),
  },
};

function setStatus(ok, text) {
  els.apiStatus.classList.toggle("ok", ok);
  els.apiStatus.classList.toggle("error", !ok);
  els.apiStatusText.textContent = text;
}

function activeRole() {
  return els.roleSelect.value;
}

function requestHeaders(extra = {}) {
  return { "X-JINX-Role": activeRole(), ...extra };
}

async function getJSON(url) {
  const response = await fetch(url, { headers: requestHeaders() });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
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

function renderList(container, records, emptyText, renderer) {
  if (!records || records.length === 0) {
    container.className = "list empty";
    container.textContent = emptyText;
    return;
  }
  container.className = "list";
  container.innerHTML = records.map(renderer).join("");
}

function renderTracks(cop) {
  els.copMap.querySelectorAll(".track-marker").forEach((marker) => marker.remove());
  els.copName.textContent = cop.name || "empty";
  const tracks = cop.tracks || [];
  els.metrics.tracks.textContent = tracks.length;
  els.trackCount.textContent = `${tracks.length} active`;

  renderList(els.trackList, tracks, "No tracks loaded", (track) => `
    <article class="item">
      <strong>${escapeHTML(track.label)}</strong>
      <span>${escapeHTML(track.location)} · ${escapeHTML(track.status)} · confidence ${escapeHTML(track.confidence)}</span>
      <span>${escapeHTML(track.report_count)} reports · ${escapeHTML(track.advisory_count)} advisories · updated ${formatTime(track.updated_at)}</span>
    </article>
  `);

  tracks.forEach((track, index) => {
    const marker = document.createElement("div");
    marker.className = "track-marker";
    marker.dataset.label = track.label;
    marker.style.left = `${22 + (index * 19) % 58}%`;
    marker.style.top = `${28 + (index * 29) % 48}%`;
    els.copMap.appendChild(marker);
  });
}

function renderReports(reports) {
  els.metrics.reports.textContent = reports.length;
  els.metrics.reviewQueue.textContent = reports.filter((report) => !["validated", "closed"].includes(report.review_state)).length;
  document.querySelector("#report-count").textContent = reports.length;
  renderList(els.reportList, reports, "No reports", (report) => `
    <article class="item">
      <strong>${escapeHTML(report.reporter_id)} · ${escapeHTML(report.report_type)}</strong>
      <span>${escapeHTML(report.location || "no location")} · confidence ${escapeHTML(report.confidence)} · ${escapeHTML(report.summary)}</span>
      <div class="review-row">
        <span class="badge review-${escapeHTML(report.review_state || "new")}">${reviewLabel(report.review_state)}</span>
        <button type="button" data-review="${escapeHTML(report.id)}" data-state="under_review">Review</button>
        <button type="button" data-review="${escapeHTML(report.id)}" data-state="validated">Validate</button>
        <button type="button" data-review="${escapeHTML(report.id)}" data-state="needs_more_info">Need info</button>
        <button type="button" data-review="${escapeHTML(report.id)}" data-state="closed">Close</button>
      </div>
    </article>
  `);
}

function formatTime(value) {
  if (!value) return "unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "unknown";
  return date.toLocaleTimeString();
}

function reviewLabel(state = "new") {
  const labels = {
    new: "New",
    under_review: "Under review",
    validated: "Validated",
    needs_more_info: "Needs info",
    closed: "Closed",
  };
  return labels[state] || state;
}

async function updateReportReview(reportId, state) {
  const reviewer = activeRole() === "commander" ? "commander-alpha" : "c5isr-manager-alpha";
  const note = `Set to ${reviewLabel(state)} from COP manager.`;
  const response = await postJSON("/api/operator-reports/review", {
    report_id: reportId,
    state,
    reviewer_id: reviewer,
    note,
  });
  addActivity(`Report ${response.report.id} marked ${reviewLabel(response.report.review_state)}.`);
  await refreshDashboard();
}

function renderAdvisories(advisories) {
  els.metrics.advisories.textContent = advisories.length;
  document.querySelector("#advisory-count").textContent = advisories.length;
  renderList(els.advisoryList, advisories, "No advisories", (advisory) => `
    <article class="item advisory">
      <strong>${escapeHTML(advisory.recipient_id)}</strong>
      <span>${escapeHTML(advisory.summary)} · confidence ${escapeHTML(advisory.confidence)}</span>
    </article>
  `);
}

function renderEvents(events) {
  els.metrics.events.textContent = events.length;
  document.querySelector("#event-count").textContent = events.length;
  renderList(els.eventList, events, "No events", (event) => `
    <article class="item">
      <strong>${escapeHTML(event.event_type)}</strong>
      <span>${escapeHTML(event.location || "no location")} · ${escapeHTML(event.description)}</span>
    </article>
  `);
}

function renderModules(modules) {
  els.moduleList.innerHTML = modules.map((module) => `
    <article class="module-card">
      <strong>${escapeHTML(module.name)}</strong>
      <span class="badge ${module.status === "online" ? "online" : "stubbed"}">${escapeHTML(module.status)}</span>
      <p>${escapeHTML(module.role)}</p>
    </article>
  `).join("");
}

function addActivity(text) {
  if (els.activityList.classList.contains("empty")) {
    els.activityList.className = "list";
    els.activityList.innerHTML = "";
  }
  const item = document.createElement("div");
  item.className = "item";
  item.innerHTML = `<strong>${new Date().toLocaleTimeString()}</strong><span>${escapeHTML(text)}</span>`;
  els.activityList.prepend(item);
}

async function refreshDashboard() {
  try {
    const [health, cop, reports, advisories, events, modules] = await Promise.all([
      getJSON("/api/health"),
      getJSON("/api/cop"),
      getJSON("/api/operator-reports"),
      getJSON("/api/advisories"),
      getJSON("/api/events"),
      getJSON("/api/modules"),
    ]);
    setStatus(true, `${health.service} API online`);
    renderTracks(cop);
    renderReports(reports.operator_reports || []);
    renderAdvisories(advisories.advisories || []);
    renderEvents(events.events || []);
    renderModules(modules.modules || []);
  } catch (error) {
    setStatus(false, "API offline");
    addActivity(error.message);
  }
}

els.reportForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.reportForm).entries());
  try {
    const response = await postJSON("/api/operator-reports", data);
    addActivity(`Report ${response.report_id} delivered; advisory ${response.advisory_id} generated.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

els.commandForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.commandForm).entries());
  try {
    const response = await postJSON("/api/human-commands", data);
    addActivity(`Human input ${response.command_id} delivered: ${response.delivered}`);
  } catch (error) {
    addActivity(error.message);
  }
});

els.reportList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-review]");
  if (!button) return;
  try {
    await updateReportReview(button.dataset.review, button.dataset.state);
  } catch (error) {
    addActivity(error.message);
  }
});

els.refreshButton.addEventListener("click", refreshDashboard);
els.roleSelect.addEventListener("change", async () => {
  addActivity(`Active role changed to ${activeRole()}.`);
  await refreshDashboard();
});
els.demoButton.addEventListener("click", async () => {
  try {
    const response = await postJSON("/api/sim/demo");
    addActivity(`Injected ${response.injected} synthetic reports.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

refreshDashboard();
