const intel = {
  apiStatus: document.querySelector("#api-status"),
  apiStatusText: document.querySelector("#api-status-text"),
  roleSelect: document.querySelector("#role-select"),
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

function activeRole() {
  return intel.roleSelect.value;
}

function requestHeaders(extra = {}) {
  return { "X-JINX-Role": activeRole(), "X-JINX-Package": "intel", ...extra };
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
  intel.apiStatus.classList.toggle("ok", ok);
  intel.apiStatus.classList.toggle("error", !ok);
  intel.apiStatusText.textContent = text;
}

function renderEntitlements(entitlements) {
  document.querySelector(".eyebrow").textContent = entitlements.label || "INTEL package";
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
    const [health, entitlements, summaries, impacts, correlations, notices, feeds, brain] = await Promise.all([
      getJSON("/api/health"),
      getJSON("/api/entitlements"),
      getJSON("/api/intel/summaries"),
      getJSON("/api/intel/impacts"),
      getJSON("/api/intel/correlations"),
      getJSON("/api/intel/module-notices"),
      getJSON("/api/intel/isr-feeds"),
      getJSON("/api/brain/chat-messages"),
    ]);
    setStatus(true, `${health.service} API online`);
    renderEntitlements(entitlements);
    renderSummaries(summaries.intelligence_summaries || []);
    renderImpacts(impacts.intelligence_impacts || []);
    renderCorrelations(correlations.intel_correlations || []);
    renderNotices(notices.intel_module_notices || []);
    renderFeeds(feeds.isr_feeds || []);
    renderBrain(brain.messages || []);
  } catch (error) {
    setStatus(false, "API offline");
  }
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

intel.refreshButton.addEventListener("click", refresh);
intel.roleSelect.addEventListener("change", refresh);
refresh();
