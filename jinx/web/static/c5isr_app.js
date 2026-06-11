const c5 = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
  roleSelect: document.querySelector("#role-select"),
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

function activeRole() {
  return c5.roleSelect.value;
}

function headers(extra = {}) {
  return { "X-JINX-Role": activeRole(), "X-JINX-Package": "c5isr", ...extra };
}

async function getJSON(url) {
  const response = await fetch(url, { headers: headers() });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
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
      <span>${escapeHTML(track.location)} · ${escapeHTML(track.lifecycle || track.status)} · confidence ${escapeHTML(track.confidence)}</span>
      <span>${track.human_validated ? "human validated" : "human validation pending"} · updated ${formatTime(track.updated_at)}</span>
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
      <span>Routes: ${escapeHTML((mission.routes || []).join(", ") || "none")}</span>
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
      <span>${escapeHTML(report.location || "no location")} · confidence ${escapeHTML(report.confidence)} · ${escapeHTML(report.summary)}</span>
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
      <strong>${escapeHTML(item.kind)} · ${escapeHTML(item.severity)} · ${escapeHTML(item.review_state)}</strong>
      <span>${escapeHTML(item.summary)}</span>
      <span>assigned ${escapeHTML(item.assigned_reviewer)} · escalation ${escapeHTML(item.escalation_state)}</span>
    </article>
  `);
}

function renderMissionImpacts(impacts) {
  document.querySelector("#mission-impact-count").textContent = impacts.length;
  renderList(c5.missionImpactList, impacts, "No mission impacts", (impact) => `
    <article class="item mission-impact">
      <strong>${escapeHTML(impact.impacted_area)} · confidence ${escapeHTML(impact.confidence)}</strong>
      <span>${escapeHTML(impact.summary)}</span>
      <span>review: ${escapeHTML(impact.recommended_review_role)}</span>
    </article>
  `);
}

function renderAdvisories(advisories) {
  document.querySelector("#metric-advisories").textContent = advisories.length;
  document.querySelector("#advisory-count").textContent = advisories.length;
  renderList(c5.advisoryList, advisories.slice(-10).reverse(), "No advisories", (advisory) => `
    <article class="item advisory">
      <strong>${escapeHTML(advisory.recipient_id)}</strong>
      <span>${escapeHTML(advisory.summary)} · confidence ${escapeHTML(advisory.confidence)}</span>
    </article>
  `);
}

function renderConflicts(conflicts) {
  document.querySelector("#conflict-count").textContent = conflicts.length;
  renderList(c5.conflictList, conflicts.slice(-8).reverse(), "No conflicts", (conflict) => `
    <article class="item conflict">
      <strong>${escapeHTML(conflict.conflict_type)}</strong>
      <span>${escapeHTML(conflict.explanation)}</span>
      <span>confidence ${escapeHTML(conflict.confidence)} · review: ${escapeHTML(conflict.recommended_review_role)}</span>
    </article>
  `);
}

function renderRecommendations(recommendations) {
  document.querySelector("#recommendation-count").textContent = recommendations.length;
  renderList(c5.recommendationList, recommendations.slice(-8).reverse(), "No recommendations", (recommendation) => `
    <article class="item recommendation">
      <strong>${escapeHTML(recommendation.recommendation_type)}</strong>
      <span>${escapeHTML(recommendation.text)}</span>
    </article>
  `);
}

function renderBrain(messages) {
  document.querySelector("#brain-chat-count").textContent = messages.length;
  renderList(c5.brainChatList, messages.slice(-5).reverse(), "No Brain chat yet", (message) => `
    <article class="item brain-chat">
      <strong>${escapeHTML(message.answer.confidence_band)} · Core reachback ${message.answer.core_reachback_used ? "used" : "not used"}</strong>
      <span>Q: ${escapeHTML(message.question.text)}</span>
      <span>${escapeHTML(message.answer.answer_text)}</span>
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
    setStatus(false, "API offline");
  }
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

c5.refreshButton.addEventListener("click", refresh);
c5.roleSelect.addEventListener("change", refresh);
refresh();
