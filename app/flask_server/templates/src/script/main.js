(function () {
	function startClock(elementId, locale = 'ru-RU') {
		const el = document.getElementById(elementId);
		if (!el) return null;

		function tick() {
			el.textContent = new Date().toLocaleTimeString(locale);
		}

		tick();
		return window.setInterval(tick, 1000);
	}

	async function postJson(url, payload) {
		const response = await fetch(url, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload),
		});
		return response;
	}

	window.PetCareCommon = {
		startClock,
		postJson,
	};
})();
