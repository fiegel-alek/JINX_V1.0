const net = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
  roleSelect: document.querySelector("#role-select"),
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

let entitlementProfile = null;

function activeRole() {
  return net.roleSelect.value;
}

function requestHeaders(extra = {}) {
  return { "X-JINX-Role": activeRole(), "X-JINX-Package": "net", ...extra };
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

function setStatus(ok, text) {
  net.apiStatus.classList.toggle("ok", ok);
  net.apiStatus.classList.toggle("error", !ok);
  net.apiStatusText.textContent = text;
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

function renderEntitlements(entitlements) {
  entitlementProfile = entitlements;
  document.querySelector(".eyebrow").textContent = entitlements.label || "NET package";
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
    const [health, entitlements, plans, issues, validations, advisories, brain] = await Promise.all([
      getJSON("/api/health"),
      getJSON("/api/entitlements"),
      getJSON("/api/net/plans"),
      getJSON("/api/net/issues"),
      getJSON("/api/net/validation-runs"),
      getJSON("/api/net/advisories"),
      getJSON("/api/brain/chat-messages"),
    ]);
    setStatus(true, `${health.service} API online`);
    renderEntitlements(entitlements);
    renderPlans(plans.network_plans || []);
    renderIssues(issues.network_issues || []);
    renderValidationRuns(validations.network_validation_runs || []);
    renderAdvisories(advisories.network_advisories || []);
    renderBrain(brain.messages || []);
  } catch (error) {
    setStatus(false, "API offline");
  }
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

net.refreshButton.addEventListener("click", refresh);
net.roleSelect.addEventListener("change", refresh);
refresh();
