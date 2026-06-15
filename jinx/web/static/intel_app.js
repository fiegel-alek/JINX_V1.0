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
  focusKind: document.querySelector("#intel-focus-kind"),
  focusCard: document.querySelector("#intel-focus-card"),
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
  intel.apiStatus.classList.toggle("ok", ok);
  intel.apiStatus.classList.toggle("error", !ok);
  intel.apiStatusText.textContent = text;
}

function renderFocusCard(packet) {
  if (!packet) {
    intel.focusKind.textContent = "Awaiting analyst packet";
    intel.focusCard.className = "list focus-card empty";
    intel.focusCard.textContent = "No INTEL focus yet";
    return;
  }
  intel.focusKind.textContent = packet.kind;
  intel.focusCard.className = "list focus-card";
  intel.focusCard.innerHTML = `
    <article class="item ${escapeHTML(packet.tone || "")}">
      <strong>${escapeHTML(packet.title)}</strong>
      <span class="item-caption">${escapeHTML(packet.caption || "")}</span>
      <span>${escapeHTML(packet.summary || "")}</span>
      ${pairGrid(packet.pairs || [])}
      ${packet.callout ? `
        <div class="item-callout">
          <strong>${escapeHTML(packet.calloutTitle || "Analyst next step")}</strong>
          <span>${escapeHTML(packet.callout)}</span>
        </div>
      ` : ""}
    </article>
  `;
}

function renderIntelFocus(snapshot) {
  const correlation = lastItem(snapshot.correlations || []);
  if (correlation) {
    renderFocusCard({
      kind: "Correlation packet",
      tone: "conflict",
      title: readableLabel(correlation.impacted_area),
      caption: `Correlation ready for ${correlation.recommended_review_role || "analyst review"}`,
      summary: correlation.summary || "Correlation packet available.",
      pairs: [
        ["Confidence", correlation.confidence],
        ["Reliability", correlation.reliability],
        ["Affected modules", (correlation.affected_modules || []).join(", ") || "none"],
      ],
      callout: `Validate restrictions and reliability before promoting this packet into a planning assumption.`,
    });
    return;
  }

  const impact = lastItem(snapshot.impacts || []);
  if (impact) {
    renderFocusCard({
      kind: "Impact packet",
      tone: "mission-impact",
      title: readableLabel(impact.impacted_area),
      caption: "Potential intelligence-derived effect on other packages",
      summary: impact.summary || "INTEL impact packet available.",
      pairs: [
        ["Confidence", impact.confidence],
        ["Delivered", impact.delivered_to_core ? "Yes" : "Pending"],
        ["Review role", impact.recommended_review_role || "intel analyst"],
      ],
      callout: "Confirm the impact before it changes planning, communications, or route assumptions.",
    });
    return;
  }

  const notice = lastItem(snapshot.notices || []);
  if (notice) {
    renderFocusCard({
      kind: "Module notice",
      tone: "advisory",
      title: notice.module || "affected module",
      caption: "Affected package notice sent from the fusion desk",
      summary: notice.summary || "Module notice available.",
      pairs: [
        ["Confidence", notice.confidence],
        ["Human review", notice.required_human_review ? "Required" : "Optional"],
        ["Delivered", notice.delivered_to_core ? "Yes" : "Pending"],
      ],
      callout: "Make sure the receiving package gets only the bounded context it is licensed to see.",
    });
    return;
  }

  const summary = lastItem(snapshot.summaries || []);
  if (summary) {
    renderFocusCard({
      kind: "Summary intake",
      tone: "isr",
      title: summary.source_category || "summary",
      caption: `Reliability ${summary.reliability || "unknown"} with restrictions preserved`,
      summary: summary.summary || "INTEL summary available.",
      pairs: [
        ["Locations", (summary.related_locations || []).join(", ") || "none"],
        ["Entities", (summary.related_entities || []).join(", ") || "none"],
        ["Restrictions", (summary.restrictions || []).join("; ") || "none"],
      ],
      callout: "Keep provenance and restrictions visible before using this summary outside the INTEL desk.",
    });
    return;
  }

  const feed = lastItem(snapshot.feeds || []);
  if (feed) {
    renderFocusCard({
      kind: "ISR feed snapshot",
      tone: "isr",
      title: feed.feed_name || "ISR feed",
      caption: `${feed.status || "unknown"} coverage for ${feed.coverage_area || "the current area"}`,
      summary: feed.summary || "ISR feed snapshot available.",
      pairs: [
        ["Feed type", feed.feed_type],
        ["Coverage", feed.coverage_area],
        ["Status", feed.status],
      ],
      callout: "Use the feed description to guide analysis, not as a hidden authority layer.",
    });
    return;
  }

  const brain = lastItem(snapshot.brain || []);
  if (brain) {
    renderFocusCard({
      kind: "BRAIN reachback",
      tone: "brain-chat",
      title: `${brain.answer.confidence_band || "limited"} confidence guidance`,
      caption: "Doctrine and review support for the analyst",
      summary: brain.answer.answer_text || "BRAIN answer available.",
      pairs: [
        ["Reachback", brain.answer.core_reachback_used ? "Used" : "Not used"],
        ["References", (brain.answer.references || []).join(", ") || "none"],
      ],
      callout: "Use BRAIN to frame the review, then keep final analytic judgment with the human analyst.",
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
      <span class="item-caption">INTEL summary with restrictions and provenance preserved</span>
      <span>${escapeHTML(summary.summary)}</span>
      ${pairGrid([
        ["Restrictions", (summary.restrictions || []).join("; ") || "none"],
        ["Locations", (summary.related_locations || []).join(", ") || "none"],
        ["Entities", (summary.related_entities || []).join(", ") || "none"],
      ])}
    </article>
  `);
}

function renderImpacts(impacts) {
  document.querySelector("#metric-impacts").textContent = impacts.length;
  document.querySelector("#impact-count").textContent = impacts.length;
  renderList(intel.impactList, impacts.slice(-8).reverse(), "No impacts", (impact) => `
    <article class="item mission-impact">
      <strong>${escapeHTML(impact.impacted_area)} · confidence ${escapeHTML(impact.confidence)}</strong>
      <span class="item-caption">Potential operational effect derived from INTEL context</span>
      <span>${escapeHTML(impact.summary)}</span>
      ${pairGrid([
        ["Delivered to Core", impact.delivered_to_core ? "Yes" : "Pending"],
        ["Review role", impact.recommended_review_role || "intel analyst"],
      ])}
    </article>
  `);
}

function renderCorrelations(correlations) {
  document.querySelector("#metric-correlations").textContent = correlations.length;
  document.querySelector("#correlation-count").textContent = correlations.length;
  renderList(intel.correlationList, correlations.slice(-8).reverse(), "No correlation packets", (correlation) => `
    <article class="item conflict">
      <strong>${escapeHTML(correlation.impacted_area)} · confidence ${escapeHTML(correlation.confidence)}</strong>
      <span class="item-caption">Correlation packet waiting for analyst validation</span>
      <span>${escapeHTML(correlation.summary)}</span>
      ${pairGrid([
        ["Modules", (correlation.affected_modules || []).join(", ") || "none"],
        ["Restrictions", (correlation.restrictions || []).join("; ") || "none"],
        ["Reliability", correlation.reliability],
      ])}
      <div class="item-callout">
        <strong>Analyst step</strong>
        <span>Validate restrictions and reliability before promoting this correlation into a broader package assumption.</span>
      </div>
    </article>
  `);
}

function renderNotices(notices) {
  document.querySelector("#metric-notices").textContent = notices.length;
  document.querySelector("#notice-count").textContent = notices.length;
  renderList(intel.noticeList, notices.slice(-10).reverse(), "No module notices", (notice) => `
    <article class="item advisory">
      <strong>${escapeHTML(notice.module)} · confidence ${escapeHTML(notice.confidence)}</strong>
      <span class="item-caption">Bounded notice for an affected licensed package</span>
      <span>${escapeHTML(notice.summary)}</span>
      ${pairGrid([
        ["Human review", notice.required_human_review ? "Required" : "Optional"],
        ["Delivered", notice.delivered_to_core ? "Yes" : "Pending"],
      ])}
    </article>
  `);
}

function renderFeeds(feeds) {
  document.querySelector("#feed-count").textContent = feeds.length;
  renderList(intel.feedList, feeds.slice(-8).reverse(), "No ISR feeds", (feed) => `
    <article class="item isr">
      <strong>${escapeHTML(feed.feed_name)} · ${escapeHTML(feed.status)}</strong>
      <span class="item-caption">Current feed snapshot for analyst awareness</span>
      ${pairGrid([
        ["Feed type", feed.feed_type],
        ["Coverage", feed.coverage_area],
      ])}
      <span>${escapeHTML(feed.summary)}</span>
    </article>
  `);
}

function renderBrain(messages) {
  document.querySelector("#brain-chat-count").textContent = messages.length;
  renderList(intel.brainChatList, messages.slice(-6).reverse(), "No Brain chat yet", (message) => `
    <article class="item brain-chat">
      <strong>${escapeHTML(message.answer.confidence_band)} · Core reachback ${message.answer.core_reachback_used ? "used" : "not used"}</strong>
      <span class="item-caption">Doctrine and review logic support for the INTEL desk</span>
      <span>Q: ${escapeHTML(message.question.text)}</span>
      <span>${escapeHTML(message.answer.answer_text)}</span>
      ${pairGrid([
        ["References", (message.answer.references || []).join(", ") || "none"],
        ["Reachback", message.answer.core_reachback_used ? "Used" : "Not used"],
      ])}
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
    renderIntelFocus({
      summaries: summaries.intelligence_summaries || [],
      impacts: impacts.intelligence_impacts || [],
      correlations: correlations.intel_correlations || [],
      notices: notices.intel_module_notices || [],
      feeds: feeds.isr_feeds || [],
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
