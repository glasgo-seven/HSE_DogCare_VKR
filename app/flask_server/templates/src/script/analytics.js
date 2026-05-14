const ML = "/api/ml";
let refreshToken = Date.now();

async function fetchJson(path, params) {
	const u = new URL(ML.replace(/\/$/, "") + path, window.location.origin);
	if (params) Object.entries(params).forEach(([k, v]) => { if (v !== "" && v != null) u.searchParams.set(k, v); });
	u.searchParams.set("_ts", String(refreshToken));
	const r = await fetch(u.toString(), { cache: "no-store" });
	if (!r.ok) throw new Error(await r.text());
	return r.json();
}

function formatRefreshTime(ts) {
	return new Date(ts).toLocaleTimeString("ru-RU");
}

async function refreshAllDashboards() {
	const btn = document.getElementById("btn-refresh-all");
	const note = document.getElementById("refresh-note");
	btn.disabled = true;
	refreshToken = Date.now();
	note.textContent = "Обновление данных...";
	try {
		await Promise.all([
			loadAssociation(),
			loadSegmentation(),
			loadTemporal(),
		]);
		note.textContent = "Обновлено: " + formatRefreshTime(refreshToken);
	} catch (e) {
		note.textContent = "Ошибка обновления";
		alert(e.message);
	} finally {
		btn.disabled = false;
	}
}

/* --- Tabs --- */
document.querySelectorAll("#tab-nav button").forEach((btn) => {
	btn.addEventListener("click", () => {
		document.querySelectorAll("#tab-nav button").forEach((b) => b.classList.remove("active"));
		btn.classList.add("active");
		const id = btn.dataset.tab;
		document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
		document.getElementById("panel-" + (id === "assoc" ? "assoc" : id === "seg" ? "seg" : "temp")).classList.add("active");
	});
});

function ruleText(r) {
	const a = (r.antecedents || []).join(" ∧ ");
	const c = (r.consequents || []).join(", ");
	return a + " → " + c + " &nbsp; <small>(sup=" + r.support.toFixed(2) + ", conf=" + r.confidence.toFixed(2) + ", lift=" + r.lift.toFixed(2) + ")</small>";
}

async function loadAssociation() {
	const params = {
		dog_gender: document.getElementById("f-gender").value,
		age_bucket: document.getElementById("f-age").value,
		season: document.getElementById("f-season").value,
		region: document.getElementById("f-region").value.trim(),
	};
	const data = await fetchJson("/dashboards/association", params);
	const rulesEl = document.getElementById("assoc-rules");
	if (!data.rules || !data.rules.length) {
		rulesEl.innerHTML = "<p class='msg'>Нет правил при текущих фильтрах. Добавьте визиты в админке или ослабьте фильтры.</p>";
	} else {
		rulesEl.innerHTML = data.rules.slice(0, 50).map((r) => "<div class='rule-row'>" + ruleText(r) + "</div>").join("");
	}
	const nodes = (data.graph && data.graph.nodes) || [];
	const edges = (data.graph && data.graph.edges) || [];
	const container = document.getElementById("assoc-network");
	container.innerHTML = "";
	if (!nodes.length) {
		container.innerHTML = "<p class='msg'>Нет узлов (мало данных или слишком строгие фильтры).</p>";
		return;
	}
	const nodeIds = new Set(nodes.map((n) => n.id));
	const visNodes = new vis.DataSet(nodes.map((n) => ({
		id: n.id,
		label: n.label,
		group: n.group,
		title: n.id,
	})));
	const visEdges = new vis.DataSet(
		edges
			.filter((e) => nodeIds.has(e.from) && nodeIds.has(e.to))
			.map((e, i) => ({
				id: "e" + i,
				from: e.from,
				to: e.to,
				value: e.width,
				title: "lift=" + (e.lift != null ? e.lift.toFixed(2) : "?"),
			}))
	);
	new vis.Network(container, { nodes: visNodes, edges: visEdges }, {
		physics: { stabilization: { iterations: 120 } },
		edges: { scaling: { min: 1, max: 8 } },
	});
}

document.getElementById("btn-assoc-apply").addEventListener("click", () => loadAssociation().catch((e) => alert(e.message)));
loadAssociation().catch(() => { document.getElementById("assoc-rules").innerHTML = "<p class='msg'>Сервис аналитики недоступен.</p>"; });

document.getElementById("btn-seg-load").addEventListener("click", loadSegmentation);
async function loadSegmentation() {
	const k = document.getElementById("seg-k").value || "4";
	const data = await fetchJson("/dashboards/segmentation", { n_clusters: k });
	const sc = data.scatter || [];
	const byCluster = {};
	sc.forEach((p) => {
		const cid = String(p.cluster);
		if (!byCluster[cid]) byCluster[cid] = { x: [], y: [], text: [] };
		byCluster[cid].x.push(p.x);
		byCluster[cid].y.push(p.y);
		byCluster[cid].text.push(p.label + " (владелец " + p.owner_id + ")");
	});
	const traces = Object.keys(byCluster).sort((a, b) => Number(a) - Number(b)).map((cid) => ({
		x: byCluster[cid].x, y: byCluster[cid].y, mode: "markers", type: "scatter",
		name: "Кластер " + cid, text: byCluster[cid].text,
		marker: { size: 11 },
	}));
	if (!traces.length) {
		document.getElementById("scatter-plot").innerHTML = "<p class='msg'>Нет точек для t-SNE.</p>";
	} else {
		Plotly.newPlot("scatter-plot", traces, {
			title: "t-SNE проекция владельцев (по визитам)",
			xaxis: { title: "x" }, yaxis: { title: "y" },
		}, { responsive: true });
	}

	const cards = document.getElementById("cluster-cards");
	cards.innerHTML = (data.clusters || []).map((c) => {
		const svcs = (c.top_services || []).map((s, i) => (i + 1) + ". " + s).join("<br>");
		return "<div class='cluster-card'><h4>Кластер " + c.cluster_id + "</h4>" +
			"<div>Размер: " + c.size + "</div>" +
			"<div>Средний LTV: " + (c.avg_ltv || 0).toFixed(0) + " ₽</div>" +
			"<div>Средний возраст (мес.): " + (c.avg_age_months || 0).toFixed(0) + "</div>" +
			"<div><strong>Топ услуги</strong><br>" + (svcs || "—") + "</div></div>";
	}).join("") || "<p class='msg'>Нет данных</p>";
}

document.getElementById("btn-temp-load").addEventListener("click", loadTemporal);
async function loadTemporal() {
	const data = await fetchJson("/dashboards/temporal", {});
	const services = new Set();
	(data.heatmap || []).forEach((h) => services.add(h.service_name));
	const sel = document.getElementById("heat-service");
	const cur = sel.value;
	sel.innerHTML = '<option value="">Все услуги</option>' + [...services].sort().map((s) =>
		"<option value='" + String(s).replace(/'/g, "&#39;") + "'>" + s + "</option>").join("");
	sel.value = cur;

	const filterSvc = sel.value;
	const rows = {};
	const months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
	(data.heatmap || []).forEach((h) => {
		if (filterSvc && h.service_name !== filterSvc) return;
		const b = h.breed || "?";
		if (!rows[b]) rows[b] = {};
		rows[b][h.month] = (rows[b][h.month] || 0) + h.count;
	});
	const breedList = Object.keys(rows).sort();
	let html = "<thead><tr><th>Порода \\ Месяц</th>" + months.map((m) => "<th>" + m + "</th>").join("") + "</tr></thead><tbody>";
	let maxv = 1;
	breedList.forEach((b) => months.forEach((m) => { maxv = Math.max(maxv, rows[b][m] || 0); }));
	breedList.forEach((b) => {
		html += "<tr><th>" + b + "</th>";
		months.forEach((m) => {
			const v = rows[b][m] || 0;
			const inten = maxv ? Math.round(200 + 55 * (v / maxv)) : 255;
			const bg = "rgb(255," + (280 - inten) + "," + (240 - v * 3) + ")";
			html += "<td style='background:" + bg + "'>" + (v || "") + "</td>";
		});
		html += "</tr>";
	});
	html += "</tbody>";
	document.getElementById("heat-table").innerHTML = html;

	const cohort = data.cohort || [];
	const cols = data.service_columns || [];
	if (!cols.length) {
		document.getElementById("cohort-plot").innerHTML = "<p class='msg'>Нет когортных данных.</p>";
	} else {
		const tracesC = cols.map((col) => ({
			x: cohort.map((r) => r.age_bucket),
			y: cohort.map((r) => r[col] || 0),
			name: col,
			type: "bar",
		}));
		Plotly.newPlot("cohort-plot", tracesC, {
			barmode: "stack",
			title: "Доли услуг по возрастной группе собак (%)",
			xaxis: { title: "Возрастная группа" },
			yaxis: { title: "%" },
		}, { responsive: true });
	}
}

document.getElementById("heat-service").addEventListener("change", () => loadTemporal().catch((e) => alert(e.message)));
document.getElementById("btn-refresh-all").addEventListener("click", refreshAllDashboards);
loadSegmentation().catch(() => { });
loadTemporal().catch(() => { });