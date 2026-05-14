// Простой скрипт для показа/скрытия пароля
function togglePassword() {
	const passwordInput = document.getElementById('password');
	const toggleIcon = document.querySelector('.toggle-password');

	if (passwordInput.type === 'password') {
		passwordInput.type = 'text';
		toggleIcon.textContent = '🙈'; // Иконка "закрыть"
	} else {
		passwordInput.type = 'password';
		toggleIcon.textContent = '👁️'; // Иконка "показать"
	}
}

document.querySelector('form').addEventListener('submit', async function (event) {
	event.preventDefault();

	const login = document.getElementById('login').value;
	const password = document.getElementById('password').value;
	const submitBtn = document.querySelector('.submit-btn');

	submitBtn.disabled = true;
	submitBtn.textContent = 'Входим...';

	try {
		const body = new URLSearchParams();
		body.set('username', login);
		body.set('password', password);
		const response = await fetch('/api/proxy/token', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded'
			},
			body: body.toString()
		});

		const data = await response.json();

		if (response.ok) {
			localStorage.setItem('authToken', data.access_token);
			window.location.href = '/';
		} else {
			const msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data);
			alert('Ошибка: ' + (msg || 'Неверный логин или пароль'));
		}
	} catch (error) {
		console.error('Ошибка сети:', error);
		alert('Произошла ошибка соединения. Попробуйте позже.');
	} finally {
		submitBtn.disabled = false;
		submitBtn.textContent = 'Войти';
	}
});