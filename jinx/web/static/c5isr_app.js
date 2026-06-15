const c5 = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
  roleSelect: document.querySelector("#role-select"),
  usernameInput: document.querySelector("#username-input"),
  sessionButton: document.querySelector("#session-button"),
  clearSessionButton: document.querySelector("#clear-session-button"),
  sessionSummary: document.querySelector("#session-summary"),
  sessionMode: document.querySelector("#session-mode"),
  copName: document.querySelector("#cop-name"),
  copMap: document.querySelector("#cop-map"),
  trackList: document.querySelector("#track-list"),
  reportList: document.querySelector("#report-list"),
  reviewCenterList: document.querySelector("#review-center-list"),
  missionImpactList: document.querySelector("#mission-impact-list"),
  advisoryList: document.querySelector("#advisory-list"),
  conflictList: document.querySelector("#conflict-list"),
  recommendationList: document.querySelector("#recommendation-list"),
  brainChatList: document.querySelector("#brain-chat-list"),
  timelineList: document.querySelector("#timeline-list"),
  missionContext: document.querySelector("#mission-context"),
  reportForm: document.querySelector("#report-form"),
  brainChatForm: document.querySelector("#brain-chat-form"),
  refreshButton: document.querySelector("#refresh-button"),
  missionButton: document.querySelector("#mission-button"),
};

const SESSION_KEY = "jinx-c5isr-session-token";
const PACKAGE_NAME = "c5isr";
const USERNAME_BY_ROLE = {
  c5isr_manager: "c5isr-manager-alpha",
  operator: "operator-alpha",
  commander: "systemadministrator",
  auditor: "auditor-alpha",
};

function activeRole() {
  return c5.roleSelect.value;
}

function activeSessionToken() {
  return localStorage.getItem(SESSION_KEY) || "";
}

function suggestedUsername() {
  return USERNAME_BY_ROLE[activeRole()] || "c5isr-manager-alpha";
}

function syncSuggestedUsername(force = false) {
  if (c5.usernameInput.readOnly) return;
  const current = c5.usernameInput.value.trim();
  if (force || !current || Object.values(USERNAME_BY_ROLE).includes(current)) {
    c5.usernameInput.value = suggestedUsername();
  }
}

function activeUsername() {
  return c5.usernameInput.value.trim() || suggestedUsername();
}

function headers(extra = {}) {
  const sessionToken = activeSessionToken();
  return sessionToken
    ? { "X-JINX-Role": activeRole(), "X-JINX-Package": PACKAGE_NAME, "X-JINX-Session": sessionToken, ...extra }
    : { "X-JINX-Role": activeRole(), "X-JINX-Package": PACKAGE_NAME, ...extra };
}

async function getJSON(url) {
  const response = await fetch(url, { headers: headers() });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `${response.status} ${response.statusText}`);
  return body;
}

async function postJSON(url, payload = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
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

function renderList(container, records, emptyText, renderer) {
  if (!records || records.length === 0) {
    container.className = "list empty";
    container.textContent = emptyText;
    return;
  }
  container.className = "list";
  container.innerHTML = records.map(renderer).join("");
}

function setStatus(ok, text) {
  c5.apiStatus.classList.toggle("ok", ok);
  c5.apiStatus.classList.toggle("error", !ok);
  c5.apiStatusText.textContent = text;
}

function renderSession(sessionDoc, entitlements) {
  const session = sessionDoc.session || null;
  if (!session && activeSessionToken()) {
    localStorage.removeItem(SESSION_KEY);
  }
  document.querySelector(".eyebrow").textContent = entitlements.label || "C5ISR package";
  c5.sessionMode.textContent = session ? "Session active" : "Header role mode";
  c5.roleSelect.disabled = Boolean(session);
  c5.usernameInput.readOnly = Boolean(session);

  if (session) {
    const role = String((session.roles || [])[0] || activeRole());
    if (c5.roleSelect.querySelector(`option[value="${role}"]`)) {
      c5.roleSelect.value = role;
    }
    c5.usernameInput.value = session.username || activeUsername();
    c5.brainChatForm.elements.user_id.value = session.username || activeUsername();
    c5.sessionSummary.className = "list";
    c5.sessionSummary.innerHTML = `
      <article class="item advisory">
        <strong>${escapeHTML(session.display_name || session.username)}</strong>
        <span>${escapeHTML(role)} · package ${escapeHTML(session.package || PACKAGE_NAME)} · session ${escapeHTML(session.id || "unknown")}</span>
        <span>license ${entitlements.license_active ? "active" : "inactive"} · ${entitlements.simulation_only ? "simulation only" : "controlled adapter enabled"}</span>
      </article>
    `;
    return;
  }

  syncSuggestedUsername(true);
  c5.brainChatForm.elements.user_id.value = activeUsername();
  c5.sessionSummary.className = "list empty";
  c5.sessionSummary.textContent = entitlements.license_active
    ? `No active session. ${entitlements.label || "C5ISR package"} is running in local header mode.`
    : `${entitlements.label || "C5ISR package"} license is inactive.`;
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

function formatTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "unknown" : date.toLocaleTimeString();
}

function renderTracks(cop) {
  c5.copMap.querySelectorAll(".track-marker").forEach((marker) => marker.remove());
  c5.copName.textContent = cop.name || "empty";
  const tracks = cop.tracks || [];
  document.querySelector("#metric-tracks").textContent = tracks.length;
  document.querySelector("#track-count").textContent = `${tracks.length} active`;
  renderList(c5.trackList, tracks, "No tracks loaded", (track) => `
    <article class="item">
      <strong>${escapeHTML(track.label)}</strong>
      ${pairGrid([
        ["Location", track.location],
        ["State", track.lifecycle || track.status],
        ["Confidence", track.confidence],
        ["Validation", track.human_validated ? "Human validated" : "Pending"],
        ["Updated", formatTime(track.updated_at)],
      ])}
    </article>
  `);
  tracks.forEach((track, index) => {
    const marker = document.createElement("div");
    marker.className = "track-marker";
    marker.dataset.label = track.label;
    marker.style.left = `${22 + (index * 19) % 58}%`;
    marker.style.top = `${28 + (index * 29) % 48}%`;
    c5.copMap.appendChild(marker);
  });
}

function renderMission(mission) {
  document.querySelector("#mission-id").textContent = mission.id || "not loaded";
  if (!mission.id) {
    c5.missionContext.className = "list empty";
    c5.missionContext.textContent = "No mission context loaded";
    return;
  }
  c5.missionContext.className = "list";
  c5.missionContext.innerHTML = `
    <article class="item">
      <strong>${escapeHTML(mission.mission_statement)}</strong>
      <span>${escapeHTML(mission.commander_intent)}</span>
      ${pairGrid([
        ["Routes", (mission.routes || []).join(", ") || "none"],
        ["Areas", (mission.named_areas || []).join(", ") || "none"],
      ])}
    </article>
  `;
}

function renderReports(reports) {
  document.querySelector("#metric-reports").textContent = reports.length;
  document.querySelector("#report-count").textContent = reports.length;
  document.querySelector("#metric-review-queue").textContent = reports.filter(
    (report) => !["validated", "closed"].includes(report.review_state)
  ).length;
  renderList(c5.reportList, reports.slice(-10).reverse(), "No reports", (report) => `
    <article class="item">
      <strong>${escapeHTML(report.reporter_id)} · ${escapeHTML(report.report_type)}</strong>
      <span>${escapeHTML(report.summary)}</span>
      ${pairGrid([
        ["Location", report.location || "no location"],
        ["Confidence", report.confidence],
        ["Review state", report.review_state || "new"],
      ])}
      <div class="review-row">
        <span class="badge review-${escapeHTML(report.review_state || "new")}">${reviewLabel(report.review_state)}</span>
      </div>
    </article>
  `);
}

function renderReview(items) {
  document.querySelector("#review-center-count").textContent = items.length;
  renderList(c5.reviewCenterList, items, "No review items", (item) => `
    <article class="item review-item">
      <strong>${escapeHTML(item.kind)} · ${escapeHTML(item.review_state)}</strong>
      <span>${escapeHTML(item.summary)}</span>
      ${pairGrid([
        ["Severity", item.severity],
        ["Assigned", item.assigned_reviewer],
        ["Escalation", item.escalation_state],
      ])}
    </article>
  `);
}

function renderMissionImpacts(impacts) {
  document.querySelector("#mission-impact-count").textContent = impacts.length;
  renderList(c5.missionImpactList, impacts, "No mission impacts", (impact) => `
    <article class="item mission-impact">
      <strong>${escapeHTML(impact.impacted_area)}</strong>
      <span>${escapeHTML(impact.summary)}</span>
      ${pairGrid([
        ["Confidence", impact.confidence],
        ["Review", impact.recommended_review_role],
      ])}
    </article>
  `);
}

function renderAdvisories(advisories) {
  document.querySelector("#metric-advisories").textContent = advisories.length;
  document.querySelector("#advisory-count").textContent = advisories.length;
  renderList(c5.advisoryList, advisories.slice(-10).reverse(), "No advisories", (advisory) => `
    <article class="item advisory">
      <strong>${escapeHTML(advisory.recipient_id)}</strong>
      <span>${escapeHTML(advisory.summary)}</span>
      ${pairGrid([["Confidence", advisory.confidence]])}
    </article>
  `);
}

function renderConflicts(conflicts) {
  document.querySelector("#conflict-count").textContent = conflicts.length;
  renderList(c5.conflictList, conflicts.slice(-8).reverse(), "No conflicts", (conflict) => `
    <article class="item conflict">
      <strong>${escapeHTML(conflict.conflict_type)}</strong>
      <span>${escapeHTML(conflict.explanation)}</span>
      ${pairGrid([
        ["Confidence", conflict.confidence],
        ["Review", conflict.recommended_review_role],
      ])}
    </article>
  `);
}

function renderRecommendations(recommendations) {
  document.querySelector("#recommendation-count").textContent = recommendations.length;
  renderList(c5.recommendationList, recommendations.slice(-8).reverse(), "No recommendations", (recommendation) => `
    <article class="item recommendation">
      <strong>${escapeHTML(recommendation.recommendation_type)}</strong>
      <span>${escapeHTML(recommendation.text)}</span>
      ${pairGrid([
        ["Confidence", recommendation.confidence],
        ["Human review", recommendation.required_human_review ? "Required" : "No"],
      ])}
    </article>
  `);
}

function renderBrain(messages) {
  document.querySelector("#brain-chat-count").textContent = messages.length;
  renderList(c5.brainChatList, messages.slice(-5).reverse(), "No Brain chat yet", (message) => `
    <article class="item brain-chat">
      <strong>${escapeHTML(message.answer.confidence_band)} confidence</strong>
      <span>Q: ${escapeHTML(message.question.text)}</span>
      <span>${escapeHTML(message.answer.answer_text)}</span>
      ${pairGrid([
        ["Reachback", message.answer.core_reachback_used ? "Used" : "Not used"],
        ["References", (message.answer.references || []).join(", ") || "none"],
      ])}
    </article>
  `);
}

function renderTimeline(timeline) {
  renderList(c5.timelineList, timeline.slice(-8).reverse(), "No timeline entries", (entry) => `
    <article class="item timeline">
      <strong>${escapeHTML(entry.kind)} · ${formatTime(entry.timestamp)}</strong>
      <span>${escapeHTML(entry.summary)}</span>
    </article>
  `);
}

async function refresh() {
  try {
    const [
      health,
      entitlements,
      sessionDoc,
      cop,
      mission,
      reports,
      review,
      impacts,
      advisories,
      conflicts,
      recommendations,
      brain,
      timeline,
    ] = await Promise.all([
      getJSON("/api/health"),
      getJSON("/api/entitlements"),
      getJSON("/api/auth/session"),
      getJSON("/api/cop"),
      getJSON("/api/mission-context"),
      getJSON("/api/operator-reports"),
      getJSON("/api/review-center"),
      getJSON("/api/mission-impacts"),
      getJSON("/api/advisories"),
      getJSON("/api/conflicts"),
      getJSON("/api/recommendations"),
      getJSON("/api/brain/chat-messages"),
      getJSON("/api/timeline"),
    ]);
    renderSession(sessionDoc, entitlements);
    setStatus(true, `${health.service} API online`);
    renderTracks(cop);
    renderMission(mission.mission);
    renderReports(reports.operator_reports || []);
    renderReview(review.items || []);
    renderMissionImpacts(impacts.mission_impacts || []);
    renderAdvisories(advisories.advisories || []);
    renderConflicts(conflicts.conflicts || []);
    renderRecommendations(recommendations.recommendations || []);
    renderBrain(brain.messages || []);
    renderTimeline(timeline.timeline || []);
  } catch (error) {
    setStatus(false, error.message || "API offline");
  }
}

async function connectSession() {
  const response = await postJSON("/api/auth/login", {
    username: activeUsername(),
    package: PACKAGE_NAME,
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

c5.reportForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await postJSON("/api/operator-reports", Object.fromEntries(new FormData(c5.reportForm).entries()));
  await refresh();
});

c5.brainChatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(c5.brainChatForm).entries());
  data.role = activeRole();
  await postJSON("/api/brain/chat", data);
  await refresh();
});

c5.missionButton.addEventListener("click", async () => {
  await postJSON("/api/mission-context", {
    mission_statement: "Synthetic C5ISR mission monitors Route Alpha and Area Alpha.",
    commander_intent: "Maintain coherent COP confidence and surface mission impacts for review.",
    route: "Route Alpha",
    named_area: "Area Alpha",
  });
  await refresh();
});

c5.sessionButton.addEventListener("click", async () => {
  try {
    await connectSession();
    await refresh();
  } catch (error) {
    setStatus(false, error.message || "Session denied");
  }
});

c5.clearSessionButton.addEventListener("click", async () => {
  await clearSession();
  syncSuggestedUsername(true);
  await refresh();
});

c5.refreshButton.addEventListener("click", refresh);
c5.roleSelect.addEventListener("change", async () => {
  syncSuggestedUsername(true);
  await refresh();
});

syncSuggestedUsername(true);
refresh();
