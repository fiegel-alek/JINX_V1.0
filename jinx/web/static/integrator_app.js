const integrator = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
  roleSelect: document.querySelector("#role-select"),
  usernameInput: document.querySelector("#username-input"),
  sessionButton: document.querySelector("#session-button"),
  clearSessionButton: document.querySelector("#clear-session-button"),
  sessionSummary: document.querySelector("#session-summary"),
  sessionMode: document.querySelector("#session-mode"),
  familyList: document.querySelector("#family-list"),
  messageList: document.querySelector("#message-list"),
  routeList: document.querySelector("#route-list"),
  parserRunList: document.querySelector("#parser-run-list"),
  brainChatList: document.querySelector("#brain-chat-list"),
  focusKind: document.querySelector("#integrator-focus-kind"),
  focusCard: document.querySelector("#integrator-focus-card"),
  intakeForm: document.querySelector("#integrator-form"),
  messageFamilySelect: document.querySelector("#message-family-select"),
  messageText: document.querySelector("#message-text"),
  brainChatForm: document.querySelector("#brain-chat-form"),
  refreshButton: document.querySelector("#refresh-button"),
};

const SESSION_KEY = "jinx-integrator-session-token";
const PACKAGE_NAME = "integrator";
const USERNAME_BY_ROLE = {
  integrator_operator: "integrator-alpha",
  auditor: "auditor-alpha",
  system_administrator: "systemadministrator",
};

const TEMPLATE_BY_FAMILY = {
  vmf: `message_type: vmf spot report
originator: unit-alpha
recipient: review-cell
summary: Synthetic location and status update for bounded internal review.
transport: fabric-shadow
precedence: routine
location: grid-alpha
tags: status,position`,
  "k-series": `message_type: k-series network status
originator: relay-cell
recipient: communications-review
summary: Synthetic network timing and link status note for bounded communications review.
transport: fabric-shadow
precedence: priority
location: relay-grid
tags: communications,timing`,
  "j-series": `message_type: j-series track update
originator: unit-bravo
recipient: review-cell
summary: Synthetic track and communications status update for bounded internal review.
transport: fabric-shadow
precedence: routine
location: grid-bravo
tags: communications,track`,
  usmtf: `message_type: usmtf summary
originator: command-post-alpha
recipient: planner-review
summary: Synthetic formatted message summary preserved for human review and audit.
transport: fabric-shadow
precedence: routine
location: route-alpha
tags: planning,review`,
};

function activeRole() {
  return integrator.roleSelect.value;
}

function activeSessionToken() {
  return localStorage.getItem(SESSION_KEY) || "";
}

function suggestedUsername() {
  return USERNAME_BY_ROLE[activeRole()] || "integrator-alpha";
}

function syncSuggestedUsername(force = false) {
  if (integrator.usernameInput.readOnly) return;
  const current = integrator.usernameInput.value.trim();
  if (force || !current || Object.values(USERNAME_BY_ROLE).includes(current)) {
    integrator.usernameInput.value = suggestedUsername();
  }
}

function activeUsername() {
  return integrator.usernameInput.value.trim() || suggestedUsername();
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
  integrator.apiStatus.classList.toggle("ok", ok);
  integrator.apiStatus.classList.toggle("error", !ok);
  integrator.apiStatusText.textContent = text;
}

function renderSession(sessionDoc, entitlements) {
  const session = sessionDoc.session || null;
  if (!session && activeSessionToken()) {
    localStorage.removeItem(SESSION_KEY);
  }
  document.querySelector(".eyebrow").textContent = entitlements.label || "Integrator package";
  integrator.sessionMode.textContent = session ? "Session active" : "Header role mode";
  integrator.roleSelect.disabled = Boolean(session);
  integrator.usernameInput.readOnly = Boolean(session);

  if (session) {
    const role = String((session.roles || [])[0] || activeRole());
    if (integrator.roleSelect.querySelector(`option[value="${role}"]`)) {
      integrator.roleSelect.value = role;
    }
    integrator.usernameInput.value = session.username || activeUsername();
    integrator.brainChatForm.elements.user_id.value = session.username || activeUsername();
    integrator.sessionSummary.className = "list";
    integrator.sessionSummary.innerHTML = `
      <article class="item advisory">
        <strong>${escapeHTML(session.display_name || session.username)}</strong>
        <span>${escapeHTML(role)} · package ${escapeHTML(session.package || PACKAGE_NAME)} · session ${escapeHTML(session.id || "unknown")}</span>
        <span>license ${entitlements.license_active ? "active" : "inactive"} · ${entitlements.simulation_only ? "simulation only" : "controlled adapter enabled"}</span>
      </article>
    `;
    return;
  }

  syncSuggestedUsername(true);
  integrator.brainChatForm.elements.user_id.value = activeUsername();
  integrator.sessionSummary.className = "list empty";
  integrator.sessionSummary.textContent = entitlements.license_active
    ? `No active session. ${entitlements.label || "Integrator package"} is running in local header mode.`
    : `${entitlements.label || "Integrator package"} license is inactive.`;
}

function renderFamilies(families) {
  document.querySelector("#metric-families").textContent = families.length;
  document.querySelector("#family-count").textContent = families.length;
  renderList(integrator.familyList, families, "No family profiles", (family) => `
    <article class="item net">
      <strong>${escapeHTML(family.family)}</strong>
      <span class="item-caption">Bounded profile for normalized intake and internal routing</span>
      <span>${escapeHTML(family.summary)}</span>
      ${pairGrid([
        ["Targets", (family.route_targets || []).join(", ") || "none"],
        ["Required fields", (family.required_fields || []).join(", ") || "none"],
      ])}
      <div class="item-callout">
        <strong>Guardrail</strong>
        <span>${escapeHTML((family.restrictions || [])[0] || "Synthetic or explicitly authorized intake only.")}</span>
      </div>
    </article>
  `);
}

function renderMessages(messages) {
  document.querySelector("#metric-messages").textContent = messages.length;
  document.querySelector("#message-count").textContent = messages.length;
  renderList(integrator.messageList, messages.slice(-8).reverse(), "No normalized messages", (message) => `
    <article class="item advisory">
      <strong>${escapeHTML(message.message_family)} · ${escapeHTML(message.message_type)}</strong>
      <span class="item-caption">Bounded message-family intake record</span>
      <span>${escapeHTML(message.summary)}</span>
      ${pairGrid([
        ["Originator", message.originator],
        ["Recipient", message.recipient],
        ["Transport", message.transport],
        ["Targets", (message.route_targets || []).join(", ") || "none"],
      ])}
    </article>
  `);
}

function renderRoutes(routes) {
  document.querySelector("#metric-routes").textContent = routes.length;
  document.querySelector("#route-count").textContent = routes.length;
  renderList(integrator.routeList, routes.slice(-12).reverse(), "No integrator routes", (route) => `
    <article class="item ${route.status === "denied" ? "conflict" : "recommendation"}">
      <strong>${escapeHTML(route.destination)} · ${escapeHTML(route.status)}</strong>
      <span class="item-caption">Internal FABRIC route created by the Integrator</span>
      <span>${escapeHTML(route.policy_reason)}</span>
      ${pairGrid([
        ["Schema", route.payload_schema],
        ["Topic", route.topic],
        ["Redactions", (route.redacted_fields || []).join(", ") || "none"],
      ])}
    </article>
  `);
}

function renderParserRuns(runs) {
  document.querySelector("#metric-parser-runs").textContent = runs.length;
  document.querySelector("#parser-run-count").textContent = runs.length;
  renderList(integrator.parserRunList, runs.slice(-8).reverse(), "No parser runs", (run) => `
    <article class="item">
      <strong>${escapeHTML(run.message_family)} · ${escapeHTML(run.id)}</strong>
      <span class="item-caption">Parser and normalization audit for this intake record</span>
      ${pairGrid([
        ["Targets", (run.route_targets || []).join(", ") || "none"],
        ["Keys", (run.normalized_keys || []).join(", ") || "none"],
      ])}
      <div class="item-callout">
        <strong>Validation</strong>
        <span>${escapeHTML((run.validation_notes || []).join(" | ") || "No validation notes.")}</span>
      </div>
    </article>
  `);
}

function renderBrain(messages) {
  document.querySelector("#brain-chat-count").textContent = messages.length;
  renderList(integrator.brainChatList, messages.slice(-6).reverse(), "No Brain chat yet", (message) => `
    <article class="item brain-chat">
      <strong>${escapeHTML(message.answer.confidence_band)} confidence</strong>
      <span class="item-caption">Doctrine and review support for the intake desk</span>
      <span>Q: ${escapeHTML(message.question.text)}</span>
      <span>${escapeHTML(message.answer.answer_text)}</span>
      ${pairGrid([
        ["Reachback", message.answer.core_reachback_used ? "Used" : "Not used"],
        ["References", (message.answer.references || []).join(", ") || "none"],
      ])}
    </article>
  `);
}

function renderFocus(messages, routes, runs) {
  const message = messages.length ? messages[messages.length - 1] : null;
  const route = routes.length ? routes[routes.length - 1] : null;
  const run = runs.length ? runs[runs.length - 1] : null;
  if (!message) {
    integrator.focusKind.textContent = "Awaiting message intake";
    integrator.focusCard.className = "list focus-card empty";
    integrator.focusCard.textContent = "No Integrator focus yet";
    return;
  }
  integrator.focusKind.textContent = route ? route.status : "message normalized";
  integrator.focusCard.className = "list focus-card";
  integrator.focusCard.innerHTML = `
    <article class="item ${route && route.status === "denied" ? "conflict" : "recommendation"}">
      <strong>${escapeHTML(message.message_family)} · ${escapeHTML(message.message_type)}</strong>
      <span class="item-caption">Latest normalized intake packet</span>
      <span>${escapeHTML(message.summary)}</span>
      ${pairGrid([
        ["Targets", (message.route_targets || []).join(", ") || "none"],
        ["Filter profile", message.filter_profile],
        ["Transport", message.transport],
        ["Authority state", message.authority_state],
      ])}
      <div class="item-callout">
        <strong>Next review step</strong>
        <span>${escapeHTML(
          route
            ? `Confirm ${route.destination} is the right licensed destination and review policy result ${route.status}.`
            : run && run.validation_notes && run.validation_notes.length
              ? run.validation_notes[0]
              : "Review the normalized packet before using it in any downstream assumption."
        )}</span>
      </div>
    </article>
  `;
}

function syncTemplate(force = false) {
  const family = integrator.messageFamilySelect.value;
  const template = TEMPLATE_BY_FAMILY[family] || TEMPLATE_BY_FAMILY.vmf;
  if (force || !integrator.messageText.value.trim() || Object.values(TEMPLATE_BY_FAMILY).includes(integrator.messageText.value.trim())) {
    integrator.messageText.value = template;
  }
}

async function refresh() {
  try {
    const [health, entitlements, sessionDoc, familiesDoc, messagesDoc, routesDoc, parserRunsDoc, brainDoc] = await Promise.all([
      getJSON("/api/health"),
      getJSON("/api/entitlements"),
      getJSON("/api/auth/session"),
      getJSON("/api/integrator/families"),
      getJSON("/api/integrator/messages"),
      getJSON("/api/integrator/routes"),
      getJSON("/api/integrator/parser-runs"),
      getJSON("/api/brain/chat-messages"),
    ]);
    const families = familiesDoc.message_families || [];
    const messages = messagesDoc.integrator_messages || [];
    const routes = routesDoc.integrator_routes || [];
    const runs = parserRunsDoc.integrator_parser_runs || [];
    renderSession(sessionDoc, entitlements);
    renderFamilies(families);
    renderMessages(messages);
    renderRoutes(routes);
    renderParserRuns(runs);
    renderBrain(brainDoc.messages || []);
    renderFocus(messages, routes, runs);
    setStatus(true, `${health.service} API online`);
  } catch (error) {
    setStatus(false, error.message || "API offline");
    renderFocus([], [], []);
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

integrator.intakeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await postJSON("/api/integrator/messages", Object.fromEntries(new FormData(integrator.intakeForm).entries()));
  await refresh();
});

integrator.brainChatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(integrator.brainChatForm).entries());
  data.role = activeRole();
  await postJSON("/api/brain/chat", data);
  await refresh();
});

integrator.sessionButton.addEventListener("click", async () => {
  try {
    await connectSession();
    await refresh();
  } catch (error) {
    setStatus(false, error.message || "Session denied");
  }
});

integrator.clearSessionButton.addEventListener("click", async () => {
  await clearSession();
  syncSuggestedUsername(true);
  await refresh();
});

integrator.refreshButton.addEventListener("click", refresh);
integrator.roleSelect.addEventListener("change", async () => {
  syncSuggestedUsername(true);
  await refresh();
});
integrator.messageFamilySelect.addEventListener("change", () => {
  syncTemplate(true);
});

syncSuggestedUsername(true);
syncTemplate(true);
refresh();
