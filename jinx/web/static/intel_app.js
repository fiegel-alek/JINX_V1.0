const intel = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
  roleSelect: document.querySelector("#role-select"),
  usernameInput: document.querySelector("#username-input"),
  sessionButton: document.querySelector("#session-button"),
  clearSessionButton: document.querySelector("#clear-session-button"),
  sessionSummary: document.querySelector("#session-summary"),
  sessionMode: document.querySelector("#session-mode"),
  summaryList: document.querySelector("#summary-list"),
  impactList: document.querySelector("#impact-list"),
  correlationList: document.querySelector("#correlation-list"),
  noticeList: document.querySelector("#notice-list"),
  feedList: document.querySelector("#feed-list"),
  brainChatList: document.querySelector("#brain-chat-list"),
  summaryForm: document.querySelector("#intel-summary-form"),
  feedForm: document.querySelector("#isr-feed-form"),
  brainChatForm: document.querySelector("#brain-chat-form"),
  refreshButton: document.querySelector("#refresh-button"),
};

const SESSION_KEY = "jinx-intel-session-token";
const PACKAGE_NAME = "intel";
const USERNAME_BY_ROLE = {
  intel_analyst: "intel-alpha",
  auditor: "auditor-alpha",
  system_administrator: "systemadministrator",
};

function activeRole() {
  return intel.roleSelect.value;
}

function activeSessionToken() {
  return localStorage.getItem(SESSION_KEY) || "";
}

function suggestedUsername() {
  return USERNAME_BY_ROLE[activeRole()] || "intel-alpha";
}

function syncSuggestedUsername(force = false) {
  if (intel.usernameInput.readOnly) return;
  const current = intel.usernameInput.value.trim();
  if (force || !current || Object.values(USERNAME_BY_ROLE).includes(current)) {
    intel.usernameInput.value = suggestedUsername();
  }
}

function activeUsername() {
  return intel.usernameInput.value.trim() || suggestedUsername();
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
  intel.apiStatus.classList.toggle("ok", ok);
  intel.apiStatus.classList.toggle("error", !ok);
  intel.apiStatusText.textContent = text;
}

function renderSession(sessionDoc, entitlements) {
  const session = sessionDoc.session || null;
  if (!session && activeSessionToken()) {
    localStorage.removeItem(SESSION_KEY);
  }
  document.querySelector(".eyebrow").textContent = entitlements.label || "INTEL package";
  intel.sessionMode.textContent = session ? "Session active" : "Header role mode";
  intel.roleSelect.disabled = Boolean(session);
  intel.usernameInput.readOnly = Boolean(session);

  if (session) {
    const role = String((session.roles || [])[0] || activeRole());
    if (intel.roleSelect.querySelector(`option[value="${role}"]`)) {
      intel.roleSelect.value = role;
    }
    intel.usernameInput.value = session.username || activeUsername();
    intel.brainChatForm.elements.user_id.value = session.username || activeUsername();
    intel.sessionSummary.className = "list";
    intel.sessionSummary.innerHTML = `
      <article class="item advisory">
        <strong>${escapeHTML(session.display_name || session.username)}</strong>
        <span>${escapeHTML(role)} · package ${escapeHTML(session.package || PACKAGE_NAME)} · session ${escapeHTML(session.id || "unknown")}</span>
        <span>license ${entitlements.license_active ? "active" : "inactive"} · ${entitlements.simulation_only ? "simulation only" : "controlled adapter enabled"}</span>
      </article>
    `;
    return;
  }

  syncSuggestedUsername(true);
  intel.brainChatForm.elements.user_id.value = activeUsername();
  intel.sessionSummary.className = "list empty";
  intel.sessionSummary.textContent = entitlements.license_active
    ? `No active session. ${entitlements.label || "INTEL package"} is running in local header mode.`
    : `${entitlements.label || "INTEL package"} license is inactive.`;
}

function renderSummaries(summaries) {
  document.querySelector("#metric-summaries").textContent = summaries.length;
  document.querySelector("#summary-count").textContent = summaries.length;
  renderList(intel.summaryList, summaries.slice(-8).reverse(), "No summaries", (summary) => `
    <article class="item isr">
      <strong>${escapeHTML(summary.source_category)} · reliability ${escapeHTML(summary.reliability)}</strong>
      <span>${escapeHTML(summary.summary)}</span>
      <span>restrictions: ${escapeHTML((summary.restrictions || []).join("; ") || "none")}</span>
      <span>locations: ${escapeHTML((summary.related_locations || []).join(", ") || "none")}</span>
    </article>
  `);
}

function renderImpacts(impacts) {
  document.querySelector("#metric-impacts").textContent = impacts.length;
  document.querySelector("#impact-count").textContent = impacts.length;
  renderList(intel.impactList, impacts.slice(-8).reverse(), "No impacts", (impact) => `
    <article class="item mission-impact">
      <strong>${escapeHTML(impact.impacted_area)} · confidence ${escapeHTML(impact.confidence)}</strong>
      <span>${escapeHTML(impact.summary)}</span>
      <span>delivered to Core: ${escapeHTML(impact.delivered_to_core)}</span>
    </article>
  `);
}

function renderCorrelations(correlations) {
  document.querySelector("#metric-correlations").textContent = correlations.length;
  document.querySelector("#correlation-count").textContent = correlations.length;
  renderList(intel.correlationList, correlations.slice(-8).reverse(), "No correlation packets", (correlation) => `
    <article class="item conflict">
      <strong>${escapeHTML(correlation.impacted_area)} · confidence ${escapeHTML(correlation.confidence)}</strong>
      <span>${escapeHTML(correlation.summary)}</span>
      <span>modules: ${escapeHTML((correlation.affected_modules || []).join(", ") || "none")}</span>
      <span>restrictions: ${escapeHTML((correlation.restrictions || []).join("; ") || "none")}</span>
    </article>
  `);
}

function renderNotices(notices) {
  document.querySelector("#metric-notices").textContent = notices.length;
  document.querySelector("#notice-count").textContent = notices.length;
  renderList(intel.noticeList, notices.slice(-10).reverse(), "No module notices", (notice) => `
    <article class="item advisory">
      <strong>${escapeHTML(notice.module)} · confidence ${escapeHTML(notice.confidence)}</strong>
      <span>${escapeHTML(notice.summary)}</span>
      <span>human review ${notice.required_human_review ? "required" : "missing"} · delivered ${escapeHTML(notice.delivered_to_core)}</span>
    </article>
  `);
}

function renderFeeds(feeds) {
  document.querySelector("#feed-count").textContent = feeds.length;
  renderList(intel.feedList, feeds.slice(-8).reverse(), "No ISR feeds", (feed) => `
    <article class="item isr">
      <strong>${escapeHTML(feed.feed_name)} · ${escapeHTML(feed.status)}</strong>
      <span>${escapeHTML(feed.feed_type)} · ${escapeHTML(feed.coverage_area)}</span>
      <span>${escapeHTML(feed.summary)}</span>
    </article>
  `);
}

function renderBrain(messages) {
  document.querySelector("#brain-chat-count").textContent = messages.length;
  renderList(intel.brainChatList, messages.slice(-6).reverse(), "No Brain chat yet", (message) => `
    <article class="item brain-chat">
      <strong>${escapeHTML(message.answer.confidence_band)} · Core reachback ${message.answer.core_reachback_used ? "used" : "not used"}</strong>
      <span>Q: ${escapeHTML(message.question.text)}</span>
      <span>${escapeHTML(message.answer.answer_text)}</span>
    </article>
  `);
}

async function refresh() {
  try {
    const [health, entitlements, sessionDoc, summaries, impacts, correlations, notices, feeds, brain] = await Promise.all([
      getJSON("/api/health"),
      getJSON("/api/entitlements"),
      getJSON("/api/auth/session"),
      getJSON("/api/intel/summaries"),
      getJSON("/api/intel/impacts"),
      getJSON("/api/intel/correlations"),
      getJSON("/api/intel/module-notices"),
      getJSON("/api/intel/isr-feeds"),
      getJSON("/api/brain/chat-messages"),
    ]);
    renderSession(sessionDoc, entitlements);
    setStatus(true, `${health.service} API online`);
    renderSummaries(summaries.intelligence_summaries || []);
    renderImpacts(impacts.intelligence_impacts || []);
    renderCorrelations(correlations.intel_correlations || []);
    renderNotices(notices.intel_module_notices || []);
    renderFeeds(feeds.isr_feeds || []);
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

intel.summaryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await postJSON("/api/intel/summaries", Object.fromEntries(new FormData(intel.summaryForm).entries()));
  await refresh();
});

intel.feedForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await postJSON("/api/intel/isr-feeds", Object.fromEntries(new FormData(intel.feedForm).entries()));
  await refresh();
});

intel.brainChatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(intel.brainChatForm).entries());
  data.role = activeRole();
  await postJSON("/api/brain/chat", data);
  await refresh();
});

intel.sessionButton.addEventListener("click", async () => {
  try {
    await connectSession();
    await refresh();
  } catch (error) {
    setStatus(false, error.message || "Session denied");
  }
});

intel.clearSessionButton.addEventListener("click", async () => {
  await clearSession();
  syncSuggestedUsername(true);
  await refresh();
});

intel.refreshButton.addEventListener("click", refresh);
intel.roleSelect.addEventListener("change", async () => {
  syncSuggestedUsername(true);
  await refresh();
});

syncSuggestedUsername(true);
refresh();
