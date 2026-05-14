const PREFIX = "{{ api_proxy_prefix }}".replace(/\/$/, "");

async function loadBreeds() {
	const sel = document.getElementById("breed_id");
	try {
		const res = await fetch(PREFIX + "/breeds/");
		const data = await res.json();
		if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : res.status);
		sel.innerHTML = '<option value="">Выберите породу</option>' +
			data.map((b) => `<option value="${b.id}">${escapeHtml(b.name)}</option>`).join("");
	} catch (e) {
		sel.innerHTML = '<option value="">Ошибка загрузки пород</option>';
		console.error(e);
	}
}

function escapeHtml(s) {
	return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
}

document.getElementById("photos").addEventListener("change", (ev) => {
	const row = document.getElementById("preview-row");
	row.innerHTML = "";
	const files = ev.target.files;
	if (!files || !files.length) return;
	const n = Math.min(files.length, 8);
	for (let i = 0; i < n; i++) {
		const url = URL.createObjectURL(files[i]);
		const img = document.createElement("img");
		img.src = url;
		img.alt = "";
		row.appendChild(img);
	}
});

document.getElementById("reg-form").addEventListener("submit", async (e) => {
	e.preventDefault();
	const btn = document.getElementById("submit-btn");
	const msg = document.getElementById("form-msg");
	msg.textContent = "";
	msg.className = "msg";
	btn.disabled = true;
	const fd = new FormData(e.target);
	try {
		const res = await fetch("/api/register", { method: "POST", body: fd });
		const data = await res.json().catch(() => ({}));
		if (!res.ok) {
			const d = data.detail;
			msg.textContent = typeof d === "string" ? d : (d ? JSON.stringify(d) : "Ошибка " + res.status);
			msg.className = "msg err";
			btn.disabled = false;
			return;
		}
		document.getElementById("reg-form").style.display = "none";
		document.getElementById("success").style.display = "block";
		const o = data.owner || {};
		const d = data.dog || {};
		document.getElementById("success-summary").innerHTML =
			`Владелец: <strong>${escapeHtml(o.name)}</strong> (id ${o.id})<br/>` +
			`Питомец: <strong>${escapeHtml(d.name)}</strong>, порода ${escapeHtml(d.breed || "")}` +
			(data.dog_embedding
				? `<br/>DogID сохранён в <strong>dog_embeddings</strong> по <strong>${data.dog_embedding.source_photo_count}</strong> фото (размерность вектора ${data.dog_embedding.embedding_dim}).`
				: "");
		const ul = document.getElementById("rec-ul");
		const recs = data.service_recommendations || [];
		if (recs.length === 0) {
			ul.innerHTML = "<li>Пока нет устойчивых правил для выбранного профиля — загляните позже или посмотрите общую <a href=\"/analytics\">аналитику</a>.</li>";
		} else {
			ul.innerHTML = recs.map((r) =>
				`<li><strong>${escapeHtml(r.service)}</strong>` +
				`<div class="rec-meta">уверенность ${r.confidence}, lift ${r.lift}, support ${r.support}</div></li>`
			).join("");
		}
		const w = document.getElementById("rec-warn");
		if (data.recommendations_warning) {
			w.style.display = "block";
			w.textContent = data.recommendations_warning;
		}
	} catch (err) {
		msg.textContent = String(err.message || err);
		msg.className = "msg err";
	}
	btn.disabled = false;
});

loadBreeds();