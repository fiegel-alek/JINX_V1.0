const sim = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
  roleSelect: document.querySelector("#role-select"),
  usernameInput: document.querySelector("#username-input"),
  sessionButton: document.querySelector("#session-button"),
  clearSessionButton: document.querySelector("#clear-session-button"),
  sessionSummary: document.querySelector("#session-summary"),
  sessionMode: document.querySelector("#session-mode"),
  refreshButton: document.querySelector("#refresh-button"),
  scenarioForm: document.querySelector("#scenario-form"),
  scrubForm: document.querySelector("#scrub-form"),
  brainChatForm: document.querySelector("#brain-chat-form"),
  libraryList: document.querySelector("#scenario-library-list"),
  controlSummary: document.querySelector("#control-summary"),
  timelineList: document.querySelector("#scenario-timeline-list"),
  latestResultCard: document.querySelector("#latest-result-card"),
  runList: document.querySelector("#simulation-run-list"),
  comparisonList: document.querySelector("#comparison-list"),
  brainChatList: document.querySelector("#brain-chat-list"),
};

const SESSION_KEY = "jinx-sim-session-token";
const PACKAGE_NAME = "sim";
const USERNAME_BY_ROLE = {
  simulation_operator: "sim-operator-alpha",
  c5isr_manager: "c5isr-manager-alpha",
  system_administrator: "systemadministrator",
};

let library = [];
let selectedScenarioId = "";

function activeRole() {
  return sim.roleSelect.value;
}

function activeSessionToken() {
  return localStorage.getItem(SESSION_KEY) || "";
}

function suggestedUsername() {
  return USERNAME_BY_ROLE[activeRole()] || "sim-operator-alpha";
}

function syncSuggestedUsername(force = false) {
  if (sim.usernameInput.readOnly) return;
  const current = sim.usernameInput.value.trim();
  if (force || !current || Object.values(USERNAME_BY_ROLE).includes(current)) {
    sim.usernameInput.value = suggestedUsername();
  }
}

function activeUsername() {
  return sim.usernameInput.value.trim() || suggestedUsername();
}

function requestHeaders(extra = {}) {
  const sessionToken = activeSessionToken();
  return sessionToken
    ? { "X-JINX-Role": activeRole(), "X-JINX-Package": PACKAGE_NAME, "X-JINX-Session": sessionToken, ...extra }
    : { "X-JINX-Role": activeRole(), "X-JINX-Package": PACKAGE_NAME, ...extra };
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
  sim.apiStatus.classList.toggle("ok", ok);
  sim.apiStatus.classList.toggle("error", !ok);
  sim.apiStatusText.textContent = text;
}

function renderSession(sessionDoc, entitlements) {
  const session = sessionDoc.session || null;
  if (!session && activeSessionToken()) {
    localStorage.removeItem(SESSION_KEY);
  }
  document.querySelector(".eyebrow").textContent = entitlements.label || "SIM package";
  sim.sessionMode.textContent = session ? "Session active" : "Header role mode";
  sim.roleSelect.disabled = Boolean(session);
  sim.usernameInput.readOnly = Boolean(session);

  if (session) {
    const role = String((session.roles || [])[0] || activeRole());
    if (sim.roleSelect.querySelector(`option[value="${role}"]`)) {
      sim.roleSelect.value = role;
    }
    sim.usernameInput.value = session.username || activeUsername();
    sim.brainChatForm.elements.user_id.value = session.username || activeUsername();
    sim.sessionSummary.className = "list";
    sim.sessionSummary.innerHTML = `
      <article class="item advisory">
        <strong>${escapeHTML(session.display_name || session.username)}</strong>
        <span>${escapeHTML(role)} · package ${escapeHTML(session.package || PACKAGE_NAME)} · session ${escapeHTML(session.id || "unknown")}</span>
        <span>license ${entitlements.license_active ? "active" : "inactive"} · ${entitlements.simulation_only ? "simulation only" : "controlled adapter enabled"}</span>
      </article>
    `;
    return;
  }

  syncSuggestedUsername(true);
  sim.brainChatForm.elements.user_id.value = activeUsername();
  sim.sessionSummary.className = "list empty";
  sim.sessionSummary.textContent = entitlements.license_active
    ? `No active session. ${entitlements.label || "SIM package"} is running in local header mode.`
    : `${entitlements.label || "SIM package"} license is inactive.`;
}

function selectedScenario() {
  return library.find((scenario) => scenario.id === selectedScenarioId) || library[0] || null;
}

function renderMetrics(dashboard) {
  document.querySelector("#metric-library").textContent = dashboard.library_count || 0;
  document.querySelector("#metric-custom").textContent = dashboard.custom_scenario_count || 0;
  document.querySelector("#metric-runs").textContent = dashboard.run_count || 0;
  document.querySelector("#metric-mismatch").textContent = dashboard.mismatch_count || 0;
}

function renderLibrary(scenarios, control) {
  library = scenarios;
  selectedScenarioId = control.selected_scenario_id || selectedScenarioId || (scenarios[0] && scenarios[0].id) || "";
  document.querySelector("#library-count").textContent = scenarios.length;
  renderList(sim.libraryList, scenarios, "No simulation scenarios", (scenario) => {
    const isSelected = scenario.id === selectedScenarioId;
    const injectCount = (scenario.injects || []).length;
    return `
      <article class="item ${isSelected ? "recommendation" : "net"}">
        <strong>${escapeHTML(scenario.name)} · ${escapeHTML(scenario.source)}</strong>
        <span>${escapeHTML(scenario.summary)}</span>
        <span>injects ${escapeHTML(injectCount)} · duration ${escapeHTML(scenario.duration_seconds)}s · expected ${(scenario.expected_outputs || []).length}</span>
        <div class="review-row">
          <button type="button" data-scenario-action="select" data-scenario-id="${escapeHTML(scenario.id)}">Load</button>
          <button type="button" data-scenario-action="run" data-scenario-id="${escapeHTML(scenario.id)}">Run</button>
        </div>
      </article>
    `;
  });
}

function renderControl(control) {
  document.querySelector("#control-status").textContent = control.playback_state || "idle";
  sim.controlSummary.className = "list";
  sim.controlSummary.innerHTML = [
    `<article class="item advisory">`,
    `<strong>${escapeHTML(control.selected_scenario_name || "No scenario")} · ${escapeHTML(control.selected_scenario_source || "built_in")}</strong>`,
    `<span>clock ${escapeHTML(control.current_offset_seconds)}s / ${escapeHTML(control.duration_seconds)}s</span>`,
    `<span>current ${escapeHTML(control.current_frame ? control.current_frame.type : "none")} · next ${escapeHTML(control.next_frame ? control.next_frame.type : "none")}</span>`,
    `<span>last action ${escapeHTML(control.last_action || "bootstrap")} · latest run ${escapeHTML(control.latest_run_id || "none")}</span>`,
    `</article>`,
  ].join("");
}

function renderTimeline(scenario) {
  const injects = (scenario && scenario.injects) || [];
  document.querySelector("#timeline-count").textContent = injects.length;
  renderList(sim.timelineList, injects, "No inject timeline loaded", (inject) => `
    <article class="item isr">
      <strong>T+${escapeHTML(inject.offset_seconds)} · ${escapeHTML(inject.type)}</strong>
      <span>${escapeHTML(inject.summary || inject.name || inject.mission_statement || inject.report_text || inject.report_type || inject.feed_name || "Synthetic inject")}</span>
    </article>
  `);
}

function renderLatestResult(run) {
  document.querySelector("#latest-result-status").textContent = run ? (run.result_state || "matched") : "none";
  if (!run) {
    sim.latestResultCard.className = "list empty";
    sim.latestResultCard.textContent = "No simulation run yet";
    return;
  }
  sim.latestResultCard.className = "list";
  sim.latestResultCard.innerHTML = `
    <article class="item mission-impact">
      <strong>${escapeHTML(run.scenario_name)} · ${escapeHTML(run.result_state || "matched")}</strong>
      <span>expected ${(run.expected_outputs || []).length} · actual ${(run.actual_outputs || []).length} · drift ${escapeHTML(run.confidence_drift)}</span>
      <span>brain answer ${escapeHTML(run.brain_answer_id || "none")} · status ${escapeHTML(run.status || "completed")}</span>
    </article>
  `;
}

function renderRuns(runs) {
  document.querySelector("#run-count").textContent = runs.length;
  renderList(sim.runList, runs.slice(-8).reverse(), "No simulation runs", (run) => `
    <article class="item ${run.result_state === "matched" ? "advisory" : "conflict"}">
      <strong>${escapeHTML(run.scenario_name)} · ${escapeHTML(run.result_state || "matched")}</strong>
      <span>expected ${(run.expected_outputs || []).length} · actual ${(run.actual_outputs || []).length} · synthetic ${run.synthetic ? "yes" : "no"}</span>
      <span>${escapeHTML(run.timestamp || "")}</span>
    </article>
  `);
}

function renderComparison(run) {
  if (!run) {
    document.querySelector("#comparison-count").textContent = "0";
    sim.comparisonList.className = "list empty";
    sim.comparisonList.textContent = "No comparison packet yet";
    return;
  }
  const records = [
    { title: "Expected outputs", detail: (run.expected_outputs || []).join(", ") || "none" },
    { title: "Actual outputs", detail: (run.actual_outputs || []).join(", ") || "none" },
    { title: "Missing outputs", detail: (run.missing_outputs || []).join(", ") || "none" },
    { title: "Unexpected outputs", detail: (run.unexpected_outputs || []).join(", ") || "none" },
  ];
  document.querySelector("#comparison-count").textContent = records.length;
  renderList(sim.comparisonList, records, "No comparison packet yet", (record) => `
    <article class="item ${record.title.includes("Missing") || record.title.includes("Unexpected") ? "conflict" : "advisory"}">
      <strong>${escapeHTML(record.title)}</strong>
      <span>${escapeHTML(record.detail)}</span>
    </article>
  `);
}

function renderBrain(messages) {
  document.querySelector("#brain-chat-count").textContent = messages.length;
  renderList(sim.brainChatList, messages.slice(-6).reverse(), "No Brain chat yet", (message) => `
    <article class="item brain-chat">
      <strong>${escapeHTML(message.answer.confidence_band)} · Core reachback ${message.answer.core_reachback_used ? "used" : "not used"}</strong>
      <span>Q: ${escapeHTML(message.question.text)}</span>
      <span>${escapeHTML(message.answer.answer_text)}</span>
    </article>
  `);
}

async function refresh() {
  try {
    const [health, entitlements, sessionDoc, dashboardDoc, libraryDoc, controlDoc, runsDoc, brainDoc] = await Promise.all([
      getJSON("/api/health"),
      getJSON("/api/entitlements"),
      getJSON("/api/auth/session"),
      getJSON("/api/sim/dashboard"),
      getJSON("/api/sim/library"),
      getJSON("/api/sim/control"),
      getJSON("/api/sim/runs"),
      getJSON("/api/brain/chat-messages"),
    ]);
    const dashboard = dashboardDoc.simulation || {};
    const scenarios = libraryDoc.simulation_scenarios || [];
    const control = controlDoc.simulation_control || {};
    const runs = runsDoc.simulation_runs || [];
    const latestRun = dashboard.latest_run || runs[runs.length - 1] || null;
    renderSession(sessionDoc, entitlements);
    renderMetrics(dashboard);
    renderLibrary(scenarios, control);
    renderControl(control);
    renderTimeline(selectedScenario());
    renderLatestResult(latestRun);
    renderRuns(runs);
    renderComparison(latestRun);
    renderBrain(brainDoc.messages || []);
    setStatus(true, `${health.service} API online`);
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

sim.libraryList.addEventListener("click", async (event) => {
  const target = event.target.closest("button[data-scenario-action]");
  if (!target) return;
  const scenarioId = target.dataset.scenarioId || "";
  selectedScenarioId = scenarioId;
  if (target.dataset.scenarioAction === "select") {
    await postJSON("/api/sim/control", { action: "select", scenario_id: scenarioId });
  } else if (target.dataset.scenarioAction === "run") {
    await postJSON("/api/sim/run", { scenario_id: scenarioId });
  }
  await refresh();
});

document.querySelectorAll("button[data-control-action]").forEach((button) => {
  button.addEventListener("click", async () => {
    await postJSON("/api/sim/control", {
      action: button.dataset.controlAction,
      scenario_id: selectedScenarioId,
    });
    await refresh();
  });
});

document.querySelectorAll("button[data-run-scenario]").forEach((button) => {
  button.addEventListener("click", async () => {
    await postJSON("/api/sim/run", { scenario_id: selectedScenarioId });
    await refresh();
  });
});

sim.scenarioForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const response = await postJSON("/api/sim/scenarios", Object.fromEntries(new FormData(sim.scenarioForm).entries()));
  selectedScenarioId = response.simulation_scenario.id;
  await postJSON("/api/sim/control", { action: "select", scenario_id: selectedScenarioId });
  await refresh();
});

sim.scrubForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(sim.scrubForm).entries());
  payload.action = "scrub";
  payload.scenario_id = selectedScenarioId;
  await postJSON("/api/sim/control", payload);
  await refresh();
});

sim.brainChatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(sim.brainChatForm).entries());
  data.role = activeRole();
  await postJSON("/api/brain/chat", data);
  await refresh();
});

sim.sessionButton.addEventListener("click", async () => {
  try {
    await connectSession();
    await refresh();
  } catch (error) {
    setStatus(false, error.message || "Session denied");
  }
});

sim.clearSessionButton.addEventListener("click", async () => {
  await clearSession();
  syncSuggestedUsername(true);
  await refresh();
});

sim.refreshButton.addEventListener("click", refresh);
sim.roleSelect.addEventListener("change", async () => {
  syncSuggestedUsername(true);
  await refresh();
});

syncSuggestedUsername(true);
refresh();
