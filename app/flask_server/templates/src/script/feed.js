document.addEventListener('DOMContentLoaded', () => {
	const mainVideo = document.getElementById('main-video');

	window.switchCamera = async function switchCamera(element, idx) {
		document.querySelectorAll('.camera-thumb').forEach((el) => el.classList.remove('active'));
		element.classList.add('active');

		if (mainVideo) {
			mainVideo.style.opacity = '0.5';
		}

		try {
			await window.PetCareCommon.postJson('/switch', { index: idx });
			if (mainVideo) {
				mainVideo.src = '/video_feed?t=' + Date.now();
				mainVideo.style.opacity = '1';
			}
		} catch (err) {
			if (mainVideo) {
				mainVideo.style.opacity = '1';
			}
			console.error(err);
		}
	};

	window.PetCareCommon.startClock('clock');
});
