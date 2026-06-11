const els = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
  copName: document.querySelector("#cop-name"),
  copMap: document.querySelector("#cop-map"),
  trackList: document.querySelector("#track-list"),
  trackCount: document.querySelector("#track-count"),
  missionContext: document.querySelector("#mission-context"),
  layerList: document.querySelector("#layer-list"),
  reportList: document.querySelector("#report-list"),
  reviewCenterList: document.querySelector("#review-center-list"),
  missionImpactList: document.querySelector("#mission-impact-list"),
  scenarioPackList: document.querySelector("#scenario-pack-list"),
  simRunList: document.querySelector("#sim-run-list"),
  advisoryList: document.querySelector("#advisory-list"),
  eventList: document.querySelector("#event-list"),
  timelineList: document.querySelector("#timeline-list"),
  opsConsoleList: document.querySelector("#ops-console-list"),
  operatorLoopList: document.querySelector("#operator-loop-list"),
  conflictList: document.querySelector("#conflict-list"),
  recommendationList: document.querySelector("#recommendation-list"),
  analysisRunList: document.querySelector("#analysis-run-list"),
  explanationList: document.querySelector("#explanation-list"),
  brainChatList: document.querySelector("#brain-chat-list"),
  brainReferenceList: document.querySelector("#brain-reference-list"),
  auditList: document.querySelector("#audit-list"),
  provenanceList: document.querySelector("#provenance-list"),
  boundaryList: document.querySelector("#boundary-list"),
  isrFeedList: document.querySelector("#isr-feed-list"),
  moduleList: document.querySelector("#module-list"),
  activityList: document.querySelector("#activity-list"),
  reportForm: document.querySelector("#report-form"),
  commandForm: document.querySelector("#command-form"),
  intelForm: document.querySelector("#intel-form"),
  isrFeedForm: document.querySelector("#isr-feed-form"),
  brainQueryForm: document.querySelector("#brain-query-form"),
  brainChatForm: document.querySelector("#brain-chat-form"),
  refreshButton: document.querySelector("#refresh-button"),
  demoButton: document.querySelector("#demo-button"),
  missionButton: document.querySelector("#mission-button"),
  roleSelect: document.querySelector("#role-select"),
  metrics: {
    tracks: document.querySelector("#metric-tracks"),
    reports: document.querySelector("#metric-reports"),
    reviewQueue: document.querySelector("#metric-review-queue"),
    conflicts: document.querySelector("#metric-conflicts"),
    isrFeeds: document.querySelector("#metric-isr-feeds"),
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

async function getOptionalJSON(url, fallback) {
  const response = await fetch(url, { headers: requestHeaders() });
  if (response.status === 403) return fallback;
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
      <span>${escapeHTML(track.location)} · ${escapeHTML(track.lifecycle || track.status)} · confidence ${escapeHTML(track.confidence)}</span>
      <span>${escapeHTML(track.report_count)} reports · ${escapeHTML(track.conflict_count)} conflicts · ${escapeHTML(track.history_count)} history points</span>
      <span>${track.human_validated ? "human validated" : "human validation pending"} · updated ${formatTime(track.updated_at)}</span>
      <div class="review-row">
        <button type="button" data-track-validate="${escapeHTML(track.entity_id)}">Validate track</button>
      </div>
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

function renderMission(mission) {
  document.querySelector("#mission-id").textContent = mission.id || "not loaded";
  if (!mission.id) {
    els.missionContext.className = "list empty";
    els.missionContext.textContent = "No mission context loaded";
    return;
  }
  const tasks = mission.tasks || [];
  els.missionContext.className = "list";
  els.missionContext.innerHTML = `
    <article class="item">
      <strong>${escapeHTML(mission.mission_statement)}</strong>
      <span>${escapeHTML(mission.commander_intent)}</span>
      <span>Routes: ${escapeHTML((mission.routes || []).join(", ") || "none")} · Areas: ${escapeHTML((mission.named_areas || []).join(", ") || "none")}</span>
    </article>
    ${tasks.map((task) => `
      <article class="item">
        <strong>${escapeHTML(task.task_id)} · ${escapeHTML(task.title)}</strong>
        <span>${escapeHTML(task.purpose)}</span>
        <span>${escapeHTML(task.assigned_to)} · ${escapeHTML(task.route || "no route")} · ${escapeHTML(task.named_area || "no area")}</span>
      </article>
    `).join("")}
  `;
}

function renderLayers(layers) {
  els.layerList.innerHTML = (layers || []).map((layer) => `
    <label class="layer-toggle">
      <input type="checkbox" data-layer="${escapeHTML(layer.id)}" ${layer.enabled ? "checked" : ""} />
      ${escapeHTML(layer.label)}
    </label>
  `).join("");
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

function renderReviewCenter(items) {
  document.querySelector("#review-center-count").textContent = items.length;
  renderList(els.reviewCenterList, items, "No review items", (item) => `
    <article class="item review-item">
      <strong>${escapeHTML(item.kind)} · ${escapeHTML(item.severity)} · ${escapeHTML(item.review_state)}</strong>
      <span>${escapeHTML(item.summary)}</span>
      <span>assigned ${escapeHTML(item.assigned_reviewer)} · escalation ${escapeHTML(item.escalation_state)}</span>
      <span>${item.needs_operator_clarification ? "operator clarification needed" : "operator clarification clear"} · ${item.needs_intel_review ? "INTEL review" : "INTEL clear"} · ${item.needs_net_review ? "NET review" : "NET clear"}</span>
    </article>
  `);
}

function renderMissionImpacts(impacts) {
  document.querySelector("#mission-impact-count").textContent = impacts.length;
  renderList(els.missionImpactList, impacts, "No mission impacts", (impact) => `
    <article class="item mission-impact">
      <strong>${escapeHTML(impact.impacted_area)} · confidence ${escapeHTML(impact.confidence)}</strong>
      <span>${escapeHTML(impact.summary)}</span>
      <span>tasks: ${escapeHTML((impact.affected_tasks || []).join(", ") || "none")} · routes: ${escapeHTML((impact.affected_routes || []).join(", ") || "none")}</span>
      <span>review: ${escapeHTML(impact.recommended_review_role)}</span>
    </article>
  `);
}

function renderScenarioPacks(packs) {
  document.querySelector("#scenario-pack-count").textContent = packs.length;
  renderList(els.scenarioPackList, packs, "No scenario packs", (pack) => `
    <article class="item scenario">
      <strong>${escapeHTML(pack.name)}</strong>
      <span>${escapeHTML(pack.summary)}</span>
      <span>expects: ${escapeHTML((pack.expected_outputs || []).join(", "))}</span>
      <div class="review-row">
        <button type="button" data-run-scenario="${escapeHTML(pack.id)}">Run scenario</button>
      </div>
    </article>
  `);
}

function renderSimulationRuns(runs) {
  document.querySelector("#sim-run-count").textContent = runs.length;
  renderList(els.simRunList, runs.slice(-6).reverse(), "No scenario runs", (run) => `
    <article class="item scenario">
      <strong>${escapeHTML(run.scenario_name)} · ${escapeHTML(run.status)}</strong>
      <span>actual: ${escapeHTML((run.actual_outputs || []).join(", ") || "none")}</span>
      <span>expected: ${escapeHTML((run.expected_outputs || []).join(", ") || "none")}</span>
      <span>BRAIN answer: ${escapeHTML(run.brain_answer_id)}</span>
    </article>
  `);
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

function renderConflicts(conflicts) {
  els.metrics.conflicts.textContent = conflicts.length;
  document.querySelector("#conflict-count").textContent = conflicts.length;
  renderList(els.conflictList, conflicts, "No conflicts", (conflict) => `
    <article class="item conflict">
      <strong>${escapeHTML(conflict.conflict_type)}</strong>
      <span>${escapeHTML(conflict.explanation)}</span>
      <span>confidence ${escapeHTML(conflict.confidence)} · review: ${escapeHTML(conflict.recommended_review_role)}</span>
      <ul>${(conflict.potential_human_resolutions || []).map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul>
    </article>
  `);
}

function renderRecommendations(recommendations) {
  document.querySelector("#recommendation-count").textContent = recommendations.length;
  renderList(els.recommendationList, recommendations, "No recommendations", (recommendation) => `
    <article class="item recommendation">
      <strong>${escapeHTML(recommendation.recommendation_type)}</strong>
      <span>${escapeHTML(recommendation.text)}</span>
      <span>Brain refs: ${escapeHTML((recommendation.brain_references || []).join(", ") || "none")}</span>
      <ul>${(recommendation.allowed_actions || []).map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul>
    </article>
  `);
}

function renderAnalysisRuns(runs) {
  document.querySelector("#analysis-run-count").textContent = runs.length;
  renderList(els.analysisRunList, runs, "No analysis runs", (run) => `
    <article class="item analysis">
      <strong>${escapeHTML(run.id)} · ${escapeHTML(run.confidence_summary?.band || "unknown")}</strong>
      <span>inputs ${escapeHTML((run.input_ids || []).length)} · outputs ${escapeHTML((run.output_ids || []).length)} · confidence ${escapeHTML(run.confidence_summary?.value)}</span>
      <span>${escapeHTML((run.modules_consulted || []).join(", "))}</span>
    </article>
  `);
}

function renderExplanations(explanations) {
  document.querySelector("#explanation-count").textContent = explanations.length;
  renderList(els.explanationList, explanations, "No explanations", (explanation) => `
    <article class="item explanation">
      <strong>${escapeHTML(explanation.output_type)} · ${escapeHTML(explanation.output_id)}</strong>
      <span>${escapeHTML(explanation.why_flagged)}</span>
      <span>uncertainty: ${escapeHTML(explanation.uncertainty)}</span>
      <span>review: ${escapeHTML(explanation.recommended_review_role)}</span>
    </article>
  `);
}

function renderBrainChat(messages) {
  document.querySelector("#brain-chat-count").textContent = messages.length;
  renderList(els.brainChatList, messages.slice(-8).reverse(), "No Brain chat yet", (message) => `
    <article class="item brain-chat">
      <strong>${escapeHTML(message.answer.confidence_band)} · Core reachback ${message.answer.core_reachback_used ? "used" : "not used"}</strong>
      <span>Q: ${escapeHTML(message.question.text)}</span>
      <span>${escapeHTML(message.answer.answer_text)}</span>
      <span>refs: ${escapeHTML((message.answer.references || []).join(", ") || "none")}</span>
      <span>uncertainty: ${escapeHTML(message.answer.uncertainty)}</span>
    </article>
  `);
}

function renderBrainReferences(matches) {
  document.querySelector("#brain-reference-count").textContent = matches.length;
  renderList(els.brainReferenceList, matches, "No Brain references", (record) => `
    <article class="item brain">
      <strong>${escapeHTML(record.title)} · ${escapeHTML(record.scope)}</strong>
      <span>${escapeHTML(record.summary)}</span>
      <span>tags: ${escapeHTML((record.tags || []).join(", "))}</span>
    </article>
  `);
}

function renderAudit(records) {
  document.querySelector("#audit-count").textContent = records.length;
  renderList(els.auditList, records.slice(-10).reverse(), "No audit records", (record) => `
    <article class="item audit">
      <strong>${escapeHTML(record.event_type)} · ${escapeHTML(record.actor)}</strong>
      <span>${escapeHTML(record.summary)}</span>
    </article>
  `);
}

function renderProvenance(records) {
  document.querySelector("#provenance-count").textContent = records.length;
  renderList(els.provenanceList, records.slice(-10).reverse(), "No provenance", (record) => `
    <article class="item provenance">
      <strong>${escapeHTML(record.processed_by_module)} · ${escapeHTML(record.source)}</strong>
      <span>event ${escapeHTML(record.event_id)} · confidence ${escapeHTML(record.confidence)}</span>
      <span>${escapeHTML((record.transformations || []).join(", "))}</span>
    </article>
  `);
}

function renderBoundaries(boundary) {
  const modules = boundary.modules || [];
  const routes = boundary.routes || [];
  document.querySelector("#boundary-count").textContent = `${routes.length}/${modules.length}`;
  renderList(els.boundaryList, modules.slice(0, 8), "No boundary data", (module) => `
    <article class="item boundary">
      <strong>${escapeHTML(module.name)} · ${escapeHTML(module.license_scope)}</strong>
      <span>inputs ${escapeHTML((module.allowed_inputs || []).length)} · outputs ${escapeHTML((module.allowed_outputs || []).length)}</span>
      <span>deps: ${escapeHTML((module.dependencies || []).join(", ") || "none")}</span>
    </article>
  `);
}

function renderISRFeeds(feeds) {
  els.metrics.isrFeeds.textContent = feeds.length;
  document.querySelector("#isr-feed-count").textContent = feeds.length;
  renderList(els.isrFeedList, feeds, "No ISR feeds", (feed) => `
    <article class="item isr">
      <strong>${escapeHTML(feed.feed_name)} · ${escapeHTML(feed.status)}</strong>
      <span>${escapeHTML(feed.feed_type)} · ${escapeHTML(feed.coverage_area)} · confidence ${escapeHTML(feed.confidence)}</span>
      <span>${escapeHTML(feed.summary)}</span>
      <span>${escapeHTML(feed.data_mode)} · BUS delivered: ${escapeHTML(feed.delivered_to_bus)}</span>
    </article>
  `);
}

function renderTimeline(timeline) {
  renderList(els.timelineList, timeline.slice(-10).reverse(), "No timeline entries", (entry) => `
    <article class="item timeline">
      <strong>${escapeHTML(entry.kind)} · ${formatTime(entry.timestamp)}</strong>
      <span>${escapeHTML(entry.summary)}</span>
    </article>
  `);
}

function renderOpsConsole(consoleState) {
  const counts = consoleState.counts || {};
  document.querySelector("#ops-console-count").textContent = consoleState.mode || "unknown";
  renderList(els.opsConsoleList, [
    {
      title: `Authority · ${consoleState.authority || "unknown"}`,
      detail: `live adapters ${consoleState.live_adapters || "unknown"} · routes ${consoleState.delivered_routes || 0}/${consoleState.denied_routes || 0}`,
      extra: `reports ${counts.operator_reports || 0} · conflicts ${counts.conflicts || 0} · impacts ${counts.mission_impacts || 0} · chat ${counts.brain_chat_messages || 0}`,
    },
    {
      title: "Licensed Modules",
      detail: (consoleState.licensed_modules || []).join(", ") || "none",
      extra: `audit ${consoleState.audit_records || 0} · provenance ${consoleState.provenance_records || 0}`,
    },
  ], "No ops console", (item) => `
    <article class="item ops">
      <strong>${escapeHTML(item.title)}</strong>
      <span>${escapeHTML(item.detail)}</span>
      <span>${escapeHTML(item.extra)}</span>
    </article>
  `);
}

function renderOperatorLoop(packet) {
  document.querySelector("#operator-loop-status").textContent = packet.status || "unknown";
  renderList(els.operatorLoopList, packet.flow_steps || [], "No operator loop packet", (step) => `
    <article class="item operator-loop">
      <strong>${escapeHTML(step.label)} · ${escapeHTML(step.state)}</strong>
      <span>count ${escapeHTML(step.count)} · latest ${escapeHTML(step.latest_id || "none")}</span>
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
    const [
      health,
      cop,
      mission,
      layers,
      reports,
      reviewCenter,
      missionImpacts,
      advisories,
      events,
      opsConsole,
      operatorLoop,
      conflicts,
      recommendations,
      analysisRuns,
      explanations,
      brainChat,
      brainReferences,
      audit,
      provenance,
      boundaries,
      isrFeeds,
      timeline,
      scenarios,
      simRuns,
      modules,
    ] = await Promise.all([
      getJSON("/api/health"),
      getJSON("/api/cop"),
      getJSON("/api/mission-context"),
      getJSON("/api/cop/layers"),
      getJSON("/api/operator-reports"),
      getJSON("/api/review-center"),
      getJSON("/api/mission-impacts"),
      getJSON("/api/advisories"),
      getJSON("/api/events"),
      getJSON("/api/core/ops-console"),
      getJSON("/api/core/operator-loop"),
      getJSON("/api/conflicts"),
      getJSON("/api/recommendations"),
      getJSON("/api/core/analysis-runs"),
      getJSON("/api/core/explanations"),
      getJSON("/api/brain/chat-messages"),
      getJSON("/api/brain/references"),
      getJSON("/api/core/audit"),
      getJSON("/api/core/provenance"),
      getJSON("/api/core/module-boundaries"),
      getOptionalJSON("/api/isr-feeds", { isr_feeds: [] }),
      getJSON("/api/timeline"),
      getJSON("/api/sim/c5isr-scenarios"),
      getJSON("/api/sim/runs"),
      getJSON("/api/modules"),
    ]);
    setStatus(true, `${health.service} API online`);
    renderTracks(cop);
    renderMission(mission.mission);
    renderLayers(layers.layers || []);
    renderReports(reports.operator_reports || []);
    renderReviewCenter(reviewCenter.items || []);
    renderMissionImpacts(missionImpacts.mission_impacts || []);
    renderAdvisories(advisories.advisories || []);
    renderEvents(events.events || []);
    renderOpsConsole(opsConsole);
    renderOperatorLoop(operatorLoop.operator_loop || {});
    renderConflicts(conflicts.conflicts || []);
    renderRecommendations(recommendations.recommendations || []);
    renderAnalysisRuns(analysisRuns.analysis_runs || []);
    renderExplanations(explanations.explanations || []);
    renderBrainChat(brainChat.messages || []);
    renderBrainReferences(brainReferences.matches || []);
    renderAudit(audit.audit_records || []);
    renderProvenance(provenance.provenance || []);
    renderBoundaries(boundaries);
    renderISRFeeds(isrFeeds.isr_feeds || []);
    renderTimeline(timeline.timeline || []);
    renderScenarioPacks(scenarios.scenario_packs || []);
    renderSimulationRuns(simRuns.simulation_runs || []);
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

els.intelForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.intelForm).entries());
  try {
    const response = await postJSON("/api/intelligence-summaries", data);
    addActivity(`INTEL summary ${response.summary_id} generated ${response.events_generated} C5ISR events.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

els.isrFeedForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.isrFeedForm).entries());
  try {
    const response = await postJSON("/api/isr-feeds", data);
    addActivity(`ISR feed ${response.feed_id} delivered to BUS: ${response.delivered_to_bus}.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

els.brainQueryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.brainQueryForm).entries());
  try {
    const response = await postJSON("/api/brain/query", data);
    renderBrainReferences(response.matches || []);
    addActivity(`Brain returned ${(response.matches || []).length} references.`);
  } catch (error) {
    addActivity(error.message);
  }
});

els.brainChatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.brainChatForm).entries());
  data.role = activeRole();
  data.use_core_reachback = els.brainChatForm.querySelector('[name="use_core_reachback"]').checked ? "true" : "false";
  try {
    const response = await postJSON("/api/brain/chat", data);
    addActivity(`BRAIN answered ${response.answer.id} with ${response.answer.confidence_band} confidence.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

els.missionButton.addEventListener("click", async () => {
  try {
    const response = await postJSON("/api/mission-context", {
      mission_statement: "Synthetic C5ISR mission monitors Route Alpha and Area Alpha.",
      commander_intent: "Maintain coherent COP confidence and surface mission impacts for review.",
      route: "Route Alpha",
      named_area: "Area Alpha",
    });
    addActivity(`Mission ${response.mission.id} loaded.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

els.trackList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-track-validate]");
  if (!button) return;
  try {
    const response = await postJSON("/api/cop/tracks/validate", {
      entity_id: button.dataset.trackValidate,
      reviewer_id: activeRole() === "commander" ? "commander-alpha" : "c5isr-manager-alpha",
      note: "Human validation from COP manager.",
    });
    addActivity(`Track ${response.track.entity_id} marked ${response.track.lifecycle}.`);
    await refreshDashboard();
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

els.scenarioPackList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-run-scenario]");
  if (!button) return;
  try {
    const response = await postJSON("/api/sim/run-c5isr", {
      scenario_id: button.dataset.runScenario,
    });
    addActivity(`Scenario ${response.simulation_run.scenario_name} produced ${response.simulation_run.actual_outputs.length} outputs.`);
    await refreshDashboard();
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
