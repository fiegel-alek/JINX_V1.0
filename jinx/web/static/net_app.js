const net = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
  roleSelect: document.querySelector("#role-select"),
  usernameInput: document.querySelector("#username-input"),
  sessionButton: document.querySelector("#session-button"),
  clearSessionButton: document.querySelector("#clear-session-button"),
  sessionSummary: document.querySelector("#session-summary"),
  sessionMode: document.querySelector("#session-mode"),
  planList: document.querySelector("#net-plan-list"),
  issueList: document.querySelector("#net-issue-list"),
  validationList: document.querySelector("#net-validation-list"),
  advisoryList: document.querySelector("#net-advisory-list"),
  brainChatList: document.querySelector("#brain-chat-list"),
  planForm: document.querySelector("#net-plan-form"),
  parserForm: document.querySelector("#net-parser-form"),
  brainChatForm: document.querySelector("#brain-chat-form"),
  refreshButton: document.querySelector("#refresh-button"),
};

const SESSION_KEY = "jinx-net-session-token";
const PACKAGE_NAME = "net";
const USERNAME_BY_ROLE = {
  network_manager: "net-manager-alpha",
  auditor: "auditor-alpha",
  system_administrator: "systemadministrator",
};

function activeRole() {
  return net.roleSelect.value;
}

function activeSessionToken() {
  return localStorage.getItem(SESSION_KEY) || "";
}

function suggestedUsername() {
  return USERNAME_BY_ROLE[activeRole()] || "net-manager-alpha";
}

function syncSuggestedUsername(force = false) {
  if (net.usernameInput.readOnly) return;
  const current = net.usernameInput.value.trim();
  if (force || !current || Object.values(USERNAME_BY_ROLE).includes(current)) {
    net.usernameInput.value = suggestedUsername();
  }
}

function activeUsername() {
  return net.usernameInput.value.trim() || suggestedUsername();
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
  net.apiStatus.classList.toggle("ok", ok);
  net.apiStatus.classList.toggle("error", !ok);
  net.apiStatusText.textContent = text;
}

function renderSession(sessionDoc, entitlements) {
  const session = sessionDoc.session || null;
  if (!session && activeSessionToken()) {
    localStorage.removeItem(SESSION_KEY);
  }
  document.querySelector(".eyebrow").textContent = entitlements.label || "NET package";
  net.sessionMode.textContent = session ? "Session active" : "Header role mode";
  net.roleSelect.disabled = Boolean(session);
  net.usernameInput.readOnly = Boolean(session);

  if (session) {
    const role = String((session.roles || [])[0] || activeRole());
    if (net.roleSelect.querySelector(`option[value="${role}"]`)) {
      net.roleSelect.value = role;
    }
    net.usernameInput.value = session.username || activeUsername();
    net.brainChatForm.elements.user_id.value = session.username || activeUsername();
    net.sessionSummary.className = "list";
    net.sessionSummary.innerHTML = `
      <article class="item advisory">
        <strong>${escapeHTML(session.display_name || session.username)}</strong>
        <span>${escapeHTML(role)} · package ${escapeHTML(session.package || PACKAGE_NAME)} · session ${escapeHTML(session.id || "unknown")}</span>
        <span>license ${entitlements.license_active ? "active" : "inactive"} · ${entitlements.simulation_only ? "simulation only" : "controlled adapter enabled"}</span>
      </article>
    `;
    return;
  }

  syncSuggestedUsername(true);
  net.brainChatForm.elements.user_id.value = activeUsername();
  net.sessionSummary.className = "list empty";
  net.sessionSummary.textContent = entitlements.license_active
    ? `No active session. ${entitlements.label || "NET package"} is running in local header mode.`
    : `${entitlements.label || "NET package"} license is inactive.`;
}

function renderPlans(plans) {
  document.querySelector("#metric-plans").textContent = plans.length;
  document.querySelector("#net-plan-count").textContent = plans.length;
  renderList(net.planList, plans.slice(-8).reverse(), "No NET plans", (plan) => `
    <article class="item net">
      <strong>${escapeHTML(plan.name)} · ${escapeHTML(plan.source_format)}</strong>
      <span>nodes ${escapeHTML((plan.nodes || []).length)} · timeslots ${escapeHTML((plan.timeslots || []).length)} · LOS ${escapeHTML((plan.los_links || []).length)}</span>
      <span>${escapeHTML(plan.data_mode)} · confidence ${escapeHTML(plan.confidence)}</span>
    </article>
  `);
}

function renderIssues(issues) {
  document.querySelector("#metric-issues").textContent = issues.length;
  document.querySelector("#net-issue-count").textContent = issues.length;
  renderList(net.issueList, issues.slice(-10).reverse(), "No NET issues", (issue) => `
    <article class="item net conflict">
      <strong>${escapeHTML(issue.issue_type)} · ${escapeHTML(issue.severity)}</strong>
      <span>${escapeHTML(issue.summary)}</span>
      <span>nodes: ${escapeHTML((issue.affected_nodes || []).join(", ") || "none")} · delivered ${escapeHTML(issue.delivered_to_core)}</span>
      <span>review: ${escapeHTML(issue.recommended_review_role)}</span>
    </article>
  `);
}

function renderValidationRuns(runs) {
  document.querySelector("#metric-validations").textContent = runs.length;
  document.querySelector("#net-validation-count").textContent = runs.length;
  renderList(net.validationList, runs.slice(-8).reverse(), "No validation runs", (run) => `
    <article class="item net">
      <strong>${escapeHTML(run.id)}</strong>
      <span>${escapeHTML(run.summary)}</span>
      <span>plan ${escapeHTML(run.plan_id)} · issues ${escapeHTML((run.issue_ids || []).length)} · confidence ${escapeHTML(run.confidence)}</span>
    </article>
  `);
}

function renderAdvisories(advisories) {
  document.querySelector("#metric-advisories").textContent = advisories.length;
  document.querySelector("#net-advisory-count").textContent = advisories.length;
  renderList(net.advisoryList, advisories.slice(-10).reverse(), "No NET advisories", (advisory) => `
    <article class="item net recommendation">
      <strong>${escapeHTML(advisory.recommended_review_role)} · confidence ${escapeHTML(advisory.confidence)}</strong>
      <span>${escapeHTML(advisory.summary)}</span>
      <span>${advisory.required_human_review ? "human review required" : "review missing"} · issue ${escapeHTML(advisory.issue_id)}</span>
    </article>
  `);
}

function renderBrain(messages) {
  document.querySelector("#brain-chat-count").textContent = messages.length;
  renderList(net.brainChatList, messages.slice(-6).reverse(), "No Brain chat yet", (message) => `
    <article class="item brain-chat">
      <strong>${escapeHTML(message.answer.confidence_band)} · Core reachback ${message.answer.core_reachback_used ? "used" : "not used"}</strong>
      <span>Q: ${escapeHTML(message.question.text)}</span>
      <span>${escapeHTML(message.answer.answer_text)}</span>
    </article>
  `);
}

async function refresh() {
  try {
    const [health, entitlements, sessionDoc, plans, issues, validations, advisories, brain] = await Promise.all([
      getJSON("/api/health"),
      getJSON("/api/entitlements"),
      getJSON("/api/auth/session"),
      getJSON("/api/net/plans"),
      getJSON("/api/net/issues"),
      getJSON("/api/net/validation-runs"),
      getJSON("/api/net/advisories"),
      getJSON("/api/brain/chat-messages"),
    ]);
    renderSession(sessionDoc, entitlements);
    setStatus(true, `${health.service} API online`);
    renderPlans(plans.network_plans || []);
    renderIssues(issues.network_issues || []);
    renderValidationRuns(validations.network_validation_runs || []);
    renderAdvisories(advisories.network_advisories || []);
    renderBrain(brain.messages || []);
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

async function submitPlan(form) {
  await postJSON("/api/net/plans", Object.fromEntries(new FormData(form).entries()));
  await refresh();
}

net.planForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await submitPlan(net.planForm);
});

net.parserForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await submitPlan(net.parserForm);
});

net.brainChatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(net.brainChatForm).entries());
  data.role = activeRole();
  await postJSON("/api/brain/chat", data);
  await refresh();
});

net.sessionButton.addEventListener("click", async () => {
  try {
    await connectSession();
    await refresh();
  } catch (error) {
    setStatus(false, error.message || "Session denied");
  }
});

net.clearSessionButton.addEventListener("click", async () => {
  await clearSession();
  syncSuggestedUsername(true);
  await refresh();
});

net.refreshButton.addEventListener("click", refresh);
net.roleSelect.addEventListener("change", async () => {
  syncSuggestedUsername(true);
  await refresh();
});

syncSuggestedUsername(true);
refresh();
