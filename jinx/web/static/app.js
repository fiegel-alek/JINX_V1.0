const els = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
  authSessionList: document.querySelector("#auth-session-list"),
  licenseList: document.querySelector("#license-list"),
  identityUserList: document.querySelector("#identity-user-list"),
  boundaryControlList: document.querySelector("#boundary-control-list"),
  adapterList: document.querySelector("#adapter-list"),
  evidencePackList: document.querySelector("#evidence-pack-list"),
  reviewTaskList: document.querySelector("#review-task-list"),
  doctrineList: document.querySelector("#doctrine-list"),
  memoryList: document.querySelector("#memory-list"),
  recallList: document.querySelector("#recall-list"),
  adapterRunList: document.querySelector("#adapter-run-list"),
  auditReplayList: document.querySelector("#audit-replay-list"),
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
  fabricMessageList: document.querySelector("#fabric-message-list"),
  fabricDeadLetterList: document.querySelector("#fabric-dead-letter-list"),
  coreContextList: document.querySelector("#core-context-list"),
  conflictList: document.querySelector("#conflict-list"),
  recommendationList: document.querySelector("#recommendation-list"),
  analysisRunList: document.querySelector("#analysis-run-list"),
  explanationList: document.querySelector("#explanation-list"),
  brainChatList: document.querySelector("#brain-chat-list"),
  brainExplanationList: document.querySelector("#brain-explanation-list"),
  brainOptionList: document.querySelector("#brain-option-list"),
  brainChecklistList: document.querySelector("#brain-checklist-list"),
  learningProposalList: document.querySelector("#learning-proposal-list"),
  brainReferenceList: document.querySelector("#brain-reference-list"),
  auditList: document.querySelector("#audit-list"),
  policyDecisionList: document.querySelector("#policy-decision-list"),
  provenanceList: document.querySelector("#provenance-list"),
  boundaryList: document.querySelector("#boundary-list"),
  isrFeedList: document.querySelector("#isr-feed-list"),
  netPlanList: document.querySelector("#net-plan-list"),
  netIssueList: document.querySelector("#net-issue-list"),
  netValidationList: document.querySelector("#net-validation-list"),
  netAdvisoryList: document.querySelector("#net-advisory-list"),
  moduleList: document.querySelector("#module-list"),
  activityList: document.querySelector("#activity-list"),
  authForm: document.querySelector("#auth-form"),
  clearSessionButton: document.querySelector("#clear-session-button"),
  licenseForm: document.querySelector("#license-form"),
  identityUserForm: document.querySelector("#identity-user-form"),
  adapterForm: document.querySelector("#adapter-form"),
  adapterExecuteForm: document.querySelector("#adapter-execute-form"),
  reportForm: document.querySelector("#report-form"),
  commandForm: document.querySelector("#command-form"),
  intelForm: document.querySelector("#intel-form"),
  isrFeedForm: document.querySelector("#isr-feed-form"),
  netPlanForm: document.querySelector("#net-plan-form"),
  brainQueryForm: document.querySelector("#brain-query-form"),
  brainChatForm: document.querySelector("#brain-chat-form"),
  doctrineForm: document.querySelector("#doctrine-form"),
  memoryForm: document.querySelector("#memory-form"),
  recallForm: document.querySelector("#recall-form"),
  learningPromotionForm: document.querySelector("#learning-promotion-form"),
  auditReplayForm: document.querySelector("#audit-replay-form"),
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

const SESSION_KEY = "jinx-ops-session-token";

function setStatus(ok, text) {
  els.apiStatus.classList.toggle("ok", ok);
  els.apiStatus.classList.toggle("error", !ok);
  els.apiStatusText.textContent = text;
}

function activeRole() {
  return els.roleSelect.value;
}

function activeReviewerId() {
  const mapping = {
    commander: "commander-alpha",
    c5isr_manager: "c5isr-manager-alpha",
    network_manager: "net-manager-alpha",
    intel_analyst: "intel-alpha",
    simulation_operator: "sim-operator-alpha",
    system_administrator: "systemadministrator",
    auditor: "auditor-alpha",
    operator: "operator-alpha",
  };
  return mapping[activeRole()] || "systemadministrator";
}

function activeSessionToken() {
  return localStorage.getItem(SESSION_KEY) || "";
}

function requestHeaders(extra = {}) {
  const sessionToken = activeSessionToken();
  return sessionToken
    ? { "X-JINX-Role": activeRole(), "X-JINX-Session": sessionToken, ...extra }
    : { "X-JINX-Role": activeRole(), ...extra };
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
  const reviewer = activeReviewerId();
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

function renderPolicyDecisions(records) {
  document.querySelector("#policy-decision-count").textContent = records.length;
  renderList(els.policyDecisionList, records.slice(-10).reverse(), "No policy decisions", (record) => `
    <article class="item audit">
      <strong>${record.allowed ? "allowed" : "denied"} · ${escapeHTML(record.source_module)} → ${escapeHTML(record.destination)}</strong>
      <span>${escapeHTML(record.summary)}</span>
      <span>${escapeHTML(record.payload_schema)} · ${escapeHTML(record.message_id)}</span>
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

function renderNetworkPlans(plans) {
  document.querySelector("#net-plan-count").textContent = plans.length;
  renderList(els.netPlanList, plans.slice(-6).reverse(), "No NET plans", (plan) => `
    <article class="item net">
      <strong>${escapeHTML(plan.name)} · ${escapeHTML(plan.source_format)}</strong>
      <span>nodes ${escapeHTML((plan.nodes || []).length)} · timeslots ${escapeHTML((plan.timeslots || []).length)} · LOS ${escapeHTML((plan.los_links || []).length)}</span>
      <span>${escapeHTML(plan.data_mode)} · confidence ${escapeHTML(plan.confidence)}</span>
    </article>
  `);
}

function renderNetworkIssues(issues) {
  document.querySelector("#net-issue-count").textContent = issues.length;
  renderList(els.netIssueList, issues.slice(-8).reverse(), "No NET issues", (issue) => `
    <article class="item net conflict">
      <strong>${escapeHTML(issue.issue_type)} · ${escapeHTML(issue.severity)}</strong>
      <span>${escapeHTML(issue.summary)}</span>
      <span>nodes: ${escapeHTML((issue.affected_nodes || []).join(", ") || "none")} · delivered ${escapeHTML(issue.delivered_to_core)}</span>
      <span>review: ${escapeHTML(issue.recommended_review_role)}</span>
    </article>
  `);
}

function renderNetworkValidationRuns(runs) {
  document.querySelector("#net-validation-count").textContent = runs.length;
  renderList(els.netValidationList, runs.slice(-6).reverse(), "No NET validation runs", (run) => `
    <article class="item net">
      <strong>${escapeHTML(run.id)}</strong>
      <span>${escapeHTML(run.summary)}</span>
      <span>plan ${escapeHTML(run.plan_id)} · issues ${escapeHTML((run.issue_ids || []).length)} · confidence ${escapeHTML(run.confidence)}</span>
    </article>
  `);
}

function renderNetworkAdvisories(advisories) {
  document.querySelector("#net-advisory-count").textContent = advisories.length;
  renderList(els.netAdvisoryList, advisories.slice(-8).reverse(), "No NET advisories", (advisory) => `
    <article class="item net recommendation">
      <strong>${escapeHTML(advisory.recommended_review_role)} · confidence ${escapeHTML(advisory.confidence)}</strong>
      <span>${escapeHTML(advisory.summary)}</span>
      <span>${advisory.required_human_review ? "human review required" : "review missing"} · issue ${escapeHTML(advisory.issue_id)}</span>
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

function renderFabric(fabric) {
  const messages = fabric.messages || [];
  const deadLetters = fabric.dead_letters || [];
  const counts = fabric.counts || {};
  document.querySelector("#fabric-message-count").textContent = `${messages.length} total`;
  document.querySelector("#fabric-dead-letter-count").textContent = deadLetters.length;
  renderList(els.fabricMessageList, messages.slice(-12).reverse(), "No fabric messages", (message) => `
    <article class="item ops">
      <strong>${escapeHTML(message.status)} · ${escapeHTML(message.topic)}</strong>
      <span>${escapeHTML(message.source_module)} → ${escapeHTML(message.destination)} · ${escapeHTML(message.payload_schema)}</span>
      <span>policy: ${escapeHTML(message.policy_reason)} · confidence ${escapeHTML(message.confidence ?? "n/a")}</span>
      <span>redactions: ${escapeHTML((message.redacted_fields || []).join(", ") || "none")} · simulation ${escapeHTML(message.simulation_flag)}</span>
    </article>
  `);
  renderList(els.fabricDeadLetterList, deadLetters.slice(-8).reverse(), "No dead letters", (message) => `
    <article class="item conflict">
      <strong>${escapeHTML(message.topic)} · denied</strong>
      <span>${escapeHTML(message.source_module)} → ${escapeHTML(message.destination)} · ${escapeHTML(message.payload_schema)}</span>
      <span>${escapeHTML(message.policy_reason)}</span>
    </article>
  `);
  document.querySelector("#fabric-message-count").textContent =
    `${messages.length} total · ${counts.delivered || 0} delivered · ${counts.redacted || 0} redacted`;
}

function renderAuthSession(auth, entitlements) {
  const session = auth.session;
  document.querySelector("#auth-session-state").textContent = session ? session.package : "header-only";
  if (!session) {
    els.authSessionList.className = "list empty";
    els.authSessionList.textContent = "No active session token";
    return;
  }
  els.authSessionList.className = "list";
  els.authSessionList.innerHTML = `
    <article class="item ops">
      <strong>${escapeHTML(session.display_name)} · ${escapeHTML(session.package)}</strong>
      <span>${escapeHTML((session.roles || []).join(", "))} · ${escapeHTML(session.auth_mode)}</span>
      <span>reporter ${escapeHTML(session.reporter_id)} · device ${escapeHTML(session.device_id)}</span>
      <span>license ${entitlements.license_active ? "active" : "inactive"} · user authorized ${entitlements.authorized_for_user ? "yes" : "no"}</span>
      <span>expires ${escapeHTML(session.expires_at)}</span>
    </article>
  `;
}

function renderLicenses(licenseState) {
  const licenses = licenseState.licenses || [];
  document.querySelector("#license-count").textContent = licenses.length;
  renderList(els.licenseList, licenses, "No license records", (license) => `
    <article class="item ops">
      <strong>${escapeHTML(license.package)} · ${license.active ? "active" : "inactive"}</strong>
      <span>${escapeHTML(license.label || "")}</span>
      <span>users: ${escapeHTML((license.authorized_users || []).join(", ") || "none")}</span>
      <span>simulation only ${license.simulation_only ? "yes" : "no"} · real adapters ${license.controlled_real_adapters_enabled ? "enabled" : "disabled"}</span>
    </article>
  `);
}

function renderIdentity(identity) {
  const users = identity.users || [];
  document.querySelector("#identity-user-count").textContent = users.length;
  renderList(els.identityUserList, users, "No identity users", (user) => `
    <article class="item ops">
      <strong>${escapeHTML(user.display_name)} · ${escapeHTML(user.username)}</strong>
      <span>${escapeHTML((user.roles || []).join(", "))} · package ${escapeHTML(user.default_package || "operator")}</span>
      <span>reporter ${escapeHTML(user.reporter_id || "n/a")} · device ${escapeHTML(user.device_id || "n/a")}</span>
    </article>
  `);
}

function renderBoundaryControls(boundaryControls) {
  const packages = boundaryControls.packages || [];
  document.querySelector("#boundary-control-count").textContent = packages.length;
  renderList(els.boundaryControlList, packages, "No boundary controls", (policy) => `
    <article class="item boundary">
      <strong>${escapeHTML(policy.package)} · ${policy.active ? "active" : "inactive"}</strong>
      <span>${escapeHTML(policy.summary)}</span>
      <span>denies: ${escapeHTML((policy.denied_permission_prefixes || []).join(", ") || "none")}</span>
      <span>users: ${escapeHTML((policy.authorized_users || []).join(", ") || "none")}</span>
    </article>
  `);
}

function renderAdapters(adapterState) {
  const adapters = adapterState.adapters || [];
  const summary = adapterState.summary || {};
  document.querySelector("#adapter-count").textContent = adapters.length;
  document.querySelector("#adapter-summary").textContent =
    `${summary.enabled || 0} enabled · ${summary.blocked || 0} blocked`;
  renderList(els.adapterList, adapters, "No adapter manifests", (adapter) => `
    <article class="item ops">
      <strong>${escapeHTML(adapter.name)} · ${escapeHTML(adapter.status)}</strong>
      <span>${escapeHTML(adapter.adapter_type)} · ${escapeHTML(adapter.target_module)} · ${escapeHTML(adapter.data_mode)}</span>
      <span>permission ${escapeHTML(adapter.permission)} · gate ${adapter.gate_allowed ? "allow" : "deny"} · policy ${adapter.policy_allowed ? "allow" : "deny"}</span>
      <span>${escapeHTML(adapter.policy_reason || "")}</span>
    </article>
  `);
}

function renderEvidencePacks(records, summary = {}) {
  document.querySelector("#evidence-pack-count").textContent = summary.total ?? records.length;
  renderList(els.evidencePackList, records.slice(-8).reverse(), "No evidence packs", (record) => `
    <article class="item ops">
      <strong>${escapeHTML(record.source_kind)} · ${escapeHTML(record.confidence_band)}</strong>
      <span>${escapeHTML(record.title)}</span>
      <span>${escapeHTML(record.summary)}</span>
      <span>${escapeHTML(record.source_module)} · review ${escapeHTML(record.recommended_review_role)}</span>
    </article>
  `);
}

function renderReviewTasks(records, summary = {}) {
  document.querySelector("#review-task-count").textContent = summary.open ?? records.length;
  renderList(els.reviewTaskList, records.slice(-8).reverse(), "No review tasks", (record) => `
    <article class="item ops">
      <strong>${escapeHTML(record.title)} · ${escapeHTML(record.state)}</strong>
      <span>${escapeHTML(record.summary)}</span>
      <span>${escapeHTML(record.source_kind)} · ${escapeHTML(record.assigned_role)} · confidence ${escapeHTML(record.confidence)}</span>
      <div class="review-row">
        <button type="button" data-review-task="${escapeHTML(record.id)}" data-task-state="acknowledged">Acknowledge</button>
        <button type="button" data-review-task="${escapeHTML(record.id)}" data-task-state="validated">Validate</button>
        <button type="button" data-review-task="${escapeHTML(record.id)}" data-task-state="needs_more_info">Need info</button>
        <button type="button" data-review-task="${escapeHTML(record.id)}" data-task-state="rejected">Reject</button>
      </div>
    </article>
  `);
}

function renderDoctrine(records, summary = {}) {
  document.querySelector("#doctrine-count").textContent = summary.total ?? records.length;
  renderList(els.doctrineList, records.slice(-8).reverse(), "No doctrine records", (record) => `
    <article class="item brain">
      <strong>${escapeHTML(record.title)} · ${escapeHTML(record.scope)}</strong>
      <span>${escapeHTML(record.summary)}</span>
      <span>${escapeHTML(record.source)} · tags ${escapeHTML((record.tags || []).join(", ") || "none")}</span>
    </article>
  `);
}

function renderMemory(memory) {
  const records = memory.records || [];
  const compartments = memory.compartments || [];
  document.querySelector("#memory-count").textContent = records.length;
  renderList(els.memoryList, records.slice(-8).reverse(), "No memory records", (record) => `
    <article class="item ops">
      <strong>${escapeHTML(record.title)} · ${escapeHTML(record.compartment)}</strong>
      <span>${escapeHTML(record.summary)}</span>
      <span>${escapeHTML(record.source_kind)} · ${escapeHTML(record.review_state)} · tags ${escapeHTML((record.tags || []).join(", ") || "none")}</span>
    </article>
  `);
  if (!records.length && compartments.length) {
    renderList(els.memoryList, compartments, "No memory records", (record) => `
      <article class="item ops">
        <strong>${escapeHTML(record.name)}</strong>
        <span>${escapeHTML(record.count)} records</span>
      </article>
    `);
  }
}

function renderRecall(recall) {
  const results = recall.results || [];
  document.querySelector("#recall-count").textContent = recall.count ?? results.length;
  renderList(els.recallList, results, "No recall results", (record) => `
    <article class="item ops">
      <strong>${escapeHTML(record.kind)} · ${escapeHTML(record.title)}</strong>
      <span>${escapeHTML(record.summary)}</span>
      <span>${escapeHTML(record.package_scope)}</span>
    </article>
  `);
}

function renderAdapterRuns(records) {
  document.querySelector("#adapter-run-count").textContent = records.length;
  renderList(els.adapterRunList, records.slice(-8).reverse(), "No adapter runs", (record) => `
    <article class="item ops">
      <strong>${escapeHTML(record.adapter_name)} · ${escapeHTML(record.status)}</strong>
      <span>${escapeHTML(record.target_module)} · ${escapeHTML(record.initiated_by)} · ${escapeHTML(record.data_mode)}</span>
      <span>${escapeHTML(record.summary)}</span>
    </article>
  `);
}

function renderAuditReplay(replay) {
  if (!replay || !replay.id) {
    document.querySelector("#audit-replay-count").textContent = "0";
    els.auditReplayList.className = "list empty";
    els.auditReplayList.textContent = "No replay generated";
    return;
  }
  document.querySelector("#audit-replay-count").textContent = replay.summary?.timeline_events ?? 0;
  renderList(els.auditReplayList, [replay], "No replay generated", (record) => `
    <article class="item audit">
      <strong>${escapeHTML(record.focus_id)} · ${escapeHTML(record.id)}</strong>
      <span>timeline ${escapeHTML(record.summary?.timeline_events ?? 0)} · audit ${escapeHTML(record.summary?.audit_records ?? 0)} · evidence ${escapeHTML(record.summary?.evidence_packs ?? 0)}</span>
      <span>review tasks ${escapeHTML(record.summary?.review_tasks ?? 0)} · memory ${escapeHTML(record.summary?.memory_records ?? 0)} · fabric ${escapeHTML(record.summary?.fabric_messages ?? 0)}</span>
    </article>
  `);
}

function renderCoreContext(context) {
  document.querySelector("#core-context-count").textContent = (context.provenance_refs || []).length;
  renderList(els.coreContextList, [context], "No bounded context", (record) => `
    <article class="item ops">
      <strong>${escapeHTML(record.source || "jinx-core.context")}</strong>
      <span>modules: ${escapeHTML((record.allowed_modules || []).join(", ") || "none")}</span>
      <span>redactions: ${escapeHTML((record.redactions || []).join("; ") || "none")}</span>
      <span>provenance refs: ${escapeHTML((record.provenance_refs || []).slice(0, 6).join(", ") || "none")}</span>
    </article>
  `);
}

function renderBrainExplanations(records) {
  document.querySelector("#brain-explanation-count").textContent = records.length;
  renderList(els.brainExplanationList, records.slice(-6).reverse(), "No BRAIN explanations", (record) => `
    <article class="item brain">
      <strong>${escapeHTML(record.recommended_review_role)} · ${escapeHTML(record.answer_id)}</strong>
      <span>${escapeHTML(record.what_was_detected)}</span>
      <span>${escapeHTML(record.why_it_matters)}</span>
      <span>redactions: ${escapeHTML((record.redactions || []).join("; ") || "none")}</span>
    </article>
  `);
}

function renderBrainOptions(records) {
  document.querySelector("#brain-option-count").textContent = records.length;
  renderList(els.brainOptionList, records.slice(-6).reverse(), "No BRAIN options", (record) => `
    <article class="item recommendation">
      <strong>${escapeHTML(record.confidence_band)} · human approval ${record.required_human_approval ? "required" : "missing"}</strong>
      <span>${escapeHTML(record.description)}</span>
      <span>modules: ${escapeHTML((record.affected_modules || []).join(", ") || "none")}</span>
      <span>risks: ${escapeHTML((record.risks || []).join("; ") || "none")}</span>
    </article>
  `);
}

function renderBrainChecklists(records) {
  document.querySelector("#brain-checklist-count").textContent = records.length;
  renderList(els.brainChecklistList, records, "No BRAIN checklists", (record) => `
    <article class="item brain">
      <strong>${escapeHTML(record.title)}</strong>
      <span>${escapeHTML(record.summary)}</span>
      <span>tags: ${escapeHTML((record.tags || []).join(", ") || "none")}</span>
    </article>
  `);
}

function renderLearningProposals(records) {
  document.querySelector("#learning-proposal-count").textContent = records.length;
  const proposalInput = els.learningPromotionForm?.querySelector('[name="proposal_id"]');
  if (proposalInput && records.length && !proposalInput.value) {
    proposalInput.value = records[records.length - 1].id;
  }
  renderList(els.learningProposalList, records.slice(-6).reverse(), "No learner proposals", (record) => `
    <article class="item ops">
      <strong>${escapeHTML(record.proposal_type)} · ${escapeHTML(record.review_status)}</strong>
      <span>${escapeHTML(record.summary)}</span>
      <span>review: ${escapeHTML(record.required_reviewer_role)} · evidence ${escapeHTML((record.evidence_refs || []).join(", ") || "none")}</span>
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
      entitlements,
      authSession,
      identity,
      licenseState,
      boundaryControls,
      adapters,
      evidencePacks,
      reviewTasks,
      doctrineLibrary,
      memory,
      recall,
      adapterRuns,
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
      fabric,
      coreContext,
      conflicts,
      recommendations,
      analysisRuns,
      explanations,
      brainChat,
      brainExplanations,
      brainOptions,
      brainChecklists,
      learningProposals,
      brainReferences,
      audit,
      auditReplay,
      policyDecisions,
      provenance,
      boundaries,
      isrFeeds,
      netPlans,
      netIssues,
      netValidationRuns,
      netAdvisories,
      timeline,
      scenarios,
      simRuns,
      modules,
    ] = await Promise.all([
      getJSON("/api/health"),
      getJSON("/api/entitlements"),
      getJSON("/api/auth/session"),
      getOptionalJSON("/api/admin/users", { identity: { users: [], roles: [], active_session_count: 0 } }),
      getOptionalJSON("/api/admin/licenses", { licenses: [], summary: {} }),
      getOptionalJSON("/api/core/boundary-controls", { boundary_controls: { packages: [], recent_redactions: [], recent_policy_denials: [] } }),
      getOptionalJSON("/api/admin/adapters", { adapters: [], summary: {} }),
      getOptionalJSON("/api/core/evidence-packs", { evidence_packs: [], summary: { total: 0, by_kind: {} } }),
      getOptionalJSON("/api/core/review-tasks", { review_tasks: [], summary: { total: 0, open: 0 } }),
      getOptionalJSON("/api/brain/doctrine", { doctrine_library: { records: [], summary: { total: 0, scope_counts: {} } } }),
      getOptionalJSON("/api/core/memory", { memory: { compartments: [], records: [] } }),
      getOptionalJSON("/api/core/recall", { recall: { query: "", results: [], count: 0 } }),
      getOptionalJSON("/api/admin/adapter-runs", { adapter_runs: [] }),
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
      getJSON("/api/core/fabric"),
      getJSON("/api/core/context"),
      getJSON("/api/conflicts"),
      getJSON("/api/recommendations"),
      getJSON("/api/core/analysis-runs"),
      getJSON("/api/core/explanations"),
      getJSON("/api/brain/chat-messages"),
      getJSON("/api/brain/explanations"),
      getJSON("/api/brain/options"),
      getJSON("/api/brain/checklists"),
      getJSON("/api/brain/learning-proposals"),
      getJSON("/api/brain/references"),
      getJSON("/api/core/audit"),
      getOptionalJSON("/api/core/audit-replay", { audit_replay: null }),
      getJSON("/api/core/policy-decisions"),
      getJSON("/api/core/provenance"),
      getJSON("/api/core/module-boundaries"),
      getOptionalJSON("/api/isr-feeds", { isr_feeds: [] }),
      getOptionalJSON("/api/net/plans", { network_plans: [] }),
      getOptionalJSON("/api/net/issues", { network_issues: [] }),
      getOptionalJSON("/api/net/validation-runs", { network_validation_runs: [] }),
      getOptionalJSON("/api/net/advisories", { network_advisories: [] }),
      getJSON("/api/timeline"),
      getJSON("/api/sim/c5isr-scenarios"),
      getJSON("/api/sim/runs"),
      getJSON("/api/modules"),
    ]);
    setStatus(true, `${health.service} API online`);
    renderAuthSession(authSession, entitlements);
    renderIdentity(identity.identity || {});
    renderLicenses(licenseState);
    renderBoundaryControls(boundaryControls.boundary_controls || {});
    renderAdapters(adapters);
    renderEvidencePacks(evidencePacks.evidence_packs || [], evidencePacks.summary || {});
    renderReviewTasks(reviewTasks.review_tasks || [], reviewTasks.summary || {});
    renderDoctrine(doctrineLibrary.doctrine_library?.records || [], doctrineLibrary.doctrine_library?.summary || {});
    renderMemory(memory.memory || {});
    renderRecall(recall.recall || {});
    renderAdapterRuns(adapterRuns.adapter_runs || []);
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
    renderFabric(fabric.fabric || {});
    renderCoreContext(coreContext.core_context || {});
    renderConflicts(conflicts.conflicts || []);
    renderRecommendations(recommendations.recommendations || []);
    renderAnalysisRuns(analysisRuns.analysis_runs || []);
    renderExplanations(explanations.explanations || []);
    renderBrainChat(brainChat.messages || []);
    renderBrainExplanations(brainExplanations.brain_explanations || []);
    renderBrainOptions(brainOptions.brain_options || []);
    renderBrainChecklists(brainChecklists.checklists || []);
    renderLearningProposals(learningProposals.learning_proposals || []);
    renderBrainReferences(brainReferences.matches || []);
    renderAudit(audit.audit_records || []);
    renderAuditReplay(auditReplay.audit_replay || null);
    renderPolicyDecisions(policyDecisions.policy_decisions || []);
    renderProvenance(provenance.provenance || []);
    renderBoundaries(boundaries);
    renderISRFeeds(isrFeeds.isr_feeds || []);
    renderNetworkPlans(netPlans.network_plans || []);
    renderNetworkIssues(netIssues.network_issues || []);
    renderNetworkValidationRuns(netValidationRuns.network_validation_runs || []);
    renderNetworkAdvisories(netAdvisories.network_advisories || []);
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

els.netPlanForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.netPlanForm).entries());
  try {
    const response = await postJSON("/api/net/plans", data);
    addActivity(`NET plan ${response.plan_id} produced ${response.issues} issue(s).`);
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

els.authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.authForm).entries());
  try {
    const response = await postJSON("/api/auth/login", data);
    localStorage.setItem(SESSION_KEY, response.session.id);
    addActivity(`Session ${response.session.id} issued for ${response.session.username}.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

els.clearSessionButton.addEventListener("click", async () => {
  if (activeSessionToken()) {
    try {
      await postJSON("/api/auth/logout", {});
    } catch {
      // Best-effort sign-out for the local synthetic session.
    }
  }
  localStorage.removeItem(SESSION_KEY);
  addActivity("Session token cleared; using header-only role mode.");
  await refreshDashboard();
});

els.licenseForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.licenseForm).entries());
  try {
    const response = await postJSON("/api/admin/licenses", data);
    addActivity(`License ${response.license.package} updated.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

els.identityUserForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.identityUserForm).entries());
  try {
    const response = await postJSON("/api/admin/users", data);
    addActivity(`Identity user ${response.user.username} saved.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

els.adapterForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.adapterForm).entries());
  try {
    const response = await postJSON("/api/admin/adapters", data);
    addActivity(`Adapter ${response.adapter.id} updated to ${response.adapter.status}.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

els.adapterExecuteForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.adapterExecuteForm).entries());
  try {
    const response = await postJSON("/api/admin/adapters/execute", data);
    addActivity(`Adapter run ${response.adapter_run.id} completed with status ${response.adapter_run.status}.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

els.doctrineForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.doctrineForm).entries());
  try {
    const response = await postJSON("/api/brain/doctrine", data);
    addActivity(`Doctrine record ${response.doctrine_record.id} registered.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

els.memoryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.memoryForm).entries());
  try {
    const response = await postJSON("/api/core/memory", data);
    addActivity(`Memory record ${response.memory_record.id} captured.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

els.recallForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.recallForm).entries());
  try {
    const response = await postJSON("/api/core/recall", data);
    renderRecall(response.recall || {});
    addActivity(`Recall returned ${response.recall?.count || 0} result(s).`);
  } catch (error) {
    addActivity(error.message);
  }
});

els.learningPromotionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.learningPromotionForm).entries());
  try {
    const response = await postJSON("/api/brain/promote-learning", data);
    addActivity(`Learning proposal ${response.learning_proposal.id} promoted to ${response.doctrine_record.id}.`);
    await refreshDashboard();
  } catch (error) {
    addActivity(error.message);
  }
});

els.auditReplayForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(els.auditReplayForm).entries());
  try {
    const response = await postJSON("/api/core/audit-replay", data);
    renderAuditReplay(response.audit_replay || null);
    addActivity(`Audit replay ${response.audit_replay.id} generated.`);
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

els.reviewTaskList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-review-task]");
  if (!button) return;
  try {
    const response = await postJSON("/api/core/review-tasks", {
      task_id: button.dataset.reviewTask,
      state: button.dataset.taskState,
      reviewer_id: activeReviewerId(),
      note: `Review task moved to ${button.dataset.taskState} from Ops.`,
      remember: button.dataset.taskState === "validated" ? "true" : "false",
    });
    addActivity(`Review task ${response.review_task.id} marked ${response.review_task.state}.`);
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
      reviewer_id: activeReviewerId(),
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
