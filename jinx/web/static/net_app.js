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
  focusKind: document.querySelector("#net-focus-kind"),
  focusCard: document.querySelector("#net-focus-card"),
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

function readableLabel(value) {
  return String(value || "unknown").replaceAll("_", " ");
}

function lastItem(records) {
  return records && records.length ? records[records.length - 1] : null;
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

function renderFocusCard(packet) {
  if (!packet) {
    net.focusKind.textContent = "Awaiting NET review";
    net.focusCard.className = "list focus-card empty";
    net.focusCard.textContent = "No NET focus yet";
    return;
  }
  net.focusKind.textContent = packet.kind;
  net.focusCard.className = "list focus-card";
  net.focusCard.innerHTML = `
    <article class="item ${escapeHTML(packet.tone || "")}">
      <strong>${escapeHTML(packet.title)}</strong>
      <span class="item-caption">${escapeHTML(packet.caption || "")}</span>
      <span>${escapeHTML(packet.summary || "")}</span>
      ${pairGrid(packet.pairs || [])}
      ${packet.callout ? `
        <div class="item-callout">
          <strong>${escapeHTML(packet.calloutTitle || "Manager next step")}</strong>
          <span>${escapeHTML(packet.callout)}</span>
        </div>
      ` : ""}
    </article>
  `;
}

function renderNetFocus(snapshot) {
  const issue = lastItem(snapshot.issues || []);
  if (issue) {
    renderFocusCard({
      kind: "Issue review",
      tone: "conflict",
      title: readableLabel(issue.issue_type),
      caption: `Severity ${issue.severity || "unknown"} · ${issue.recommended_review_role || "human review"} needed`,
      summary: issue.summary || "Network issue awaiting review.",
      pairs: [
        ["Nodes", (issue.affected_nodes || []).join(", ") || "none"],
        ["Confidence", issue.confidence],
        ["Delivered", issue.delivered_to_core ? "Yes" : "Pending"],
      ],
      calloutTitle: "First review step",
      callout: (issue.recommended_human_actions || [])[0]
        || "Review the synthetic plan before changing communications assumptions.",
    });
    return;
  }

  const advisory = lastItem(snapshot.advisories || []);
  if (advisory) {
    renderFocusCard({
      kind: "Manager advisory",
      tone: "recommendation",
      title: advisory.recommended_review_role || "network manager",
      caption: "Advisory path returned to the NET desk",
      summary: advisory.summary || "NET advisory available.",
      pairs: [
        ["Confidence", advisory.confidence],
        ["Issue", advisory.issue_id],
        ["Human review", advisory.required_human_review ? "Required" : "Optional"],
      ],
      callout: "Use the advisory to guide review, not to modify live network systems.",
    });
    return;
  }

  const run = lastItem(snapshot.validations || []);
  if (run) {
    renderFocusCard({
      kind: "Validation run",
      tone: "net",
      title: run.plan_id || run.id || "validation run",
      caption: "Latest parser or plan validation result",
      summary: run.summary || "Validation history is available for review.",
      pairs: [
        ["Issues", (run.issue_ids || []).length],
        ["Confidence", run.confidence],
        ["Run id", run.id],
      ],
      callout: "Open the related issue list before reusing the plan in a broader package workflow.",
    });
    return;
  }

  const plan = lastItem(snapshot.plans || []);
  if (plan) {
    renderFocusCard({
      kind: "Plan picture",
      tone: "net",
      title: plan.name || "network plan",
      caption: `Synthetic ${plan.source_format || "network planning"} record`,
      summary: "Plan structure is loaded and ready for human validation.",
      pairs: [
        ["Nodes", (plan.nodes || []).length],
        ["Timeslots", (plan.timeslots || []).length],
        ["LOS links", (plan.los_links || []).length],
      ],
      callout: "Validate timeslots and LOS before treating the plan as reusable knowledge.",
    });
    return;
  }

  const brain = lastItem(snapshot.brain || []);
  if (brain) {
    renderFocusCard({
      kind: "BRAIN reachback",
      tone: "brain-chat",
      title: `${brain.answer.confidence_band || "limited"} confidence guidance`,
      caption: "Troubleshooting and doctrine support for the NET desk",
      summary: brain.answer.answer_text || "BRAIN guidance available.",
      pairs: [
        ["Reachback", brain.answer.core_reachback_used ? "Used" : "Not used"],
        ["References", (brain.answer.references || []).join(", ") || "none"],
      ],
      callout: "Use BRAIN to frame the review, then keep the network change decision with the human chain.",
    });
    return;
  }

  renderFocusCard(null);
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
      <span class="item-caption">Synthetic network plan record ready for validation</span>
      ${pairGrid([
        ["Nodes", (plan.nodes || []).length],
        ["Timeslots", (plan.timeslots || []).length],
        ["LOS links", (plan.los_links || []).length],
        ["Mode", plan.data_mode],
        ["Confidence", plan.confidence],
      ])}
    </article>
  `);
}

function renderIssues(issues) {
  document.querySelector("#metric-issues").textContent = issues.length;
  document.querySelector("#net-issue-count").textContent = issues.length;
  renderList(net.issueList, issues.slice(-10).reverse(), "No NET issues", (issue) => `
    <article class="item net conflict">
      <strong>${escapeHTML(issue.issue_type)} · ${escapeHTML(issue.severity)}</strong>
      <span class="item-caption">Human review stays with the network manager</span>
      <span>${escapeHTML(issue.summary)}</span>
      ${pairGrid([
        ["Nodes", (issue.affected_nodes || []).join(", ") || "none"],
        ["Delivered", issue.delivered_to_core],
        ["Review", issue.recommended_review_role],
      ])}
      <div class="item-callout">
        <strong>First review step</strong>
        <span>${escapeHTML((issue.recommended_human_actions || [])[0] || "Review the synthetic plan and confirm the problem before changing any assumption.")}</span>
      </div>
    </article>
  `);
}

function renderValidationRuns(runs) {
  document.querySelector("#metric-validations").textContent = runs.length;
  document.querySelector("#net-validation-count").textContent = runs.length;
  renderList(net.validationList, runs.slice(-8).reverse(), "No validation runs", (run) => `
    <article class="item net">
      <strong>${escapeHTML(run.id)}</strong>
      <span class="item-caption">Validation history for parser or plan review</span>
      <span>${escapeHTML(run.summary)}</span>
      ${pairGrid([
        ["Plan", run.plan_id],
        ["Issues", (run.issue_ids || []).length],
        ["Confidence", run.confidence],
      ])}
    </article>
  `);
}

function renderAdvisories(advisories) {
  document.querySelector("#metric-advisories").textContent = advisories.length;
  document.querySelector("#net-advisory-count").textContent = advisories.length;
  renderList(net.advisoryList, advisories.slice(-10).reverse(), "No NET advisories", (advisory) => `
    <article class="item net recommendation">
      <strong>${escapeHTML(advisory.recommended_review_role)}</strong>
      <span class="item-caption">Advisory returned to the NET desk</span>
      <span>${escapeHTML(advisory.summary)}</span>
      ${pairGrid([
        ["Confidence", advisory.confidence],
        ["Human review", advisory.required_human_review ? "Required" : "Missing"],
        ["Issue", advisory.issue_id],
      ])}
      <div class="item-callout">
        <strong>Guardrail</strong>
        <span>Use this packet to guide human review. Do not treat it as live network control authority.</span>
      </div>
    </article>
  `);
}

function renderBrain(messages) {
  document.querySelector("#brain-chat-count").textContent = messages.length;
  renderList(net.brainChatList, messages.slice(-6).reverse(), "No Brain chat yet", (message) => `
    <article class="item brain-chat">
      <strong>${escapeHTML(message.answer.confidence_band)} confidence</strong>
      <span class="item-caption">Troubleshooting and doctrine support for NET review</span>
      <span>Q: ${escapeHTML(message.question.text)}</span>
      <span>${escapeHTML(message.answer.answer_text)}</span>
      ${pairGrid([
        ["Reachback", message.answer.core_reachback_used ? "Used" : "Not used"],
        ["References", (message.answer.references || []).join(", ") || "none"],
      ])}
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
    renderNetFocus({
      plans: plans.network_plans || [],
      issues: issues.network_issues || [],
      validations: validations.network_validation_runs || [],
      advisories: advisories.network_advisories || [],
      brain: brain.messages || [],
    });
  } catch (error) {
    setStatus(false, error.message || "API offline");
    renderFocusCard(null);
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
