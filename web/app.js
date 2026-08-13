const api_base_input = document.getElementById("api_base");
const line_select = document.getElementById("line_select");
const snapshot_at_input = document.getElementById("snapshot_at");
const history_from_input = document.getElementById("history_from");
const history_to_input = document.getElementById("history_to");
const status_panel = document.getElementById("status_panel");
const show_heatmap_input = document.getElementById("show_heatmap");

const map = L.map("map", { zoomControl: true }).setView([-33.865143, 151.2099], 14);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const endpoint_layer = L.layerGroup().addTo(map);
const pod_layer = L.layerGroup().addTo(map);
const history_layer = L.layerGroup().addTo(map);
let heat_layer = L.heatLayer([], { radius: 22, blur: 18, minOpacity: 0.2 }).addTo(map);

function set_status(payload) {
  status_panel.textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
}

function to_datetime_local(date) {
  const offset_ms = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset_ms).toISOString().slice(0, 16);
}

function parse_datetime_local(value) {
  if (!value) return null;
  return new Date(value);
}

function get_api_base() {
  return api_base_input.value.trim().replace(/\/+$/, "");
}

function is_map_position(point) {
  return Number.isFinite(point.lat) && Number.isFinite(point.long) && Math.abs(point.lat) <= 90 && Math.abs(point.long) <= 180;
}

function endpoint_popup(label, point) {
  const timestamp = new Date(point.ts_utc_ms).toLocaleString();
  const battery = point.battery_mv > 0 ? `${(point.battery_mv / 1000).toFixed(2)} V` : "inconnue";
  const quality = point.stale ? "position ancienne" : point.fix ? "fix valide" : "sans fix";
  return [
    `<strong>${label} · ${point.tracker_id}</strong>`,
    timestamp,
    `${quality} · ${point.time_quality}`,
    `${point.publish_reason} · ${point.motion_state}`,
    `batterie ${battery} · hop ${point.hop_count}`,
  ].join("<br/>");
}

async function request_json(path) {
  const endpoint = `${get_api_base()}${path}`;
  const response = await fetch(endpoint);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`${response.status} ${response.statusText} - ${message}`);
  }
  return response.json();
}

function render_snapshot(snapshot) {
  endpoint_layer.clearLayers();
  pod_layer.clearLayers();

  const markers = [];

  if (snapshot.endpoint_a && is_map_position(snapshot.endpoint_a)) {
    const point = snapshot.endpoint_a;
    const marker = L.marker([point.lat, point.long]).bindPopup(endpoint_popup("Extrémité A", point));
    if (point.stale) marker.setOpacity(0.55);
    marker.addTo(endpoint_layer);
    markers.push([point.lat, point.long]);
  }

  if (snapshot.endpoint_b && is_map_position(snapshot.endpoint_b)) {
    const point = snapshot.endpoint_b;
    const marker = L.marker([point.lat, point.long]).bindPopup(endpoint_popup("Extrémité B", point));
    if (point.stale) marker.setOpacity(0.55);
    marker.addTo(endpoint_layer);
    markers.push([point.lat, point.long]);
  }

  for (const pod of snapshot.pods) {
    const color = pod.compressed ? "#d93f0b" : "#0b7b59";
    L.circleMarker([pod.lat, pod.long], {
      radius: 4,
      color,
      weight: 1,
      fillOpacity: 0.9,
    })
      .bindTooltip(`Pod #${pod.pod_index}${pod.compressed ? " (compressed)" : ""}`)
      .addTo(pod_layer);
    markers.push([pod.lat, pod.long]);
  }

  if (markers.length > 0) {
    map.fitBounds(markers, { padding: [30, 30] });
  }
}

function render_history(history) {
  history_layer.clearLayers();
  const valid_history = history.filter(is_map_position);
  const coordinates = valid_history.map((item) => [item.lat, item.long]);
  if (coordinates.length === 0) {
    if (heat_layer) {
      heat_layer.setLatLngs([]);
    }
    return;
  }

  const colors = ["#1453a6", "#9f1239", "#0b7b59", "#8a4b08"];
  const by_tracker = new Map();
  for (const item of valid_history) {
    if (!by_tracker.has(item.tracker_id)) by_tracker.set(item.tracker_id, []);
    by_tracker.get(item.tracker_id).push(item);
  }
  let color_index = 0;
  for (const [tracker_id, points] of by_tracker.entries()) {
    const color = colors[color_index % colors.length];
    color_index += 1;
    const tracker_coordinates = points.map((item) => [item.lat, item.long]);
    if (tracker_coordinates.length > 1) {
      L.polyline(tracker_coordinates, { color, weight: 3, opacity: 0.75, dashArray: "7 5" })
        .bindTooltip(tracker_id)
        .addTo(history_layer);
    }
    const last = points[points.length - 1];
    L.circleMarker([last.lat, last.long], { radius: 5, color, fillOpacity: 0.9 })
      .bindPopup(endpoint_popup("Dernière mesure", last))
      .addTo(history_layer);
  }

  if (heat_layer) {
    heat_layer.setLatLngs(valid_history.map((item) => [item.lat, item.long, 0.8]));
  }
}

async function load_lines() {
  const lines = await request_json("/v1/lines");
  line_select.innerHTML = "";
  for (const line of lines) {
    const option = document.createElement("option");
    option.value = line.line_id;
    option.textContent = `${line.line_id} (${line.pod_count} pods)`;
    line_select.appendChild(option);
  }

  set_status({
    line_count: lines.length,
    lines,
  });
}

async function load_snapshot() {
  if (!line_select.value) {
    return;
  }
  const at_date = parse_datetime_local(snapshot_at_input.value) || new Date();
  const at = encodeURIComponent(at_date.toISOString());
  const snapshot = await request_json(`/v1/line/${line_select.value}/snapshot?at=${at}`);
  render_snapshot(snapshot);
  set_status(snapshot);
}

async function load_history() {
  if (!line_select.value) {
    return;
  }

  const from_date = parse_datetime_local(history_from_input.value) || new Date(Date.now() - 24 * 3600 * 1000);
  const to_date = parse_datetime_local(history_to_input.value) || new Date();
  const from = encodeURIComponent(from_date.toISOString());
  const to = encodeURIComponent(to_date.toISOString());
  const history = await request_json(`/v1/line/${line_select.value}/history?from=${from}&to=${to}`);
  render_history(history);
  set_status({ points: history.length, from: from_date.toISOString(), to: to_date.toISOString() });
}

document.getElementById("refresh_lines").addEventListener("click", () => {
  load_lines().catch((error) => set_status(error.message));
});

document.getElementById("load_snapshot").addEventListener("click", () => {
  load_snapshot().catch((error) => set_status(error.message));
});

document.getElementById("load_history").addEventListener("click", () => {
  load_history().catch((error) => set_status(error.message));
});

show_heatmap_input.addEventListener("change", () => {
  if (show_heatmap_input.checked) {
    if (!heat_layer) {
      heat_layer = L.heatLayer([], { radius: 22, blur: 18, minOpacity: 0.2 }).addTo(map);
    }
  } else if (heat_layer) {
    map.removeLayer(heat_layer);
    heat_layer = null;
  }
});

function init_defaults() {
  const now = new Date();
  snapshot_at_input.value = to_datetime_local(now);
  history_to_input.value = to_datetime_local(now);
  history_from_input.value = to_datetime_local(new Date(now.getTime() - 24 * 3600 * 1000));
}

init_defaults();
load_lines()
  .then(() => load_snapshot())
  .then(() => load_history())
  .catch((error) => set_status(error.message));
