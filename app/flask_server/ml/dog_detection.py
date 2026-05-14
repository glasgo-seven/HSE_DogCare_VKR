import math
import os
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Optional

import cv2
import numpy as np
import requests
import torch
import torchvision.models as models
import torchvision.transforms as T
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO


API_INTERNAL = os.environ.get("API_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")
DETECTOR_MODEL = os.environ.get("DOG_DETECTOR_MODEL", "yolov8n.pt")
DOG_SIMILARITY_THRESHOLD = float(os.environ.get("DOG_SIMILARITY_THRESHOLD", "0.125"))
LIBRARY_SYNC_INTERVAL_SEC = float(os.environ.get("DOG_LIBRARY_SYNC_INTERVAL_SEC", "60"))
TRACK_STALE_SEC = float(os.environ.get("DOG_TRACK_STALE_SEC", "2.0"))
TRACK_MATCH_DISTANCE_PX = float(os.environ.get("DOG_TRACK_MATCH_DISTANCE_PX", "120"))
SPEED_SMOOTH_WINDOW = int(os.environ.get("DOG_SPEED_SMOOTH_WINDOW", "5"))
CALM_SPEED_MAX = float(os.environ.get("DOG_ACTIVITY_CALM_MAX", "0.18"))
MODERATE_SPEED_MAX = float(os.environ.get("DOG_ACTIVITY_MODERATE_MAX", "0.65"))
ACTIVITY_CONFIRM_FRAMES = int(os.environ.get("DOG_ACTIVITY_CONFIRM_FRAMES", "8"))
ACTIVITY_CONFIRM_SEC = float(os.environ.get("DOG_ACTIVITY_CONFIRM_SEC", "1.2"))
BBOX_MOVE_CENTER_THRESHOLD_RATIO = float(os.environ.get("DOG_BBOX_MOVE_CENTER_THRESHOLD_RATIO", "0.18"))
BBOX_MOVE_IOU_THRESHOLD = float(os.environ.get("DOG_BBOX_MOVE_IOU_THRESHOLD", "0.55"))

ACTIVITY_CALM = "спокоен"
ACTIVITY_MODERATE = "умеренно"
ACTIVITY_ACTIVE = "активен"

DOG_LIBRARY: dict[str, dict[str, Any]] = {}
TRACKS: dict[str, "ActivityTrack"] = {}
LAST_LIBRARY_SYNC = 0.0
UNKNOWN_TRACK_COUNTER = 0
CURRENT_CAMERA_INDEX: Optional[int] = None

ACTIVITY_CALM = "\u0441\u043f\u043e\u043a\u043e\u0435\u043d"
ACTIVITY_MODERATE = "\u0443\u043c\u0435\u0440\u0435\u043d\u043d\u043e"
ACTIVITY_ACTIVE = "\u0430\u043a\u0442\u0438\u0432\u0435\u043d"
FONT_CANDIDATES = [
	os.environ.get("DOG_OVERLAY_FONT", ""),
	r"C:\Windows\Fonts\arial.ttf",
	r"C:\Windows\Fonts\ArialNova.ttf",
	"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
	"/usr/share/fonts/dejavu/DejaVuSans.ttf",
]

detector = YOLO(DETECTOR_MODEL)
emb_model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
emb_model.fc = torch.nn.Identity()
emb_model.eval()
transform = T.Compose(
	[
		T.ToPILImage(),
		T.Resize(224),
		T.CenterCrop(224),
		T.ToTensor(),
		T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
	]
)


@dataclass
class ActivityTrack:
	track_key: str
	display_name: str
	dog_id: Optional[int] = None
	last_center: Optional[tuple[float, float]] = None
	last_bbox: Optional[tuple[int, int, int, int]] = None
	render_bbox: Optional[tuple[int, int, int, int]] = None
	last_seen_mono: Optional[float] = None
	last_seen_real: Optional[datetime] = None
	stable_level: Optional[str] = None
	stable_since: Optional[datetime] = None
	candidate_level: Optional[str] = None
	candidate_since_mono: Optional[float] = None
	candidate_since_real: Optional[datetime] = None
	candidate_count: int = 0
	speed_window: deque[float] = field(default_factory=lambda: deque(maxlen=SPEED_SMOOTH_WINDOW))
	period_id: Optional[int] = None
	period_speed_sum: float = 0.0
	period_sample_count: int = 0
	period_peak_speed: float = 0.0


class ActivityPeriodLogger:
	def __init__(self, api_base: str):
		self.api_base = api_base.rstrip("/")

	def _request(self, method: str, path: str, **kwargs) -> Optional[requests.Response]:
		try:
			return requests.request(method, f"{self.api_base}{path}", timeout=10, **kwargs)
		except requests.RequestException:
			return None

	def close_open_periods(self, dog_id: int, ended_at: datetime) -> None:
		resp = self._request(
			"GET",
			"/dog-activity-periods/",
			params={"dog_id": dog_id, "open_only": "true", "limit": 100},
		)
		if resp is None or not resp.ok:
			return
		try:
			rows = resp.json()
		except ValueError:
			return
		for row in rows:
			period_id = row.get("id")
			if period_id is None:
				continue
			self._request(
				"PATCH",
				f"/dog-activity-periods/{period_id}",
				json={"ended_at": ended_at.isoformat()},
				headers={"Content-Type": "application/json"},
			)

	def open_period(
		self,
		dog_id: int,
		activity_level: str,
		started_at: datetime,
		camera_index: Optional[int],
	) -> Optional[int]:
		self.close_open_periods(dog_id, started_at)
		resp = self._request(
			"POST",
			"/dog-activity-periods/",
			json={
				"dog_id": dog_id,
				"activity_level": activity_level,
				"started_at": started_at.isoformat(),
				"camera_index": camera_index,
			},
			headers={"Content-Type": "application/json"},
		)
		if resp is None or not resp.ok:
			return None
		try:
			body = resp.json()
		except ValueError:
			return None
		return body.get("id")

	def close_period(
		self,
		period_id: int,
		ended_at: datetime,
		avg_speed: Optional[float],
		peak_speed: Optional[float],
		sample_count: int,
	) -> None:
		self._request(
			"PATCH",
			f"/dog-activity-periods/{period_id}",
			json={
				"ended_at": ended_at.isoformat(),
				"avg_speed": avg_speed,
				"peak_speed": peak_speed,
				"sample_count": sample_count,
			},
			headers={"Content-Type": "application/json"},
		)


activity_logger = ActivityPeriodLogger(API_INTERNAL)


def _utc_now() -> datetime:
	return datetime.now(timezone.utc)


def _normalize_vector(vec: np.ndarray) -> np.ndarray:
	arr = np.asarray(vec, dtype=np.float32).reshape(-1)
	norm = float(np.linalg.norm(arr))
	if norm <= 1e-12:
		raise ValueError("Zero-norm embedding")
	return arr / norm


def get_embedding(img_bgr: np.ndarray) -> np.ndarray:
	if img_bgr is None or img_bgr.size == 0:
		raise ValueError("Empty image")
	img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
	x = transform(img_rgb).unsqueeze(0)
	with torch.no_grad():
		vec = emb_model(x).squeeze().cpu().numpy()
	return _normalize_vector(vec)


def create_dogid(
	_dog_name: str,
	_dog_reference_photos: list[str],
	dog_id: Optional[int] = None,
	display_name: Optional[str] = None,
):
	ref_embs: list[np.ndarray] = []
	for path in _dog_reference_photos:
		img = cv2.imread(path)
		if img is None or img.size == 0:
			continue
		ref_embs.append(get_embedding(img))
	if not ref_embs:
		raise ValueError("No valid reference photos")
	target_dog_id = _normalize_vector(np.mean(ref_embs, axis=0))
	DOG_LIBRARY[_dog_name] = {
		"dog_id": dog_id,
		"display_name": display_name or _dog_name,
		"vector": target_dog_id,
	}
	return target_dog_id


def sync_dog_library(force: bool = False) -> None:
	global LAST_LIBRARY_SYNC
	now = time.monotonic()
	if not force and now - LAST_LIBRARY_SYNC < LIBRARY_SYNC_INTERVAL_SEC:
		return
	try:
		resp = requests.get(f"{API_INTERNAL}/dog-embeddings/", timeout=20)
		resp.raise_for_status()
		rows = resp.json()
	except (requests.RequestException, ValueError):
		LAST_LIBRARY_SYNC = now
		return
	for row in rows:
		dog_id = row.get("dog_id")
		name = row.get("dog_name")
		mean_vector = row.get("mean_vector")
		if dog_id is None or not isinstance(mean_vector, list):
			continue
		try:
			vec = _normalize_vector(np.asarray(mean_vector, dtype=np.float32))
		except ValueError:
			continue
		key = f"dog_{dog_id}"
		DOG_LIBRARY[key] = {
			"dog_id": dog_id,
			"display_name": name or key,
			"vector": vec,
		}
	LAST_LIBRARY_SYNC = now


def set_camera_context(camera_index: Optional[int]) -> None:
	global CURRENT_CAMERA_INDEX
	CURRENT_CAMERA_INDEX = camera_index


def _reset_candidate(track: ActivityTrack) -> None:
	track.candidate_level = None
	track.candidate_since_mono = None
	track.candidate_since_real = None
	track.candidate_count = 0


def _reset_period_stats(track: ActivityTrack) -> None:
	track.period_speed_sum = 0.0
	track.period_sample_count = 0
	track.period_peak_speed = 0.0


def _record_period_sample(track: ActivityTrack, speed_value: float) -> None:
	track.period_speed_sum += speed_value
	track.period_sample_count += 1
	track.period_peak_speed = max(track.period_peak_speed, speed_value)


def _classify_activity(speed_value: float) -> str:
	if speed_value <= CALM_SPEED_MAX:
		return ACTIVITY_CALM
	if speed_value <= MODERATE_SPEED_MAX:
		return ACTIVITY_MODERATE
	return ACTIVITY_ACTIVE


def _track_color(level: Optional[str], recognized: bool) -> tuple[int, int, int]:
	if not recognized:
		return (0, 0, 255)
	if level == ACTIVITY_ACTIVE:
		return (0, 64, 255)
	if level == ACTIVITY_MODERATE:
		return (0, 200, 255)
	return (0, 255, 0)


def _bbox_iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
	ax1, ay1, ax2, ay2 = a
	bx1, by1, bx2, by2 = b
	ix1 = max(ax1, bx1)
	iy1 = max(ay1, by1)
	ix2 = min(ax2, bx2)
	iy2 = min(ay2, by2)
	if ix2 <= ix1 or iy2 <= iy1:
		return 0.0
	inter = float((ix2 - ix1) * (iy2 - iy1))
	area_a = float(max(ax2 - ax1, 0) * max(ay2 - ay1, 0))
	area_b = float(max(bx2 - bx1, 0) * max(by2 - by1, 0))
	den = area_a + area_b - inter
	if den <= 1e-6:
		return 0.0
	return inter / den


def _stabilize_bbox(
	prev_bbox: Optional[tuple[int, int, int, int]],
	new_bbox: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
	if prev_bbox is None:
		return new_bbox
	px1, py1, px2, py2 = prev_bbox
	nx1, ny1, nx2, ny2 = new_bbox
	prev_w = max(px2 - px1, 1)
	prev_h = max(py2 - py1, 1)
	prev_cx = (px1 + px2) / 2.0
	prev_cy = (py1 + py2) / 2.0
	new_cx = (nx1 + nx2) / 2.0
	new_cy = (ny1 + ny2) / 2.0
	center_dist = math.hypot(new_cx - prev_cx, new_cy - prev_cy)
	diag = math.hypot(prev_w, prev_h)
	move_threshold = max(8.0, diag * BBOX_MOVE_CENTER_THRESHOLD_RATIO)
	if center_dist <= move_threshold and _bbox_iou(prev_bbox, new_bbox) >= BBOX_MOVE_IOU_THRESHOLD:
		return prev_bbox
	return new_bbox


@lru_cache(maxsize=8)
def _get_overlay_font(font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
	for font_path in FONT_CANDIDATES:
		if font_path and os.path.isfile(font_path):
			try:
				return ImageFont.truetype(font_path, font_size)
			except OSError:
				continue
	return ImageFont.load_default()


def _draw_unicode_text(
	frame: np.ndarray,
	text: str,
	origin: tuple[int, int],
	color_bgr: tuple[int, int, int],
) -> None:
	font = _get_overlay_font(22)
	img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
	draw = ImageDraw.Draw(img)
	left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
	text_width = right - left
	text_height = bottom - top
	x = max(0, origin[0])
	y = max(0, origin[1] - text_height)
	bg_pad_x = 6
	bg_pad_y = 4
	draw.rounded_rectangle(
		[
			(x - bg_pad_x, y - bg_pad_y),
			(x + text_width + bg_pad_x, y + text_height + bg_pad_y),
		],
		radius=6,
		fill=(0, 0, 0),
	)
	draw.text((x, y), text, font=font, fill=(color_bgr[2], color_bgr[1], color_bgr[0]))
	frame[:] = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _close_track_period(track: ActivityTrack, ended_at: datetime) -> None:
	if track.period_id is None:
		return
	avg_speed = None
	if track.period_sample_count > 0:
		avg_speed = track.period_speed_sum / track.period_sample_count
	activity_logger.close_period(
		track.period_id,
		ended_at=ended_at,
		avg_speed=avg_speed,
		peak_speed=track.period_peak_speed if track.period_sample_count else None,
		sample_count=track.period_sample_count,
	)
	track.period_id = None
	_reset_period_stats(track)


def _open_track_period(track: ActivityTrack, started_at: datetime) -> None:
	_reset_period_stats(track)
	if track.dog_id is None or track.stable_level is None:
		track.period_id = None
		return
	track.period_id = activity_logger.open_period(
		track.dog_id,
		activity_level=track.stable_level,
		started_at=started_at,
		camera_index=CURRENT_CAMERA_INDEX,
	)


def reset_tracking_state(close_open_periods: bool = True) -> None:
	global UNKNOWN_TRACK_COUNTER
	now = _utc_now()
	for track in list(TRACKS.values()):
		if close_open_periods:
			_close_track_period(track, track.last_seen_real or now)
	TRACKS.clear()
	UNKNOWN_TRACK_COUNTER = 0


def _recognize_candidates(crop_emb: np.ndarray) -> list[dict[str, Any]]:
	candidates: list[dict[str, Any]] = []
	for key, meta in DOG_LIBRARY.items():
		sim = float(np.dot(crop_emb, meta["vector"]))
		if sim < DOG_SIMILARITY_THRESHOLD:
			continue
		candidates.append(
			{
				"key": key,
				"dog_id": meta.get("dog_id"),
				"display_name": str(meta.get("display_name") or key),
				"similarity": sim,
			}
		)
	candidates.sort(key=lambda item: item["similarity"], reverse=True)
	return candidates


def _match_existing_track(center: tuple[float, float], observed_keys: set[str], now_mono: float) -> Optional[str]:
	best_key: Optional[str] = None
	best_distance = float("inf")
	for key, track in TRACKS.items():
		if key in observed_keys or track.last_center is None or track.last_seen_mono is None:
			continue
		if now_mono - track.last_seen_mono > 1.0:
			continue
		distance = math.hypot(center[0] - track.last_center[0], center[1] - track.last_center[1])
		if distance <= TRACK_MATCH_DISTANCE_PX and distance < best_distance:
			best_key = key
			best_distance = distance
	return best_key


def _assign_unique_candidates(detections: list[dict[str, Any]]) -> None:
	used_dog_ids: set[int] = set()
	order = sorted(
		range(len(detections)),
		key=lambda idx: detections[idx]["candidates"][0]["similarity"] if detections[idx]["candidates"] else -1.0,
		reverse=True,
	)
	for idx in order:
		detection = detections[idx]
		chosen: Optional[dict[str, Any]] = None
		for candidate in detection["candidates"]:
			dog_id = candidate.get("dog_id")
			if dog_id is None:
				continue
			if dog_id in used_dog_ids:
				continue
			chosen = candidate
			used_dog_ids.add(dog_id)
			break
		detection["assigned_candidate"] = chosen


def _new_unknown_track_key() -> str:
	global UNKNOWN_TRACK_COUNTER
	UNKNOWN_TRACK_COUNTER += 1
	return f"unknown:{UNKNOWN_TRACK_COUNTER}"


def _ensure_track(track_key: str, display_name: str, dog_id: Optional[int]) -> ActivityTrack:
	track = TRACKS.get(track_key)
	if track is None:
		track = ActivityTrack(track_key=track_key, display_name=display_name, dog_id=dog_id)
		TRACKS[track_key] = track
	else:
		track.display_name = display_name
		if dog_id is not None:
			track.dog_id = dog_id
	return track


def _update_track_state(
	track: ActivityTrack,
	center: tuple[float, float],
	bbox_diag: float,
	now_mono: float,
	now_real: datetime,
) -> float:
	speed_value = 0.0
	if track.last_center is not None and track.last_seen_mono is not None:
		dt = max(now_mono - track.last_seen_mono, 1e-3)
		distance = math.hypot(center[0] - track.last_center[0], center[1] - track.last_center[1])
		speed_value = distance / max(bbox_diag, 1.0) / dt
	track.last_center = center
	track.last_seen_mono = now_mono
	track.last_seen_real = now_real
	track.speed_window.append(speed_value)
	smooth_speed = float(np.mean(track.speed_window))
	observed_level = _classify_activity(smooth_speed)

	if track.stable_level is None:
		track.stable_level = observed_level
		track.stable_since = now_real
		_reset_candidate(track)
		_open_track_period(track, now_real)
	elif observed_level == track.stable_level:
		_reset_candidate(track)
	else:
		if track.candidate_level == observed_level:
			track.candidate_count += 1
		else:
			track.candidate_level = observed_level
			track.candidate_since_mono = now_mono
			track.candidate_since_real = now_real
			track.candidate_count = 1
		if (
			track.candidate_count >= ACTIVITY_CONFIRM_FRAMES
			and track.candidate_since_mono is not None
			and now_mono - track.candidate_since_mono >= ACTIVITY_CONFIRM_SEC
		):
			transition_at = track.candidate_since_real or now_real
			_close_track_period(track, transition_at)
			track.stable_level = observed_level
			track.stable_since = transition_at
			_reset_candidate(track)
			_open_track_period(track, transition_at)

	_record_period_sample(track, smooth_speed)
	return smooth_speed


def _expire_stale_tracks(observed_keys: set[str], now_mono: float) -> None:
	for key, track in list(TRACKS.items()):
		if key in observed_keys or track.last_seen_mono is None:
			continue
		if now_mono - track.last_seen_mono < TRACK_STALE_SEC:
			continue
		_close_track_period(track, track.last_seen_real or _utc_now())
		del TRACKS[key]


def _draw_label(
	frame: np.ndarray,
	bbox: tuple[int, int, int, int],
	display_name: str,
	activity_level: Optional[str],
	recognized: bool,
) -> None:
	x1, y1, x2, y2 = bbox
	color = _track_color(activity_level, recognized)
	label = f"{display_name} | {activity_level or ACTIVITY_CALM}"
	cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
	_draw_unicode_text(frame, label, (x1, max(y1 - 10, 22)), color)


def detect_dogs(frame: np.ndarray) -> np.ndarray:
	sync_dog_library()
	results = detector(frame, conf=0.175, verbose=False)
	res = results[0]
	dog_mask = res.boxes.cls == 16
	dog_boxes = res.boxes.xyxy[dog_mask].cpu().numpy()
	now_mono = time.monotonic()
	now_real = _utc_now()
	observed_keys: set[str] = set()
	h, w = frame.shape[:2]
	detections: list[dict[str, Any]] = []

	for bbox in dog_boxes:
		x1, y1, x2, y2 = bbox.astype(int)
		x1 = max(0, min(x1, w - 1))
		y1 = max(0, min(y1, h - 1))
		x2 = max(x1 + 1, min(x2, w))
		y2 = max(y1 + 1, min(y2, h))
		crop = frame[y1:y2, x1:x2]
		if crop.size == 0:
			continue
		center = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
		candidates: list[dict[str, Any]] = []
		if DOG_LIBRARY:
			try:
				crop_emb = get_embedding(crop)
				candidates = _recognize_candidates(crop_emb)
			except ValueError:
				candidates = []
		detections.append(
			{
				"bbox": (x1, y1, x2, y2),
				"center": center,
				"candidates": candidates,
			}
		)

	_assign_unique_candidates(detections)

	used_frame_dog_ids: set[int] = set()
	for detection in detections:
		x1, y1, x2, y2 = detection["bbox"]
		center = detection["center"]
		assigned = detection.get("assigned_candidate")
		track_key: Optional[str] = None
		dog_id: Optional[int] = None
		display_name = "???"
		recognized = False
		if assigned:
			dog_id = assigned.get("dog_id")
			display_name = str(assigned.get("display_name") or "???")
			if dog_id is not None:
				track_key = f"dog:{dog_id}"
				recognized = True
		if track_key is None:
			track_key = _match_existing_track(center, observed_keys, now_mono) or _new_unknown_track_key()

		track = _ensure_track(track_key, display_name, dog_id)
		if track.display_name != "???" and display_name == "???":
			display_name = track.display_name
		else:
			track.display_name = display_name
		if dog_id is None and track.dog_id is not None:
			if track.dog_id not in used_frame_dog_ids:
				dog_id = track.dog_id
				recognized = True
			else:
				display_name = "???"
				track.display_name = display_name
				recognized = False
		if dog_id is not None:
			track.dog_id = dog_id
			used_frame_dog_ids.add(dog_id)
		track.last_bbox = (x1, y1, x2, y2)
		track.render_bbox = _stabilize_bbox(track.render_bbox, track.last_bbox)

		speed_value = _update_track_state(
			track,
			center=center,
			bbox_diag=math.hypot(x2 - x1, y2 - y1),
			now_mono=now_mono,
			now_real=now_real,
		)
		observed_keys.add(track_key)
		draw_bbox = track.render_bbox or track.last_bbox
		_draw_label(frame, draw_bbox, track.display_name, track.stable_level or _classify_activity(speed_value), recognized)

	_expire_stale_tracks(observed_keys, now_mono)
	return frame
