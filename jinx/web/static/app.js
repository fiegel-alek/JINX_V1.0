const apiStatus = document.querySelector("#api-status");
const apiStatusText = document.querySelector("#api-status-text");
const trackList = document.querySelector("#track-list");
const activityList = document.querySelector("#activity-list");
const copMap = document.querySelector("#cop-map");
const reportForm = document.querySelector("#report-form");

function setStatus(ok, text) {
  apiStatus.classList.toggle("ok", ok);
  apiStatus.classList.toggle("error", !ok);
  apiStatusText.textContent = text;
}

async function getJSON(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function postJSON(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `${response.status} ${response.statusText}`);
  return body;
}

function renderTracks(cop) {
  copMap.querySelectorAll(".track-marker").forEach((marker) => marker.remove());
  if (!cop.tracks || cop.tracks.length === 0) {
    trackList.className = "list empty";
    trackList.textContent = "No tracks loaded";
    return;
  }

  trackList.className = "list";
  trackList.innerHTML = "";
  cop.tracks.forEach((track, index) => {
    const item = document.createElement("div");
    item.className = "item";
    item.innerHTML = `<strong>${track.label}</strong><span>${track.location} · ${track.status} · confidence ${track.confidence}</span>`;
    trackList.appendChild(item);

    const marker = document.createElement("div");
    marker.className = "track-marker";
    marker.dataset.label = track.label;
    marker.style.left = `${25 + (index * 17) % 55}%`;
    marker.style.top = `${35 + (index * 23) % 40}%`;
    copMap.appendChild(marker);
  });
}

function addActivity(text) {
  if (activityList.classList.contains("empty")) {
    activityList.className = "list";
    activityList.innerHTML = "";
  }
  const item = document.createElement("div");
  item.className = "item";
  item.innerHTML = `<strong>${new Date().toLocaleTimeString()}</strong><span>${text}</span>`;
  activityList.prepend(item);
}

async function refreshCOP() {
  try {
    const health = await getJSON("/api/health");
    setStatus(true, `${health.service} API online`);
    const cop = await getJSON("/api/cop");
    renderTracks(cop);
  } catch (error) {
    setStatus(false, "API offline");
    addActivity(error.message);
  }
}

reportForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(reportForm).entries());
  try {
    const response = await postJSON("/api/operator-reports", data);
    addActivity(`Report ${response.report_id} delivered; advisory ${response.advisory_id} generated.`);
    await refreshCOP();
  } catch (error) {
    addActivity(error.message);
  }
});

refreshCOP();
