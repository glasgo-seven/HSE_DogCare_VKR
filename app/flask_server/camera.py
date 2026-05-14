import threading
import time

import cv2

from ml.dog_detection import detect_dogs, reset_tracking_state, set_camera_context, sync_dog_library


lock = threading.Lock()
active_camera = None
camera_list = []
TARGET_WIDTH = 640
TARGET_HEIGHT = 360
TARGET_FPS = 20

def check_cameras(_camera_amount: int = 10) -> list[int]:
	global camera_list
	for i in range(_camera_amount):
		active_camera = cv2.VideoCapture(i)
		if active_camera.isOpened():
			ret, frame = active_camera.read()
			print(f"Camera {i}: {'Available' if ret else 'Open but no frame'}")
			active_camera.release()
			if ret:
				camera_list.append(i)

def open_camera(index: int):
	global active_camera
	with lock:
		reset_tracking_state(close_open_periods=True)
		if active_camera: active_camera.release()
		# Windows: CAP_DSHOW or CAP_MSMF | Linux: CAP_V4L2 | macOS: CAP_AVFOUNDATION
		active_camera = cv2.VideoCapture(index, cv2.CAP_DSHOW)
		if not active_camera.isOpened():
			active_camera = cv2.VideoCapture(index)  # fallback
		if active_camera and active_camera.isOpened():
			active_camera.set(cv2.CAP_PROP_FRAME_WIDTH, TARGET_WIDTH)
			active_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_HEIGHT)
			active_camera.set(cv2.CAP_PROP_FPS, TARGET_FPS)
			active_camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
		set_camera_context(index)
		sync_dog_library(force=True)

def get_frames():
	frame_interval = 1.0 / TARGET_FPS
	next_frame_at = time.monotonic()
	while True:
		now = time.monotonic()
		if now < next_frame_at:
			time.sleep(next_frame_at - now)
		next_frame_at = max(next_frame_at + frame_interval, time.monotonic())

		with lock:
			if not active_camera or not active_camera.isOpened():
				time.sleep(0.05)
				continue
			success, frame = active_camera.read()
		if not success or frame is None or frame.size == 0:
			time.sleep(0.01)
			continue

		frame = detect_dogs(frame)
		if frame is None or frame.size == 0:
			time.sleep(0.01)
			continue

		_, buffer = cv2.imencode('.jpg', frame)
		yield (b'--frame\r\n'
			   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
