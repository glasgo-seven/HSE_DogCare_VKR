const PREFIX = "{{ api_proxy_prefix }}";

const resources = [
	{
		key: "owners",
		label: "Владельцы",
		list: "/owners/",
		tableColumns: [
			{ key: "id", header: "ID" },
			{ key: "name", header: "Имя" },
			{ key: "gender", header: "Пол", format: "gender" },
			{ key: "age", header: "Возраст" },
			{ key: "email", header: "Email" },
			{ key: "phone", header: "Телефон" },
			{ key: "region", header: "Локация" },
			{ key: "created_at", header: "Создано", format: "datetime" },
		],
		fields: [
			{ name: "name", label: "Имя", required: true },
			{ name: "gender", label: "Пол", widget: "gender" },
			{ name: "age", label: "Возраст", type: "number" },
			{ name: "email", label: "Email" },
			{ name: "phone", label: "Телефон" },
			{ name: "region", label: "Локация (регион)" },
		],
	},
	{
		key: "breeds",
		label: "Породы",
		list: "/breeds/",
		tableColumns: [
			{ key: "id", header: "ID" },
			{ key: "name", header: "Название" },
			{ key: "size_group", header: "Размер" },
			{ key: "coat_group", header: "Шерсть" },
		],
		fields: [
			{ name: "name", label: "Название", required: true },
			{ name: "size_group", label: "Группа размера (S/M/L)" },
			{ name: "coat_group", label: "Тип шерсти" },
		],
	},
	{
		key: "services",
		label: "Услуги",
		list: "/services/",
		tableColumns: [
			{ key: "id", header: "ID" },
			{ key: "name", header: "Услуга" },
			{ key: "category", header: "Категория" },
			{ key: "created_at", header: "Создано", format: "datetime" },
		],
		fields: [
			{ name: "name", label: "Название услуги", required: true },
			{ name: "category", label: "Категория" },
		],
	},
	{
		key: "dogs",
		label: "Собаки",
		list: "/dogs/",
		tableColumns: [
			{ key: "id", header: "ID" },
			{ key: "name", header: "Имя" },
			{ key: "age", header: "Возраст" },
			{ key: "gender", header: "Пол", format: "gender" },
			{ key: "breed", header: "Порода" },
			{ key: "breed_id", header: "ID породы" },
			{ key: "owner", header: "Владелец" },
			{ key: "owner_id", header: "ID владельца" },
			{ key: "photo_url", header: "Фото" },
			{ key: "created_at", header: "Создано", format: "datetime" },
		],
		fields: [
			{ name: "name", label: "Кличка", required: true },
			{ name: "age", label: "Возраст", type: "number" },
			{ name: "gender", label: "Пол", widget: "gender" },
			{ name: "breed_id", label: "Порода", required: true, widget: "select", optionsEndpoint: "/breeds/", optionValue: "id", optionLabel: "name" },
			{ name: "owner_id", label: "Владелец", required: true, widget: "select", optionsEndpoint: "/owners/", optionValue: "id", optionLabel: "name", optionFormat: "owner" },
			{ name: "photo_url", label: "Ссылка на фото" },
		],
	},
	{
		key: "visits",
		label: "Визиты (для ML)",
		list: "/visit-records/",
		tableColumns: [
			{ key: "id", header: "ID" },
			{ key: "dog_id", header: "ID собаки" },
			{ key: "service_id", header: "ID услуги" },
			{ key: "visited_at", header: "Визит", format: "datetime" },
			{ key: "amount_rub", header: "Сумма ₽" },
			{ key: "created_at", header: "Создано", format: "datetime" },
		],
		fields: [
			{ name: "dog_id", label: "Собака", required: true, widget: "select", optionsEndpoint: "/dogs/", optionValue: "id", optionFormat: "dog" },
			{ name: "service_id", label: "Услуга", required: true, widget: "select", optionsEndpoint: "/services/", optionValue: "id", optionLabel: "name" },
			{ name: "visited_at", label: "Дата и время визита", required: true, widget: "datetime" },
			{ name: "amount_rub", label: "Сумма, ₽", type: "number" },
		],
	},
	{
		key: "roles",
		label: "Роли",
		list: "/roles/",
		tableColumns: [
			{ key: "id", header: "ID" },
			{ key: "name", header: "Название" },
		],
		fields: [
			{ name: "name", label: "Роль", required: true },
		],
	},
	{
		key: "employees",
		label: "Сотрудники",
		list: "/employees/",
		tableColumns: [
			{ key: "id", header: "ID" },
			{ key: "name", header: "Имя" },
			{ key: "role", header: "Роль" },
			{ key: "role_id", header: "ID роли" },
			{ key: "gender", header: "Пол", format: "gender" },
			{ key: "age", header: "Возраст" },
			{ key: "email", header: "Email" },
			{ key: "phone", header: "Телефон" },
			{ key: "created_at", header: "Создано", format: "datetime" },
		],
		fields: [
			{ name: "name", label: "Имя", required: true },
			{ name: "gender", label: "Пол", widget: "gender" },
			{ name: "role_id", label: "Роль", required: true, widget: "select", optionsEndpoint: "/roles/", optionValue: "id", optionLabel: "name" },
			{ name: "age", label: "Возраст", type: "number" },
			{ name: "email", label: "Email" },
			{ name: "phone", label: "Телефон" },
		],
	},
	{
		key: "events",
		label: "События",
		list: "/events/",
		createMode: "event_bundle",
		tableColumns: [
			{ key: "id", header: "ID" },
			{ key: "name", header: "Название" },
			{ key: "manager_name", header: "Менеджер" },
			{ key: "manager_id", header: "ID менеджера" },
			{ key: "visitor_amount", header: "Число посетителей" },
			{ key: "duration_min", header: "Длительность (мин)" },
			{ key: "created_at", header: "Создано", format: "datetime" },
		],
		fields: [
			{ name: "name", label: "Название", required: true },
			{ name: "manager_id", label: "Менеджер", required: true, widget: "select", optionsEndpoint: "/employees/", optionValue: "id", optionFormat: "employee" },
			{ name: "dog_id", label: "Питомец (участник)", required: true, widget: "select", optionsEndpoint: "/dogs/", optionValue: "id", optionFormat: "dog" },
			{ name: "time_start", label: "Дата и время начала", required: true, widget: "datetime" },
			{ name: "duration_min", label: "Длительность (мин)", type: "number" },
		],
		editFields: [
			{ name: "name", label: "Название", required: true },
			{ name: "manager_id", label: "Менеджер", required: true, widget: "select", optionsEndpoint: "/employees/", optionValue: "id", optionFormat: "employee" },
			{ name: "visitor_amount", label: "Число посетителей", required: true, type: "number" },
			{ name: "duration_min", label: "Длительность (мин)", type: "number" },
		],
	},
	{
		key: "schedules",
		label: "Расписание",
		list: "/schedules/",
		listOnly: true,
		tableColumns: [
			{ key: "id", header: "ID" },
			{ key: "event_name", header: "Событие" },
			{ key: "manager_name", header: "Менеджер" },
			{ key: "time_start", header: "Начало", format: "datetime" },
			{ key: "time_end", header: "Конец", format: "datetime" },
			{ key: "participants", header: "Участники" },
			{ key: "created_at", header: "Создано", format: "datetime" },
		],
		fields: [
			{ name: "event_id", label: "Событие", required: true, widget: "select", optionsEndpoint: "/events/", optionValue: "id", optionLabel: "name" },
			{ name: "time_start", label: "Дата и время начала", required: true, widget: "datetime" },
		],
		editFields: [
			{ name: "event_id", label: "Событие", required: true, widget: "select", optionsEndpoint: "/events/", optionValue: "id", optionLabel: "name" },
			{ name: "time_start", label: "Дата и время начала", required: true, widget: "datetime" },
		],
	},
	{
		key: "participations",
		label: "Участия",
		list: "/participations/",
		listOnly: true,
		tableColumns: [
			{ key: "id", header: "ID" },
			{ key: "scheduled_event_id", header: "ID слота" },
			{ key: "visitor_id", header: "ID владельца" },
			{ key: "visitor_name", header: "Владелец" },
			{ key: "created_at", header: "Создано", format: "datetime" },
		],
		fields: [
			{ name: "scheduled_event_id", label: "Слот", required: true, widget: "select", optionsEndpoint: "/schedules/", optionValue: "id", optionFormat: "schedule" },
			{ name: "visitor_id", label: "Владелец", required: true, widget: "select", optionsEndpoint: "/owners/", optionValue: "id", optionLabel: "name", optionFormat: "owner" },
		],
		editFields: [
			{ name: "scheduled_event_id", label: "Слот", required: true, widget: "select", optionsEndpoint: "/schedules/", optionValue: "id", optionFormat: "schedule" },
			{ name: "visitor_id", label: "Владелец", required: true, widget: "select", optionsEndpoint: "/owners/", optionValue: "id", optionLabel: "name", optionFormat: "owner" },
		],
	},
];

let current = resources[0];
let currentRows = [];
let modalState = null;
const optionCache = new Map();

function showMsg(text, ok) {
	const el = document.getElementById("msg");
	el.textContent = text || "";
	el.className = "msg " + (ok ? "ok" : "err");
}

function showEditMsg(text, ok) {
	const el = document.getElementById("edit-modal-msg");
	el.textContent = text || "";
	el.className = "msg modal-msg " + (text ? (ok ? "ok" : "err") : "");
}

function escAttr(s) {
	return String(s ?? "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

function formatDateRu(iso) {
	if (iso == null || iso === "") return "";
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return String(iso);
	const dd = String(d.getDate()).padStart(2, "0");
	const mm = String(d.getMonth() + 1).padStart(2, "0");
	const yyyy = d.getFullYear();
	const hh = String(d.getHours()).padStart(2, "0");
	const min = String(d.getMinutes()).padStart(2, "0");
	return `${dd}.${mm}.${yyyy} ${hh}:${min}`;
}

function toDateTimeLocal(iso) {
	if (!iso) return "";
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return "";
	const yyyy = d.getFullYear();
	const mm = String(d.getMonth() + 1).padStart(2, "0");
	const dd = String(d.getDate()).padStart(2, "0");
	const hh = String(d.getHours()).padStart(2, "0");
	const min = String(d.getMinutes()).padStart(2, "0");
	return `${yyyy}-${mm}-${dd}T${hh}:${min}`;
}

function addMinutesToIso(iso, minutes) {
	if (!iso || minutes == null || Number.isNaN(Number(minutes))) return "";
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return "";
	d.setMinutes(d.getMinutes() + Number(minutes));
	return d.toISOString();
}

function formatGender(v) {
	if (v === true || v === "true") return "Мужской";
	if (v === false || v === "false") return "Женский";
	return "—";
}

function formatCell(col, row) {
	const v = row[col.key];
	if (col.format === "datetime") return formatDateRu(v);
	if (col.format === "gender") return formatGender(v);
	if (v === null || v === undefined) return "";
	return v;
}

function getCreateFields(resource) {
	return resource.fields || [];
}

function getEditFields(resource) {
	return resource.editFields || resource.fields || [];
}

function isEditable(resource) {
	return getEditFields(resource).length > 0;
}

function isNumericField(field) {
	return field.type === "number"
		|| field.name.endsWith("_id")
		|| field.name === "age"
		|| field.name === "visitor_amount"
		|| field.name === "duration_min"
		|| field.name === "amount_rub";
}

async function api(path, opts = {}) {
	const url = PREFIX.replace(/\/$/, "") + path;
	const res = await fetch(url, opts);
	const text = await res.text();
	let data;
	try { data = text ? JSON.parse(text) : null; } catch { data = text; }
	if (!res.ok) {
		const detail = data && data.detail ? JSON.stringify(data.detail) : text;
		throw new Error(res.status + " " + detail);
	}
	return data;
}

function buildTabs() {
	const tabs = document.getElementById("tabs");
	tabs.innerHTML = resources.map((r, i) =>
		`<button type="button" class="${i === 0 ? "active" : ""}" data-idx="${i}">${r.label}</button>`
	).join("");
	tabs.querySelectorAll("button").forEach((btn) => {
		btn.addEventListener("click", async () => {
			tabs.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
			btn.classList.add("active");
			current = resources[Number(btn.dataset.idx)];
			await renderForm();
			await loadList();
		});
	});
}

async function fetchOptions(endpoint) {
	if (optionCache.has(endpoint)) return optionCache.get(endpoint);
	const rows = await api(endpoint);
	const list = Array.isArray(rows) ? rows : [];
	optionCache.set(endpoint, list);
	return list;
}

function clearOptionCaches() {
	optionCache.clear();
}

async function buildFieldContext(fields) {
	const ctx = { ownersById: {}, eventsById: {} };
	const needOwners = fields.some((field) => field.optionFormat === "dog" || field.optionFormat === "owner");
	if (needOwners) {
		try {
			const owners = await fetchOptions("/owners/");
			for (const owner of owners) ctx.ownersById[owner.id] = owner.name;
		} catch {
			ctx.ownersById = {};
		}
	}
	const needEvents = fields.some((field) => field.optionFormat === "schedule");
	if (needEvents) {
		try {
			const events = await fetchOptions("/events/");
			for (const event of events) ctx.eventsById[event.id] = event.name;
		} catch {
			ctx.eventsById = {};
		}
	}
	return ctx;
}

function optionLabel(row, field, ctx) {
	if (field.optionFormat === "owner") {
		const name = row.name || "—";
		return row.email ? `${name} (${row.email})` : name;
	}
	if (field.optionFormat === "employee") {
		const name = row.name || "—";
		return row.email ? `${name} (${row.email})` : name;
	}
	if (field.optionFormat === "dog") {
		const pet = row.name || "—";
		const ownerName = ctx.ownersById[row.owner_id] ?? `владелец #${row.owner_id}`;
		return `${pet} — ${ownerName}`;
	}
	if (field.optionFormat === "schedule") {
		const eventName = ctx.eventsById[row.event_id] ?? `событие #${row.event_id}`;
		return `#${row.id} — ${eventName} — ${formatDateRu(row.time_start)}`;
	}
	return row[field.optionLabel || "name"] ?? row.id;
}

function fieldCurrentValue(field, values) {
	const value = values[field.name];
	if (field.widget === "gender") {
		if (value === true || value === "true") return "true";
		if (value === false || value === "false") return "false";
		return "";
	}
	if (field.widget === "datetime") {
		return toDateTimeLocal(value);
	}
	return value == null ? "" : String(value);
}

async function renderFieldsHtml(fields, values = {}) {
	const ctx = await buildFieldContext(fields);
	const parts = [];
	for (const field of fields) {
		const requiredAttr = field.required ? "required" : "";
		const value = fieldCurrentValue(field, values);
		if (field.widget === "gender") {
			parts.push(
				`<label>${escAttr(field.label)}<select name="${escAttr(field.name)}" ${requiredAttr}>`
				+ `<option value="">Не указано</option>`
				+ `<option value="true"${value === "true" ? " selected" : ""}>Мужской</option>`
				+ `<option value="false"${value === "false" ? " selected" : ""}>Женский</option>`
				+ `</select></label>`
			);
			continue;
		}
		if (field.widget === "select" && field.optionsEndpoint) {
			let rows = [];
			try {
				rows = await fetchOptions(field.optionsEndpoint);
			} catch {
				rows = [];
			}
			const options = rows.length
				? rows.map((row) => {
					const optionValue = row[field.optionValue || "id"];
					const label = optionLabel(row, field, ctx);
					return `<option value="${escAttr(optionValue)}"${String(optionValue) === value ? " selected" : ""}>${escAttr(label)}</option>`;
				}).join("")
				: `<option value="">Нет доступных записей</option>`;
			parts.push(`<label>${escAttr(field.label)}<select name="${escAttr(field.name)}" ${requiredAttr}>${options}</select></label>`);
			continue;
		}
		const type = field.widget === "datetime" ? "datetime-local" : (field.type || "text");
		parts.push(
			`<label>${escAttr(field.label)}`
			+ `<input name="${escAttr(field.name)}" type="${type}" value="${escAttr(value)}" ${requiredAttr} />`
			+ `</label>`
		);
	}
	return parts.join("");
}

function normalizeFieldValue(field, rawValue) {
	if (field.widget === "gender") {
		if (rawValue === "") return null;
		return rawValue === "true";
	}
	if (field.widget === "datetime") {
		return rawValue === "" ? null : new Date(rawValue).toISOString();
	}
	if (isNumericField(field)) {
		return rawValue === "" ? null : Number(rawValue);
	}
	return rawValue === "" ? null : rawValue;
}

function formDataToPayload(form, fields, { includeNulls }) {
	const fd = new FormData(form);
	const body = {};
	for (const field of fields) {
		const rawValue = fd.get(field.name);
		const value = normalizeFieldValue(field, rawValue == null ? "" : String(rawValue));
		if (value === null && !includeNulls) continue;
		body[field.name] = value;
	}
	return body;
}

async function renderForm() {
	const area = document.getElementById("form-area");
	const fields = getCreateFields(current);
	if (current.listOnly && fields.length === 0) {
		const note = current.key === "schedules"
			? "Расписание показывает уже конкретные слоты активностей: когда начинается и заканчивается активность, кто менеджер и кто записан."
			: "Для этой вкладки доступно редактирование и удаление через таблицу.";
		area.innerHTML = `<p class="helper-note">${note}</p>`;
		return;
	}
	const formInner = await renderFieldsHtml(fields);
	let note = "";
	if (current.key === "events") {
		note = `<p class="helper-note">События здесь — это список активностей: название, менеджер, вместимость и длительность. Время и участники относятся уже к расписанию.</p>`;
	} else if (current.key === "schedules") {
		note = `<p class="helper-note">Здесь можно добавить конкретный слот активности: выбрать событие и задать время начала.</p>`;
	} else if (current.key === "participations") {
		note = `<p class="helper-note">Здесь можно записать владельца на конкретный слот расписания.</p>`;
	}
	area.innerHTML = `${note}<form class="inline" id="create-form">${formInner}<button type="submit" class="primary-btn">Создать</button></form>`;
	document.getElementById("create-form").addEventListener("submit", async (e) => {
		e.preventDefault();
		try {
			if (current.createMode === "event_bundle") {
				await createEventBundle(e.target);
			} else {
				const body = formDataToPayload(e.target, fields, { includeNulls: false });
				await api(current.list, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(body),
				});
				showMsg("Создано", true);
			}
			e.target.reset();
			clearOptionCaches();
			await renderForm();
			await loadList();
		} catch (err) {
			showMsg(err.message, false);
		}
	});
}

async function createEventBundle(form) {
	const fd = new FormData(form);
	const name = String(fd.get("name") || "").trim();
	const managerId = Number(fd.get("manager_id"));
	const dogId = Number(fd.get("dog_id"));
	const timeLocal = String(fd.get("time_start") || "");
	const durationRaw = String(fd.get("duration_min") || "");
	if (!name || !managerId || !dogId || !timeLocal) {
		throw new Error("Заполните название, менеджера, питомца и дату/время");
	}
	const dogs = await api("/dogs/");
	const dog = Array.isArray(dogs) ? dogs.find((item) => item.id === dogId) : null;
	if (!dog) throw new Error("Питомец не найден");
	const eventBody = {
		name,
		manager_id: managerId,
		visitor_amount: 1,
		duration_min: durationRaw === "" ? null : Number(durationRaw),
	};
	const createdEvent = await api("/events/", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(eventBody),
	});
	const createdSchedule = await api("/schedules/", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ event_id: createdEvent.id, time_start: new Date(timeLocal).toISOString() }),
	});
	await api("/participations/", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({
			scheduled_event_id: createdSchedule.id,
			visitor_id: dog.owner_id,
		}),
	});
	showMsg("Событие, расписание и участие созданы", true);
}

function columnsFromRow(row) {
	return Object.keys(row).filter((key) => key !== "hashed_password");
}

async function enrichRowsForTable(rows, resource) {
	if (!Array.isArray(rows)) return rows;
	if (resource.key === "schedules") {
		let eventsById = {};
		let ownersById = {};
		let partsBySchedule = {};
		try {
			const events = await api("/events/");
			if (Array.isArray(events)) {
				for (const event of events) eventsById[event.id] = event;
			}
		} catch { }
		try {
			const owners = await api("/owners/");
			if (Array.isArray(owners)) {
				for (const owner of owners) ownersById[owner.id] = owner.name;
			}
		} catch { }
		try {
			const participations = await api("/participations/");
			if (Array.isArray(participations)) {
				for (const part of participations) {
					if (!partsBySchedule[part.scheduled_event_id]) partsBySchedule[part.scheduled_event_id] = [];
					const ownerName = ownersById[part.visitor_id] ?? `владелец #${part.visitor_id}`;
					partsBySchedule[part.scheduled_event_id].push(ownerName);
				}
			}
		} catch { }
		return rows.map((row) => {
			const event = eventsById[row.event_id] || {};
			const duration = event.duration_min;
			const participantNames = partsBySchedule[row.id] || [];
			return {
				...row,
				event_name: event.name ?? "",
				manager_name: event.manager_name ?? "",
				time_end: addMinutesToIso(row.time_start, duration),
				participants: participantNames.join(", "),
			};
		});
	}
	if (resource.key === "participations") {
		let owners = {};
		try {
			const list = await api("/owners/");
			if (Array.isArray(list)) {
				for (const owner of list) owners[owner.id] = owner.name;
			}
		} catch { }
		return rows.map((row) => ({ ...row, visitor_name: owners[row.visitor_id] ?? "" }));
	}
	return rows;
}

async function loadList() {
	showMsg("Загрузка…", true);
	try {
		let rows = await api(current.list);
		if (!Array.isArray(rows) || rows.length === 0) {
			currentRows = [];
			document.getElementById("thead").innerHTML = "";
			document.getElementById("tbody").innerHTML = `<tr><td class="empty-state">Нет записей</td></tr>`;
			showMsg("", true);
			return;
		}
		rows = await enrichRowsForTable(rows, current);
		currentRows = rows;
		const cols = current.tableColumns
			|| current.tableColumnOrder?.map((key) => ({ key, header: key }))
			|| columnsFromRow(rows[0]).map((key) => ({ key, header: key }));
		document.getElementById("thead").innerHTML = "<tr>"
			+ cols.map((col) => `<th>${escAttr(col.header || col.key)}</th>`).join("")
			+ "<th></th></tr>";
		document.getElementById("tbody").innerHTML = rows.map((row) => {
			const cells = cols.map((col) => `<td>${escAttr(String(formatCell(col, row)))}</td>`).join("");
			const editButton = isEditable(current)
				? `<button type="button" class="secondary-btn" data-action="edit" data-id="${row.id}">Изменить</button>`
				: "";
			return `<tr>${cells}<td class="row-actions">${editButton}<button type="button" class="danger-btn" data-action="del" data-id="${row.id}">Удалить</button></td></tr>`;
		}).join("");
		document.getElementById("tbody").querySelectorAll("button").forEach((btn) => {
			btn.addEventListener("click", onRowAction);
		});
		showMsg("", true);
	} catch (err) {
		showMsg(err.message, false);
	}
}

async function onRowAction(ev) {
	const id = Number(ev.target.dataset.id);
	const action = ev.target.dataset.action;
	const base = current.list.replace(/\/$/, "");
	if (action === "del") {
		if (!confirm("Удалить запись " + id + "?")) return;
		try {
			await api(base + "/" + id, { method: "DELETE" });
			showMsg("Удалено", true);
			clearOptionCaches();
			await renderForm();
			await loadList();
		} catch (err) {
			showMsg(err.message, false);
		}
		return;
	}
	if (action === "edit") {
		const row = currentRows.find((item) => Number(item.id) === id);
		if (!row) {
			showMsg("Запись не найдена в текущей таблице", false);
			return;
		}
		await openEditModal(current, row);
	}
}

async function openEditModal(resource, row) {
	modalState = { resource, row };
	document.getElementById("edit-modal-title").textContent = `Редактирование: ${resource.label}`;
	document.getElementById("edit-modal-subtitle").textContent = `ID ${row.id}`;
	document.getElementById("edit-form-fields").innerHTML = await renderFieldsHtml(getEditFields(resource), row);
	showEditMsg("", true);
	document.getElementById("edit-modal-backdrop").classList.add("open");
	document.getElementById("edit-modal-backdrop").setAttribute("aria-hidden", "false");
}

function closeEditModal() {
	modalState = null;
	document.getElementById("edit-modal-backdrop").classList.remove("open");
	document.getElementById("edit-modal-backdrop").setAttribute("aria-hidden", "true");
	document.getElementById("edit-form-fields").innerHTML = "";
	showEditMsg("", true);
}

async function submitEditForm(ev) {
	ev.preventDefault();
	if (!modalState) return;
	const { resource, row } = modalState;
	const fields = getEditFields(resource);
	const body = formDataToPayload(ev.target, fields, { includeNulls: true });
	try {
		await api(resource.list.replace(/\/$/, "") + "/" + row.id, {
			method: "PATCH",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body),
		});
		showMsg("Обновлено", true);
		closeEditModal();
		clearOptionCaches();
		await renderForm();
		await loadList();
	} catch (err) {
		showEditMsg(err.message, false);
	}
}

function renderPhoneLookup(data) {
	const el = document.getElementById("phone-lookup-result");
	const owner = data.owner || {};
	const dogs = data.dogs || [];
	const parts = data.participations || [];
	const recs = data.service_recommendations || [];
	let html = "<h3 style=\"font-size:15px;margin:12px 0 6px;\">Владелец</h3><pre>" + escAttr(JSON.stringify(owner, null, 2)) + "</pre>";

	html += "<h3 style=\"font-size:15px;margin:12px 0 6px;\">Рекомендации по услугам</h3>";
	if (data.recommendations_warning) {
		html += `<p class="msg err">${escAttr(data.recommendations_warning)}</p>`;
	}
	if (!recs.length) {
		html += "<p>Нет устойчивых правил для профиля первого питомца.</p>";
	} else {
		html += "<ul style=\"margin:0;padding-left:18px;\">";
		for (const rec of recs) {
			html += `<li><strong>${escAttr(rec.service)}</strong> — уверенность ${rec.confidence}, lift ${rec.lift}</li>`;
		}
		html += "</ul>";
	}

	html += "<h3 style=\"font-size:15px;margin:12px 0 6px;\">Собаки</h3>";
	if (!dogs.length) {
		html += "<p>Нет записей о питомцах.</p>";
	} else {
		html += "<table><thead><tr><th>ID</th><th>Кличка</th><th>Порода</th><th>Возраст</th><th>Пол</th><th>Фото</th></tr></thead><tbody>";
		for (const dog of dogs) {
			const photo = dog.photo_url ? `<a href="${escAttr(dog.photo_url)}" target="_blank" rel="noopener">ссылка</a>` : "—";
			html += `<tr><td>${dog.id}</td><td>${escAttr(dog.name)}</td><td>${escAttr(dog.breed)}</td><td>${dog.age ?? "—"}</td><td>${formatGender(dog.gender)}</td><td>${photo}</td></tr>`;
		}
		html += "</tbody></table>";
	}

	const embeddings = data.dog_embeddings || [];
	html += "<h3 style=\"font-size:15px;margin:12px 0 6px;\">dog_embeddings (DogID)</h3>";
	if (!embeddings.length) {
		html += "<p>Нет данных.</p>";
	} else {
		html += "<ul style=\"margin:0;padding-left:18px;\">";
		for (const item of embeddings) {
			const emb = item.embedding;
			if (!emb) {
				html += `<li>Собака id ${item.dog_id}: запись не создана</li>`;
			} else {
				html += `<li>Собака id ${item.dog_id}: dim ${emb.embedding_dim}, создано ${escAttr(formatDateRu(emb.created_at))}</li>`;
			}
		}
		html += "</ul>";
	}

	html += "<h3 style=\"font-size:15px;margin:12px 0 6px;\">Участие в событиях</h3>";
	if (!parts.length) {
		html += "<p>Нет записей.</p>";
	} else {
		html += "<table><thead><tr><th>Событие</th><th>Начало</th><th>ID слота</th></tr></thead><tbody>";
		for (const part of parts) {
			html += `<tr><td>${escAttr(part.event_name || "—")}</td><td>${escAttr(formatDateRu(part.time_start))}</td><td>${part.scheduled_event_id}</td></tr>`;
		}
		html += "</tbody></table>";
	}

	html += "<h3 style=\"font-size:15px;margin:12px 0 6px;\">Визиты (услуги)</h3>";
	const visits = data.visit_records || [];
	if (!visits.length) {
		html += "<p>Нет записей о визитах.</p>";
	} else {
		html += "<table><thead><tr><th>Питомец</th><th>Услуга</th><th>Дата</th><th>Сумма ₽</th></tr></thead><tbody>";
		for (const visit of visits) {
			html += `<tr><td>${escAttr(visit.dog_name || "")}</td><td>${escAttr(visit.service_name || "—")}</td><td>${escAttr(formatDateRu(visit.visited_at))}</td><td>${visit.amount_rub ?? "—"}</td></tr>`;
		}
		html += "</tbody></table>";
	}

	el.innerHTML = html;
}

document.getElementById("phone-lookup-btn").addEventListener("click", async () => {
	const phone = document.getElementById("phone-lookup-input").value.trim();
	const msg = document.getElementById("phone-lookup-msg");
	const out = document.getElementById("phone-lookup-result");
	out.innerHTML = "";
	if (!phone) {
		msg.textContent = "Введите номер телефона";
		msg.className = "msg err";
		return;
	}
	msg.textContent = "Загрузка…";
	msg.className = "msg ok";
	try {
		const res = await fetch("/api/owner-lookup?" + new URLSearchParams({ phone }));
		const text = await res.text();
		let data;
		try { data = text ? JSON.parse(text) : null; } catch { data = null; }
		if (!res.ok) {
			const detail = data && data.detail;
			msg.textContent = typeof detail === "string" ? detail : (res.status === 404 ? "Не найдено" : text.slice(0, 200));
			msg.className = "msg err";
			return;
		}
		msg.textContent = "";
		msg.className = "msg";
		renderPhoneLookup(data);
	} catch (e) {
		msg.textContent = String(e.message || e);
		msg.className = "msg err";
	}
});

document.getElementById("edit-form").addEventListener("submit", submitEditForm);
document.getElementById("edit-modal-close").addEventListener("click", closeEditModal);
document.getElementById("edit-cancel-btn").addEventListener("click", closeEditModal);
document.getElementById("edit-modal-backdrop").addEventListener("click", (ev) => {
	if (ev.target.id === "edit-modal-backdrop") closeEditModal();
});
document.addEventListener("keydown", (ev) => {
	if (ev.key === "Escape" && modalState) closeEditModal();
});

buildTabs();
(async function init() {
	await renderForm();
	await loadList();
})();