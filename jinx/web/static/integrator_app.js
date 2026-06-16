const integrator = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
  roleSelect: document.querySelector("#role-select"),
  usernameInput: document.querySelector("#username-input"),
  sessionButton: document.querySelector("#session-button"),
  clearSessionButton: document.querySelector("#clear-session-button"),
  sessionSummary: document.querySelector("#session-summary"),
  sessionMode: document.querySelector("#session-mode"),
  trafficPosture: document.querySelector("#traffic-posture"),
  trafficDelivered: document.querySelector("#metric-delivered"),
  trafficRedacted: document.querySelector("#metric-redacted"),
  trafficDenied: document.querySelector("#metric-denied"),
  trafficReview: document.querySelector("#metric-review"),
  familyList: document.querySelector("#family-list"),
  queueList: document.querySelector("#queue-list"),
  familyFilterRow: document.querySelector("#family-filter-row"),
  statusFilterRow: document.querySelector("#status-filter-row"),
  laneBoard: document.querySelector("#lane-board"),
  routeList: document.querySelector("#route-list"),
  parserRunList: document.querySelector("#parser-run-list"),
  brainChatList: document.querySelector("#brain-chat-list"),
  focusKind: document.querySelector("#integrator-focus-kind"),
  focusCard: document.querySelector("#integrator-focus-card"),
  inspectorStatus: document.querySelector("#inspector-status"),
  inspectorSummary: document.querySelector("#inspector-summary"),
  inspectorRouteCount: document.querySelector("#inspector-route-count"),
  inspectorRouteList: document.querySelector("#inspector-route-list"),
  inspectorAuthority: document.querySelector("#inspector-authority"),
  inspectorRaw: document.querySelector("#inspector-raw"),
  inspectorNormalizedCount: document.querySelector("#inspector-normalized-count"),
  inspectorNormalized: document.querySelector("#inspector-normalized"),
  inspectorFieldCount: document.querySelector("#inspector-field-count"),
  inspectorFields: document.querySelector("#inspector-fields"),
  inspectorNoteCount: document.querySelector("#inspector-note-count"),
  inspectorNotes: document.querySelector("#inspector-notes"),
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
timeslot: epoch-2
tags: communications,timing`,
  "j-series": `message_type: j-series track update
originator: unit-bravo
recipient: review-cell
summary: Synthetic track and communications status update for bounded internal review.
transport: fabric-shadow
precedence: routine
location: grid-bravo
track_number: track-204
tags: communications,track`,
  usmtf: `message_type: usmtf summary
originator: command-post-alpha
recipient: planner-review
summary: Synthetic formatted message summary preserved for human review and audit.
transport: fabric-shadow
precedence: routine
location: route-alpha
serial: usmtf-echo-5
tags: planning,review`,
};

const state = {
  families: [],
  messages: [],
  routes: [],
  runs: [],
  brainMessages: [],
  selectedMessageId: "",
  familyFilter: "all",
  statusFilter: "all",
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

function displayValue(value) {
  if (Array.isArray(value)) return value.join(", ");
  if (value && typeof value === "object") return JSON.stringify(value);
  return String(value ?? "");
}

function pairGrid(pairs) {
  const rows = pairs.filter(([, value]) => value !== undefined && value !== null && displayValue(value) !== "");
  if (!rows.length) return "";
  return `
    <div class="data-pair-grid">
      ${rows.map(([label, value]) => `
        <div class="data-pair">
          <span class="data-pair-label">${escapeHTML(label)}</span>
          <span class="data-pair-value">${escapeHTML(displayValue(value))}</span>
        </div>
      `).join("")}
    </div>
  `;
}

function renderList(container, records, emptyText, renderer) {
  if (!records || records.length === 0) {
    container.className = `${container.className.includes("queue-list") ? "queue-list" : container.className.includes("lane-board") ? "lane-board" : "list"} empty`;
    container.textContent = emptyText;
    return;
  }
  if (container === integrator.queueList) {
    container.className = "queue-list";
  } else if (container === integrator.laneBoard) {
    container.className = "lane-board";
  } else {
    container.className = "list";
  }
  container.innerHTML = records.map(renderer).join("");
}

function setStatus(ok, text) {
  integrator.apiStatus.classList.toggle("ok", ok);
  integrator.apiStatus.classList.toggle("error", !ok);
  integrator.apiStatusText.textContent = text;
}

function formatTimestamp(value) {
  if (!value) return "Unknown";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return parsed.toLocaleString([], {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function routeClassFromStatus(status) {
  if (status === "denied") return "conflict";
  if (status === "redacted") return "recommendation";
  return "advisory";
}

function routeBadge(status) {
  return `<span class="status-badge ${escapeHTML(status)}">${escapeHTML(status)}</span>`;
}

function byTimestampDesc(records) {
  return [...records].sort((left, right) => {
    const leftTime = Date.parse(left.timestamp || "") || 0;
    const rightTime = Date.parse(right.timestamp || "") || 0;
    return rightTime - leftTime;
  });
}

function routesForMessage(messageId) {
  return byTimestampDesc(state.routes.filter((route) => route.message_id === messageId));
}

function runForMessage(messageId) {
  return byTimestampDesc(state.runs.filter((run) => run.message_id === messageId))[0] || null;
}

function messageStatus(messageId) {
  const routes = routesForMessage(messageId);
  if (routes.some((route) => route.status === "denied")) return "denied";
  if (routes.some((route) => route.status === "redacted")) return "redacted";
  if (routes.some((route) => route.status === "delivered")) return "delivered";
  return "unrouted";
}

function latestMessageForRoute(route) {
  return state.messages.find((message) => message.id === route.message_id) || null;
}

function filteredMessages() {
  return byTimestampDesc(state.messages).filter((message) => {
    if (state.familyFilter !== "all" && message.message_family !== state.familyFilter) return false;
    if (state.statusFilter !== "all" && messageStatus(message.id) !== state.statusFilter) return false;
    return true;
  });
}

function ensureSelection(messages) {
  if (!messages.length) {
    state.selectedMessageId = "";
    return null;
  }
  const selected = messages.find((message) => message.id === state.selectedMessageId);
  if (selected) return selected;
  state.selectedMessageId = messages[0].id;
  return messages[0];
}

function activeMessage() {
  return state.messages.find((message) => message.id === state.selectedMessageId) || null;
}

function updateFilterButtons(row, attribute, activeValue) {
  row.querySelectorAll(`[${attribute}]`).forEach((button) => {
    button.classList.toggle("is-selected", button.getAttribute(attribute) === activeValue);
  });
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
      <div class="inline-actions">
        <button type="button" class="filter-chip" data-load-family="${escapeHTML(family.family)}">Load Template</button>
      </div>
    </article>
  `);
}

function renderTrafficSummary(messages, routes) {
  const delivered = routes.filter((route) => route.status === "delivered").length;
  const redacted = routes.filter((route) => route.status === "redacted").length;
  const denied = routes.filter((route) => route.status === "denied").length;
  integrator.trafficDelivered.textContent = String(delivered);
  integrator.trafficRedacted.textContent = String(redacted);
  integrator.trafficDenied.textContent = String(denied);
  integrator.trafficReview.textContent = String(messages.length);
  if (!messages.length) {
    integrator.trafficPosture.textContent = "Awaiting bounded traffic";
    return;
  }
  const priority = denied ? "denials present" : redacted ? "redactions present" : "all routes delivered";
  integrator.trafficPosture.textContent = `${messages.length} packets in review · ${priority}`;
}

function renderMessages(messages) {
  document.querySelector("#metric-messages").textContent = messages.length;
  document.querySelector("#queue-count").textContent = messages.length;
  renderList(integrator.queueList, messages, "No normalized messages", (message) => {
    const status = messageStatus(message.id);
    const selectedClass = state.selectedMessageId === message.id ? " is-selected" : "";
    const routes = routesForMessage(message.id);
    const lastRoute = routes[0] || null;
    return `
      <button type="button" class="queue-item${selectedClass}" data-message-id="${escapeHTML(message.id)}">
        <div class="queue-head">
          <strong>${escapeHTML(message.message_family)} · ${escapeHTML(message.message_type)}</strong>
          ${routeBadge(status)}
        </div>
        <span class="item-caption">${escapeHTML(formatTimestamp(message.timestamp))} · ${escapeHTML(message.originator)} to ${escapeHTML(message.recipient)}</span>
        <span class="queue-summary">${escapeHTML(message.summary)}</span>
        ${pairGrid([
          ["Transport", message.transport],
          ["Targets", (message.route_targets || []).join(", ") || "none"],
          ["Last lane", lastRoute ? lastRoute.destination.replace("jinx-", "") : "pending"],
        ])}
      </button>
    `;
  });
}

function renderInspector(message) {
  if (!message) {
    integrator.inspectorStatus.textContent = "Awaiting selection";
    integrator.inspectorSummary.className = "list empty";
    integrator.inspectorSummary.textContent = "Select a message from the queue to inspect its normalized packet.";
    integrator.inspectorRouteCount.textContent = "0";
    integrator.inspectorRouteList.className = "list empty";
    integrator.inspectorRouteList.textContent = "No route path loaded";
    integrator.inspectorAuthority.textContent = "Review only";
    integrator.inspectorRaw.className = "code-block empty";
    integrator.inspectorRaw.textContent = "Select a message from the queue.";
    integrator.inspectorNormalizedCount.textContent = "0 keys";
    integrator.inspectorNormalized.className = "code-block empty";
    integrator.inspectorNormalized.textContent = "No normalized packet yet.";
    integrator.inspectorFieldCount.textContent = "0";
    integrator.inspectorFields.className = "list empty";
    integrator.inspectorFields.textContent = "No extracted fields yet";
    integrator.inspectorNoteCount.textContent = "0";
    integrator.inspectorNotes.className = "list empty";
    integrator.inspectorNotes.textContent = "No validation or filter notes yet";
    return;
  }

  const routes = routesForMessage(message.id);
  const run = runForMessage(message.id);
  const status = messageStatus(message.id);
  const extractedEntries = Object.entries(message.extracted_fields || {});
  const normalizedPayload = run?.normalized_payload || {
    id: message.id,
    family: message.message_family,
    type: message.message_type,
    summary: message.summary,
    route_targets: message.route_targets || [],
  };
  const noteRecords = [
    ...(message.validation_notes || []).map((note) => ({ kind: "Validation", text: note })),
    ...((run?.filter_actions || []).map((note) => ({ kind: "Filter Action", text: note }))),
  ];

  integrator.inspectorStatus.textContent = status;
  integrator.inspectorSummary.className = "list";
  integrator.inspectorSummary.innerHTML = `
    <article class="item ${routeClassFromStatus(status)}">
      <strong>${escapeHTML(message.message_family)} · ${escapeHTML(message.message_type)}</strong>
      <span class="item-caption">Bounded packet selected from the traffic queue</span>
      <span>${escapeHTML(message.summary)}</span>
      ${pairGrid([
        ["Originator", message.originator],
        ["Recipient", message.recipient],
        ["Precedence", message.precedence],
        ["Network scope", message.network_scope],
        ["Filter profile", message.filter_profile],
        ["Confidence", message.confidence],
      ])}
    </article>
  `;

  integrator.inspectorRouteCount.textContent = String(routes.length);
  renderList(integrator.inspectorRouteList, routes, "No route path loaded", (route) => `
    <article class="item ${routeClassFromStatus(route.status)}">
      <strong>${escapeHTML(route.destination)}</strong>
      <span class="item-caption">${escapeHTML(route.topic)} · ${escapeHTML(formatTimestamp(route.timestamp))}</span>
      <span>${escapeHTML(route.policy_reason || "No policy reason captured.")}</span>
      ${pairGrid([
        ["Status", route.status],
        ["Schema", route.payload_schema],
        ["Redactions", (route.redacted_fields || []).join(", ") || "none"],
      ])}
    </article>
  `);

  integrator.inspectorAuthority.textContent = message.authority_state || "Review only";
  integrator.inspectorRaw.className = "code-block";
  integrator.inspectorRaw.textContent = message.raw_text || "No raw text preserved.";
  integrator.inspectorNormalizedCount.textContent = `${Object.keys(normalizedPayload).length} keys`;
  integrator.inspectorNormalized.className = "code-block";
  integrator.inspectorNormalized.textContent = JSON.stringify(normalizedPayload, null, 2);

  integrator.inspectorFieldCount.textContent = String(extractedEntries.length);
  if (extractedEntries.length) {
    integrator.inspectorFields.className = "list";
    integrator.inspectorFields.innerHTML = `
      <article class="item">
        <strong>Extracted Fields</strong>
        <span class="item-caption">Additional packet fields preserved for human review</span>
        ${pairGrid(extractedEntries)}
      </article>
    `;
  } else {
    integrator.inspectorFields.className = "list empty";
    integrator.inspectorFields.textContent = "No extracted fields yet";
  }

  integrator.inspectorNoteCount.textContent = String(noteRecords.length);
  renderList(integrator.inspectorNotes, noteRecords, "No validation or filter notes yet", (note) => `
    <article class="item">
      <strong>${escapeHTML(note.kind)}</strong>
      <span>${escapeHTML(note.text)}</span>
    </article>
  `);
}

function renderLanes(routes) {
  const lanes = Array.from(
    routes.reduce((accumulator, route) => {
      const current = accumulator.get(route.destination) || [];
      current.push(route);
      accumulator.set(route.destination, current);
      return accumulator;
    }, new Map()),
  ).sort(([left], [right]) => left.localeCompare(right));

  document.querySelector("#lane-count").textContent = String(lanes.length);
  renderList(integrator.laneBoard, lanes, "No route lanes yet", ([destination, laneRoutes]) => {
    const delivered = laneRoutes.filter((route) => route.status === "delivered").length;
    const redacted = laneRoutes.filter((route) => route.status === "redacted").length;
    const denied = laneRoutes.filter((route) => route.status === "denied").length;
    const highlights = laneRoutes.slice(0, 4).map((route) => {
      const message = latestMessageForRoute(route);
      return `${message ? `${message.message_family} ${message.message_type}` : route.message_id} · ${route.status}`;
    });
    return `
      <article class="lane-card ${denied ? "conflict" : redacted ? "recommendation" : "advisory"}">
        <div class="queue-head">
          <strong>${escapeHTML(destination)}</strong>
          ${routeBadge(denied ? "denied" : redacted ? "redacted" : "delivered")}
        </div>
        ${pairGrid([
          ["Delivered", delivered],
          ["Redacted", redacted],
          ["Denied", denied],
          ["Total routes", laneRoutes.length],
        ])}
        <ul class="lane-list">
          ${highlights.map((item) => `<li>${escapeHTML(item)}</li>`).join("")}
        </ul>
      </article>
    `;
  });
}

function renderRoutes(routes) {
  document.querySelector("#metric-routes").textContent = routes.length;
  document.querySelector("#route-count").textContent = routes.length;
  renderList(integrator.routeList, byTimestampDesc(routes).slice(0, 12), "No integrator routes", (route) => {
    const message = latestMessageForRoute(route);
    return `
      <article class="item ${routeClassFromStatus(route.status)}" data-message-id="${escapeHTML(route.message_id)}">
        <strong>${escapeHTML(route.destination)} · ${escapeHTML(route.status)}</strong>
        <span class="item-caption">${escapeHTML(formatTimestamp(route.timestamp))} · ${escapeHTML(message ? message.message_family : "unknown family")}</span>
        <span>${escapeHTML(route.policy_reason)}</span>
        ${pairGrid([
          ["Topic", route.topic],
          ["Schema", route.payload_schema],
          ["Redactions", (route.redacted_fields || []).join(", ") || "none"],
        ])}
      </article>
    `;
  });
}

function renderParserRuns(runs) {
  document.querySelector("#metric-parser-runs").textContent = runs.length;
  document.querySelector("#parser-run-count").textContent = runs.length;
  renderList(integrator.parserRunList, byTimestampDesc(runs).slice(0, 8), "No parser runs", (run) => `
    <article class="item">
      <strong>${escapeHTML(run.message_family)} · ${escapeHTML(run.id)}</strong>
      <span class="item-caption">${escapeHTML(formatTimestamp(run.timestamp))} · normalization ledger</span>
      ${pairGrid([
        ["Message ID", run.message_id],
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
  const message = activeMessage() || messages[0] || null;
  const route = message ? routesForMessage(message.id)[0] : routes[0] || null;
  const run = message ? runForMessage(message.id) : runs[0] || null;
  if (!message) {
    integrator.focusKind.textContent = "Awaiting message intake";
    integrator.focusCard.className = "list focus-card empty";
    integrator.focusCard.textContent = "No Integrator focus yet";
    return;
  }
  const status = route ? route.status : "message normalized";
  integrator.focusKind.textContent = status;
  integrator.focusCard.className = "list focus-card";
  integrator.focusCard.innerHTML = `
    <article class="item ${routeClassFromStatus(status)}">
      <strong>${escapeHTML(message.message_family)} · ${escapeHTML(message.message_type)}</strong>
      <span class="item-caption">Selected watchfloor packet</span>
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
            ? `Confirm ${route.destination} is the right licensed destination and review the policy result ${route.status}.`
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

function renderAll() {
  renderFamilies(state.families);
  renderTrafficSummary(state.messages, state.routes);
  const queueMessages = filteredMessages();
  const selected = ensureSelection(queueMessages);
  updateFilterButtons(integrator.familyFilterRow, "data-family-filter", state.familyFilter);
  updateFilterButtons(integrator.statusFilterRow, "data-status-filter", state.statusFilter);
  renderMessages(queueMessages);
  renderInspector(selected);
  renderLanes(byTimestampDesc(state.routes));
  renderRoutes(state.routes);
  renderParserRuns(state.runs);
  renderBrain(state.brainMessages);
  renderFocus(queueMessages, state.routes, state.runs);
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
    state.families = familiesDoc.message_families || [];
    state.messages = messagesDoc.integrator_messages || [];
    state.routes = routesDoc.integrator_routes || [];
    state.runs = parserRunsDoc.integrator_parser_runs || [];
    state.brainMessages = brainDoc.messages || [];
    renderSession(sessionDoc, entitlements);
    renderAll();
    setStatus(true, `${health.service} API online`);
  } catch (error) {
    setStatus(false, error.message || "API offline");
    renderInspector(null);
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
  const response = await postJSON("/api/integrator/messages", Object.fromEntries(new FormData(integrator.intakeForm).entries()));
  state.selectedMessageId = response.message_id || "";
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

integrator.familyFilterRow.addEventListener("click", (event) => {
  const button = event.target.closest("[data-family-filter]");
  if (!button) return;
  state.familyFilter = button.getAttribute("data-family-filter") || "all";
  renderAll();
});

integrator.statusFilterRow.addEventListener("click", (event) => {
  const button = event.target.closest("[data-status-filter]");
  if (!button) return;
  state.statusFilter = button.getAttribute("data-status-filter") || "all";
  renderAll();
});

integrator.queueList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-message-id]");
  if (!button) return;
  state.selectedMessageId = button.getAttribute("data-message-id") || "";
  renderAll();
});

integrator.routeList.addEventListener("click", (event) => {
  const card = event.target.closest("[data-message-id]");
  if (!card) return;
  state.selectedMessageId = card.getAttribute("data-message-id") || "";
  renderAll();
});

integrator.familyList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-load-family]");
  if (!button) return;
  const family = button.getAttribute("data-load-family");
  if (!family || !integrator.messageFamilySelect.querySelector(`option[value="${family}"]`)) return;
  integrator.messageFamilySelect.value = family;
  syncTemplate(true);
  integrator.messageText.focus();
});

syncSuggestedUsername(true);
syncTemplate(true);
refresh();
