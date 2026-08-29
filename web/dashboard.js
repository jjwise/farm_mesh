const ui = {
  apiBase: document.getElementById("api_base"),
  adminToken: document.getElementById("admin_token"),
  lineSelect: document.getElementById("line_select"),
  historyFrom: document.getElementById("history_from"),
  historyTo: document.getElementById("history_to"),
  nodeSort: document.getElementById("node_sort"),
  nodeList: document.getElementById("node_list"),
  nodeDetail: document.getElementById("node_detail"),
  status: document.getElementById("status_panel"),
  mapSummary: document.getElementById("map_summary"),
  profileFilters: document.getElementById("profile_filters"),
};

const map = L.map("map", { zoomControl: true }).setView([-43.5321, 172.6362], 13);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const layers = {
  podEndpoints: L.layerGroup().addTo(map),
  podPoints: L.layerGroup().addTo(map),
  trackers: L.layerGroup().addTo(map),
  valves: L.layerGroup().addTo(map),
  infrastructure: L.layerGroup().addTo(map),
  history: L.layerGroup().addTo(map),
  podHeat: L.heatLayer([], { radius: 26, blur: 21, minOpacity: 0.2 }).addTo(map),
};

L.control.layers(null, {
  "Extrémités irrigation": layers.podEndpoints,
  "Pods interpolés": layers.podPoints,
  "Chaleur des pods": layers.podHeat,
  "Trackers génériques": layers.trackers,
  Vannes: layers.valves,
  Infrastructure: layers.infrastructure,
  Historique: layers.history,
}, { collapsed: false }).addTo(map);

const state = {
  nodes: [],
  lines: [],
  snapshots: [],
  selectedNodeId: null,
  markerByNode: new Map(),
  fittedOnce: false,
};

function setStatus(payload) {
  ui.status.textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
}

function apiBase() {
  return ui.apiBase.value.trim().replace(/\/+$/, "");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${apiBase()}${path}`, options);
  if (!response.ok) {
    let detail = await response.text();
    try { detail = JSON.stringify(JSON.parse(detail)); } catch (_) { /* plain text */ }
    throw new Error(`${response.status} ${response.statusText} — ${detail}`);
  }
  return response.json();
}

function adminHeaders() {
  const token = ui.adminToken.value.trim();
  if (!token) throw new Error("Le jeton administrateur est requis pour envoyer une commande.");
  return { "Content-Type": "application/json", "x-admin-token": token };
}

function toDatetimeLocal(date) {
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function isPosition(point) {
  return point && Number.isFinite(point.lat) && Number.isFinite(point.long) &&
    Math.abs(point.lat) <= 90 && Math.abs(point.long) <= 180 &&
    !(point.lat === 0 && point.long === 0);
}

function profileLabel(profile) {
  return {
    ENDPOINT_POD: "Pod irrigation",
    BASIC_TRACKER: "Tracker",
    VALVE_ACTUATOR: "Vanne",
    RELAY_FIXED: "Relais",
    GATEWAY_CENTRAL: "Gateway",
  }[profile] || profile;
}

function profileGroup(profile) {
  return ["RELAY_FIXED", "GATEWAY_CENTRAL"].includes(profile) ? "INFRASTRUCTURE" : profile;
}

function profileLayer(profile) {
  if (profile === "ENDPOINT_POD") return layers.podEndpoints;
  if (profile === "BASIC_TRACKER") return layers.trackers;
  if (profile === "VALVE_ACTUATOR") return layers.valves;
  return layers.infrastructure;
}

function profileMarker(profile) {
  const config = {
    ENDPOINT_POD: ["pod", "P"],
    BASIC_TRACKER: ["tracker", "T"],
    VALVE_ACTUATOR: ["valve", "V"],
  }[profile] || ["infrastructure", "I"];
  return L.divIcon({
    className: "",
    html: `<div class="node_marker ${config[0]}"><span>${config[1]}</span></div>`,
    iconSize: [28, 28],
    iconAnchor: [8, 28],
  });
}

function batteryLabel(mv) {
  return Number.isFinite(mv) && mv > 0 ? `${(mv / 1000).toFixed(2)} V` : "inconnue";
}
function valveStateLabel(value, uppercase = false) {
  const label = value === true ? "ouverte" : value === false ? "fermée" : "inconnue";
  return uppercase ? label.toUpperCase() : label;
}



function relativeTime(epochMs) {
  if (!epochMs) return "jamais vu";
  const seconds = Math.max(0, Math.round((Date.now() - epochMs) / 1000));
  if (seconds < 60) return `il y a ${seconds} s`;
  if (seconds < 3600) return `il y a ${Math.round(seconds / 60)} min`;
  if (seconds < 86400) return `il y a ${Math.round(seconds / 3600)} h`;
  return `il y a ${Math.round(seconds / 86400)} j`;
}

function nodePopup(node) {
  const valve = node.node_profile === "VALVE_ACTUATOR"
    ? `<br/>Vanne : <strong>${valveStateLabel(node.valve_open)}</strong>` : "";
  return [
    `<strong>${escapeHtml(node.tracker_id)}</strong>`,
    escapeHtml(profileLabel(node.node_profile)),
    `${escapeHtml(node.line_id)} · ${escapeHtml(relativeTime(node.last_seen_utc_ms))}`,
    `Batterie ${escapeHtml(batteryLabel(node.battery_mv))}${valve}`,
  ].join("<br/>");
}

function activeProfiles() {
  return new Set(
    [...ui.profileFilters.querySelectorAll('input[type="checkbox"]:checked')].map((input) => input.value),
  );
}

function filteredNodes() {
  const active = activeProfiles();
  const nodes = state.nodes.filter((node) => active.has(profileGroup(node.node_profile)));
  const sort = ui.nodeSort.value;
  nodes.sort((a, b) => {
    if (sort === "name") return a.tracker_id.localeCompare(b.tracker_id);
    if (sort === "profile") return a.node_profile.localeCompare(b.node_profile) || a.tracker_id.localeCompare(b.tracker_id);
    if (sort === "battery") return (b.battery_mv || 0) - (a.battery_mv || 0);
    return (b.last_seen_utc_ms || 0) - (a.last_seen_utc_ms || 0);
  });
  return nodes;
}

function renderNodes({ fit = false } = {}) {
  layers.podEndpoints.clearLayers();
  layers.trackers.clearLayers();
  layers.valves.clearLayers();
  layers.infrastructure.clearLayers();
  state.markerByNode.clear();
  const visible = filteredNodes();
  const bounds = [];

  for (const node of visible) {
    if (!isPosition(node)) continue;
    const marker = L.marker([node.lat, node.long], { icon: profileMarker(node.node_profile) })
      .bindPopup(nodePopup(node))
      .on("click", () => selectNode(node.tracker_id));
    marker.addTo(profileLayer(node.node_profile));
    if (node.stale) marker.setOpacity(0.58);
    state.markerByNode.set(node.tracker_id, marker);
    bounds.push([node.lat, node.long]);
  }

  renderNodeList(visible);
  ui.mapSummary.textContent = `${visible.length} nœud${visible.length === 1 ? "" : "s"} affiché${visible.length === 1 ? "" : "s"} · ${state.snapshots.reduce((sum, item) => sum + item.pods.length, 0)} pods`;
  if (fit && bounds.length && !state.fittedOnce) {
    map.fitBounds(bounds, { padding: [45, 45], maxZoom: 16 });
    state.fittedOnce = true;
  }
}

function renderNodeList(nodes) {
  ui.nodeList.replaceChildren();
  for (const node of nodes) {
    const button = document.createElement("button");
    button.className = `node_card${node.tracker_id === state.selectedNodeId ? " selected" : ""}`;
    button.type = "button";
    button.innerHTML = `
      <div class="node_row">
        <strong>${escapeHtml(node.tracker_id)}</strong>
        <span class="profile_badge profile-${escapeHtml(node.node_profile)}">${escapeHtml(profileLabel(node.node_profile))}</span>
      </div>
      <span class="node_meta">${escapeHtml(node.line_id)} · ${escapeHtml(relativeTime(node.last_seen_utc_ms))} · ${escapeHtml(batteryLabel(node.battery_mv))}</span>`;
    button.addEventListener("click", () => selectNode(node.tracker_id, true));
    ui.nodeList.appendChild(button);
  }
}

function selectNode(trackerId, pan = false) {
  state.selectedNodeId = trackerId;
  const node = state.nodes.find((item) => item.tracker_id === trackerId);
  renderNodeList(filteredNodes());
  if (!node) return;
  renderNodeDetail(node);
  const marker = state.markerByNode.get(trackerId);
  if (marker && pan) {
    map.setView(marker.getLatLng(), Math.max(map.getZoom(), 16));
    marker.openPopup();
  }
}

function safeStatusClass(value) {
  return String(value || "").replace(/[^A-Z_]/g, "");
}

function renderNodeDetail(node) {
  const commandStatus = node.last_command_status || "AUCUNE";
  let controls = "";
  if (node.node_profile === "BASIC_TRACKER") {
    controls = `
      <label for="position_interval">Fréquence d’envoi (secondes)</label>
      <input id="position_interval" type="number" min="60" max="86400" value="${node.position_interval_sec || 900}" />
      <button id="save_interval">Appliquer au tracker</button>`;
  } else if (node.node_profile === "VALVE_ACTUATOR") {
    controls = `
      <p class="safety_note">L’ouverture exige une durée et sera refusée si l’horloge du nœud n’est pas valide. Le firmware referme aussi la sortie automatiquement.</p>
      <label for="valve_duration">Durée d’ouverture (secondes)</label>
      <input id="valve_duration" type="number" min="1" max="3600" value="300" />
      <div class="command_row">
        <button id="open_valve" class="danger_button">Ouvrir</button>
        <button id="close_valve" class="secondary_button">Fermer</button>
      </div>`;
  }

  ui.nodeDetail.classList.remove("empty");
  ui.nodeDetail.innerHTML = `
    <div class="section_heading">
      <h2>${escapeHtml(node.tracker_id)}</h2>
      <span class="profile_badge profile-${escapeHtml(node.node_profile)}">${escapeHtml(profileLabel(node.node_profile))}</span>
    </div>
    <div class="detail_grid">
      <div><span>Dernier contact</span><strong>${escapeHtml(relativeTime(node.last_seen_utc_ms))}</strong></div>
      <div><span>Batterie</span><strong>${escapeHtml(batteryLabel(node.battery_mv))}</strong></div>
      <div><span>Ligne</span><strong>${escapeHtml(node.line_id)}</strong></div>
      <div><span>Position</span><strong>${node.stale ? "ancienne" : node.fix ? "valide" : "sans fix"}</strong></div>
      ${node.node_profile === "VALVE_ACTUATOR" ? `<div><span>Vanne confirmée</span><strong>${valveStateLabel(node.valve_open, true)}</strong></div>` : ""}
      <div><span>Dernière commande</span><strong><span class="status_badge status-${safeStatusClass(commandStatus)}">${escapeHtml(commandStatus)}</span></strong></div>
    </div>
    ${controls}`;

  document.getElementById("save_interval")?.addEventListener("click", async () => {
    const interval = Number(document.getElementById("position_interval").value);
    await sendCommand(node, { action: "SET_POSITION_INTERVAL", position_interval_sec: interval });
  });
  document.getElementById("open_valve")?.addEventListener("click", async () => {
    const duration = Number(document.getElementById("valve_duration").value);
    if (!window.confirm(`Ouvrir ${node.tracker_id} pendant ${duration} secondes ?`)) return;
    await sendCommand(node, { action: "SET_VALVE", valve_open: true, duration_sec: duration });
  });
  document.getElementById("close_valve")?.addEventListener("click", async () => {
    await sendCommand(node, { action: "SET_VALVE", valve_open: false });
  });
}

async function sendCommand(node, payload) {
  try {
    setStatus(`Envoi de ${payload.action} à ${node.tracker_id}…`);
    const command = await requestJson(`/v1/nodes/${encodeURIComponent(node.tracker_id)}/commands`, {
      method: "POST",
      headers: adminHeaders(),
      body: JSON.stringify(payload),
    });
    setStatus(command);
    await refreshNodes();
    pollCommand(node.tracker_id, command.command_id);
  } catch (error) {
    setStatus(error.message);
  }
}

async function pollCommand(trackerId, commandId) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    try {
      const command = await requestJson(`/v1/nodes/${encodeURIComponent(trackerId)}/commands/${encodeURIComponent(commandId)}`);
      if (["ACKED", "REJECTED", "FAILED", "EXPIRED"].includes(command.status)) {
        setStatus(command);
        await refreshNodes();
        return;
      }
    } catch (error) {
      setStatus(error.message);
      return;
    }
  }
}

function renderPods() {
  layers.podPoints.clearLayers();
  const heat = [];
  for (const snapshot of state.snapshots) {
    for (const pod of snapshot.pods) {
      if (!isPosition(pod)) continue;
      const color = pod.compressed ? "#c94e39" : "#e2a21a";
      L.circleMarker([pod.lat, pod.long], {
        radius: 4,
        color,
        weight: 1,
        fillColor: color,
        fillOpacity: 0.9,
      }).bindTooltip(`${escapeHtml(snapshot.line_id)} · Pod #${pod.pod_index + 1}`).addTo(layers.podPoints);
      heat.push([pod.lat, pod.long, 0.72]);
    }
  }
  layers.podHeat.setLatLngs(heat);
}

async function loadHistory() {
  const lineId = ui.lineSelect.value;
  if (!lineId) return;
  const from = new Date(ui.historyFrom.value || Date.now() - 86400000).toISOString();
  const to = new Date(ui.historyTo.value || Date.now()).toISOString();
  const history = await requestJson(`/v1/line/${encodeURIComponent(lineId)}/history?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);
  layers.history.clearLayers();
  const byTracker = new Map();
  for (const item of history.filter(isPosition)) {
    if (!byTracker.has(item.tracker_id)) byTracker.set(item.tracker_id, []);
    byTracker.get(item.tracker_id).push(item);
  }
  const colors = ["#2e69b3", "#c94e39", "#166a4a", "#8b5f16", "#7546a8"];
  let index = 0;
  for (const [trackerId, points] of byTracker.entries()) {
    const coordinates = points.map((point) => [point.lat, point.long]);
    const color = colors[index % colors.length];
    index += 1;
    if (coordinates.length > 1) {
      L.polyline(coordinates, { color, weight: 3, opacity: 0.78, dashArray: "7 5" })
        .bindTooltip(escapeHtml(trackerId)).addTo(layers.history);
    }
  }
  if (!map.hasLayer(layers.history)) layers.history.addTo(map);
  setStatus({ line_id: lineId, history_points: history.length, trackers: byTracker.size });
}

async function refreshNodes() {
  state.nodes = await requestJson("/v1/nodes");
  renderNodes();
  if (state.selectedNodeId) selectNode(state.selectedNodeId);
}

async function loadAll() {
  setStatus("Chargement du réseau…");
  const [nodes, lines] = await Promise.all([requestJson("/v1/nodes"), requestJson("/v1/lines")]);
  state.nodes = nodes;
  state.lines = lines;
  ui.lineSelect.replaceChildren();
  for (const line of lines) {
    const option = document.createElement("option");
    option.value = line.line_id;
    option.textContent = `${line.name || line.line_id} · ${line.pod_count} pods`;
    ui.lineSelect.appendChild(option);
  }
  const nowIso = new Date().toISOString();
  state.snapshots = await Promise.all(
    lines.map((line) => requestJson(`/v1/line/${encodeURIComponent(line.line_id)}/snapshot?at=${encodeURIComponent(nowIso)}`)),
  );
  renderPods();
  renderNodes({ fit: true });
  setStatus({ nodes: nodes.length, lines: lines.length, pods: state.snapshots.reduce((sum, item) => sum + item.pods.length, 0) });
}

document.getElementById("refresh_all").addEventListener("click", () => loadAll().catch((error) => setStatus(error.message)));
document.getElementById("load_history").addEventListener("click", () => loadHistory().catch((error) => setStatus(error.message)));
ui.nodeSort.addEventListener("change", () => renderNodes());
ui.profileFilters.addEventListener("change", () => renderNodes());

const now = new Date();
ui.historyTo.value = toDatetimeLocal(now);
ui.historyFrom.value = toDatetimeLocal(new Date(now.getTime() - 24 * 3600 * 1000));

loadAll().catch((error) => setStatus(error.message));
setInterval(() => refreshNodes().catch((error) => setStatus(error.message)), 30000);
