document.addEventListener('DOMContentLoaded', function () {
	const guestNav = document.getElementById('guest-nav');
	const userNav = document.getElementById('user-nav');
	const logoutBtn = document.getElementById('logout-btn');

	const token = localStorage.getItem('authToken');

	if (token) {
		guestNav.style.display = 'none';
		userNav.style.display = 'flex';
	} else {
		guestNav.style.display = 'flex';
		userNav.style.display = 'none';
	}

	if (logoutBtn) {
		logoutBtn.addEventListener('click', function (e) {
			e.preventDefault();
			localStorage.removeItem('authToken');
			window.location.reload();
		});
	}

	/* --- Календарь и события дня --- */
	const MONTH_NAMES = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
	const WD_LABELS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

	let viewYear;
	let viewMonth;
	let selectedY;
	let selectedM;
	let selectedD;
	let eventsByDay = {};
	let eventsLoadError = false;

	function dateKey(y, m, d) {
		return y + '-' + String(m + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
	}

	function escapeHtml(s) {
		if (s == null) return '';
		return String(s)
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;');
	}

	async function loadEventsFromApi() {
		eventsByDay = {};
		eventsLoadError = false;
		try {
			const [schedRes, eventRes] = await Promise.all([
				fetch('/api/proxy/schedules/'),
				fetch('/api/proxy/events/')
			]);
			if (!schedRes.ok) throw new Error('HTTP ' + schedRes.status);
			if (!eventRes.ok) throw new Error('HTTP ' + eventRes.status);
			const schedules = await schedRes.json();
			const events = await eventRes.json();
			if (!Array.isArray(schedules) || !Array.isArray(events)) return;

			const eventsById = {};
			for (const ev of events) {
				eventsById[ev.id] = ev;
			}

			for (const sched of schedules) {
				if (!sched.time_start) continue;
				const dt = new Date(sched.time_start);
				if (Number.isNaN(dt.getTime())) continue;
				const key = dateKey(dt.getFullYear(), dt.getMonth(), dt.getDate());
				if (!eventsByDay[key]) eventsByDay[key] = [];
				const timeStr = dt.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
				const parts = [];
				const ev = eventsById[sched.event_id] || {};
				if (ev.manager_name) parts.push('Менеджер: ' + ev.manager_name);
				eventsByDay[key].push({
					time: timeStr,
					title: ev.name || 'Событие',
					sub: parts.join(' · ')
				});
			}
			Object.keys(eventsByDay).forEach((k) => {
				eventsByDay[k].sort((a, b) => a.time.localeCompare(b.time));
			});
		} catch (e) {
			eventsLoadError = true;
		}
	}

	function ensureSelectedInView() {
		if (selectedY !== viewYear || selectedM !== viewMonth) {
			const now = new Date();
			if (now.getFullYear() === viewYear && now.getMonth() === viewMonth) {
				selectedY = viewYear;
				selectedM = viewMonth;
				selectedD = now.getDate();
			} else {
				selectedY = viewYear;
				selectedM = viewMonth;
				selectedD = 1;
			}
		}
	}

	function renderCalendar() {
		const grid = document.getElementById('cal-grid');
		const title = document.getElementById('cal-title');
		title.textContent = MONTH_NAMES[viewMonth] + ' ' + viewYear;

		grid.innerHTML = '';
		WD_LABELS.forEach((w) => {
			const el = document.createElement('div');
			el.className = 'day-label';
			el.textContent = w;
			grid.appendChild(el);
		});

		const first = new Date(viewYear, viewMonth, 1);
		const startPad = (first.getDay() + 6) % 7;
		const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
		const today = new Date();

		for (let i = 0; i < startPad; i++) {
			const el = document.createElement('div');
			el.className = 'day-cell empty';
			grid.appendChild(el);
		}

		for (let d = 1; d <= daysInMonth; d++) {
			const el = document.createElement('div');
			el.className = 'day-cell selectable';
			el.textContent = String(d);
			const key = dateKey(viewYear, viewMonth, d);
			if (eventsByDay[key] && eventsByDay[key].length) el.classList.add('has-event');
			if (today.getFullYear() === viewYear && today.getMonth() === viewMonth && today.getDate() === d) {
				el.classList.add('today');
			}
			if (selectedY === viewYear && selectedM === viewMonth && selectedD === d) el.classList.add('active');
			el.addEventListener('click', () => {
				selectedY = viewYear;
				selectedM = viewMonth;
				selectedD = d;
				renderCalendar();
				renderDayEvents();
			});
			grid.appendChild(el);
		}
	}

	function renderDayEvents() {
		const titleEl = document.getElementById('events-day-title');
		const listEl = document.getElementById('day-events-list');
		const sel = new Date(selectedY, selectedM, selectedD);
		titleEl.textContent = 'События на ' + sel.toLocaleDateString('ru-RU', {
			day: 'numeric',
			month: 'long',
			year: 'numeric'
		});

		if (eventsLoadError) {
			listEl.innerHTML = '<p class="events-load-err">Не удалось загрузить события. Убедитесь, что сервис API запущен.</p>';
			return;
		}

		const key = dateKey(selectedY, selectedM, selectedD);
		const items = eventsByDay[key] || [];
		if (!items.length) {
			listEl.innerHTML = '<p class="events-empty">На этот день событий нет.</p>';
			return;
		}

		listEl.innerHTML = items.map((ev) => (
			'<div class="event-item">' +
			'<div class="event-time">' + escapeHtml(ev.time) + '</div>' +
			'<div class="event-details">' +
			'<h4>' + escapeHtml(ev.title) + '</h4>' +
			(ev.sub ? '<p>' + escapeHtml(ev.sub) + '</p>' : '') +
			'</div>' +
			'</div>'
		)).join('');
	}

	const now = new Date();
	viewYear = now.getFullYear();
	viewMonth = now.getMonth();
	selectedY = viewYear;
	selectedM = viewMonth;
	selectedD = now.getDate();

	loadEventsFromApi().then(() => {
		renderCalendar();
		renderDayEvents();
	});

	const prevBtn = document.getElementById('cal-prev');
	const nextBtn = document.getElementById('cal-next');
	if (prevBtn) {
		prevBtn.addEventListener('click', () => {
			viewMonth -= 1;
			if (viewMonth < 0) {
				viewMonth = 11;
				viewYear -= 1;
			}
			ensureSelectedInView();
			renderCalendar();
			renderDayEvents();
		});
	}
	if (nextBtn) {
		nextBtn.addEventListener('click', () => {
			viewMonth += 1;
			if (viewMonth > 11) {
				viewMonth = 0;
				viewYear += 1;
			}
			ensureSelectedInView();
			renderCalendar();
			renderDayEvents();
		});
	}
});