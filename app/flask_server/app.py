import os
from urllib.parse import urlsplit, urlunsplit
from typing import Any, Optional

import requests
from flask import Flask, Response, jsonify, render_template, request, send_from_directory

from camera import check_cameras, get_frames, camera_list, open_camera, active_camera

try:
	from flask_cors import CORS
except ImportError:
	CORS = None

app = Flask(__name__)
if CORS:
	CORS(app)

app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

API_INTERNAL = os.environ.get("API_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")
ML_ANALYTICS_URL = os.environ.get("ML_ANALYTICS_URL", "http://127.0.0.1:8080").rstrip("/")

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DOGS_DIR = os.path.join(_BASE_DIR, "user_uploads", "dogs")
current_idx = 0

_SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "src")


def _upstream_candidates(base_url: str, fallback_port: int) -> list[str]:
	candidates = [base_url.rstrip("/")]
	parsed = urlsplit(base_url)
	host = (parsed.hostname or "").lower()
	if host not in {"127.0.0.1", "localhost"}:
		port = parsed.port or fallback_port
		local_url = urlunsplit((parsed.scheme or "http", f"127.0.0.1:{port}", parsed.path or "", "", "")).rstrip("/")
		if local_url not in candidates:
			candidates.append(local_url)
	return candidates


def _build_proxy_target(base_url: str, path: str) -> str:
	target = f"{base_url}/{path}" if path else f"{base_url}/"
	if request.query_string:
		target = target + ("&" if "?" in target else "?") + request.query_string.decode()
	return target


def _dog_age_bucket_years(age_years: Optional[int]) -> Optional[str]:
	if age_years is None:
		return None
	if age_years <= 1:
		return "0-1y"
	if age_years <= 4:
		return "2-4y"
	if age_years <= 8:
		return "5-8y"
	return "9+y"


def _association_request_params(
	dog_gender: Optional[bool],
	age_years: Optional[int],
	region: Optional[str],
) -> dict[str, str]:
	params: dict[str, str] = {}
	if dog_gender is not None:
		params["dog_gender"] = "true" if dog_gender else "false"
	bucket = _dog_age_bucket_years(age_years)
	if bucket:
		params["age_bucket"] = bucket
	if region and str(region).strip():
		params["region"] = str(region).strip()
	return params


def _association_fallback_attempts(params: dict[str, str]) -> list[dict[str, str]]:
	keys_priority = ["dog_gender", "age_bucket", "region"]
	attempts: list[dict[str, str]] = []
	seen: set[tuple[tuple[str, str], ...]] = set()

	def add_attempt(keys: list[str]) -> None:
		candidate = {k: params[k] for k in keys if k in params}
		marker = tuple(sorted(candidate.items()))
		if marker in seen:
			return
		seen.add(marker)
		attempts.append(candidate)

	present = [k for k in keys_priority if k in params]
	add_attempt(present)
	if not present:
		return attempts

	for drop_key in ("region", "age_bucket", "dog_gender"):
		add_attempt([k for k in present if k != drop_key])
	for keep_size in (2, 1):
		for start_idx in range(len(keys_priority)):
			keys: list[str] = []
			for key in keys_priority[start_idx:]:
				if key in params:
					keys.append(key)
				if len(keys) == keep_size:
					break
			add_attempt(keys)
	for key in keys_priority:
		add_attempt([key] if key in params else [])
	add_attempt([])
	return attempts


def _association_profile_label(params: dict[str, str]) -> str:
	parts: list[str] = []
	if params.get("dog_gender") in ("true", "false"):
		parts.append("пол")
	if params.get("age_bucket"):
		parts.append("возраст")
	if params.get("region"):
		parts.append("регион")
	if not parts:
		return "общим данным"
	return ", ".join(parts)


def _extract_service_recommendations(payload: dict[str, Any]) -> list[dict[str, Any]]:
	rules = payload.get("rules") or []
	best: dict[str, dict[str, Any]] = {}
	for rl in rules:
		conf = float(rl.get("confidence") or 0)
		lift = float(rl.get("lift") or 0)
		supp = float(rl.get("support") or 0)
		for c in rl.get("consequents") or []:
			if not isinstance(c, str) or not c.startswith("service:"):
				continue
			name = c.split(":", 1)[-1].strip()
			if not name:
				continue
			cur = best.get(name)
			if cur is None or conf > float(cur.get("confidence", 0)):
				best[name] = {
					"service": name,
					"confidence": round(conf, 4),
					"lift": round(lift, 4),
					"support": round(supp, 4),
				}
	return sorted(best.values(), key=lambda x: (-float(x["confidence"]), -float(x["lift"])))[:5]


def _service_recommendations_from_association(
	dog_gender: Optional[bool],
	age_years: Optional[int],
	region: Optional[str],
) -> tuple[list[dict[str, Any]], Optional[str]]:
	params: dict[str, str] = {}
	if dog_gender is not None:
		params["dog_gender"] = "true" if dog_gender else "false"
	bucket = _dog_age_bucket_years(age_years)
	if bucket:
		params["age_bucket"] = bucket
	if region and str(region).strip():
		params["region"] = str(region).strip()
	try:
		r = requests.get(f"{ML_ANALYTICS_URL}/dashboards/association", params=params, timeout=90)
		r.raise_for_status()
		payload = r.json()
	except requests.RequestException as exc:
		return [], f"Сервис аналитики недоступен: {exc}"
	except ValueError:
		return [], "Некорректный ответ аналитики"

	rules = payload.get("rules") or []
	best: dict[str, dict[str, Any]] = {}
	for rl in rules:
		conf = float(rl.get("confidence") or 0)
		lift = float(rl.get("lift") or 0)
		supp = float(rl.get("support") or 0)
		for c in rl.get("consequents") or []:
			if not isinstance(c, str) or not c.startswith("service:"):
				continue
			name = c.split(":", 1)[-1].strip()
			if not name:
				continue
			cur = best.get(name)
			if cur is None or conf > float(cur.get("confidence", 0)):
				best[name] = {
					"service": name,
					"confidence": round(conf, 4),
					"lift": round(lift, 4),
					"support": round(supp, 4),
				}
	out = sorted(best.values(), key=lambda x: -float(x["confidence"]))
	msg = payload.get("message")
	if not out and msg:
		return [], str(msg)
	return out, None


def _service_recommendations_from_association(
	dog_gender: Optional[bool],
	age_years: Optional[int],
	region: Optional[str],
) -> tuple[list[dict[str, Any]], Optional[str]]:
	params = _association_request_params(dog_gender, age_years, region)
	attempts = _association_fallback_attempts(params)
	last_message: Optional[str] = None
	for idx, attempt in enumerate(attempts):
		try:
			r = requests.get(f"{ML_ANALYTICS_URL}/dashboards/association", params=attempt, timeout=90)
			r.raise_for_status()
			payload = r.json()
		except requests.RequestException as exc:
			return [], f"Сервис аналитики недоступен: {exc}"
		except ValueError:
			return [], "Некорректный ответ аналитики"

		out = _extract_service_recommendations(payload)
		if out:
			if idx == 0:
				return out, None
			return out, (
				"Для точного профиля данных пока мало, поэтому рекомендации подобраны по более общему профилю "
				f"({_association_profile_label(attempt)})."
			)
		msg = payload.get("message")
		if isinstance(msg, str) and msg.strip():
			last_message = msg.strip()
	if last_message:
		return [], last_message
	return [], "Пока недостаточно данных для персональной рекомендации; общие правила тоже не дали устойчивых услуг."


def _merge_lookup_with_recommendations(lookup_json: dict[str, Any]) -> dict[str, Any]:
	owner = lookup_json.get("owner") or {}
	dogs = lookup_json.get("dogs") or []
	d0 = dogs[0] if dogs else {}
	g_raw = d0.get("gender")
	g_bool = g_raw if isinstance(g_raw, bool) else None
	age_raw = d0.get("age")
	age_int = age_raw if isinstance(age_raw, int) else None
	recs, warn = _service_recommendations_from_association(
		g_bool,
		age_int,
		owner.get("region"),
	)
	lookup_json = {**lookup_json, "service_recommendations": recs}
	if warn:
		lookup_json["recommendations_warning"] = warn
	return lookup_json


@app.route("/src/<path:filename>")
def serve_src(filename):
	return send_from_directory(_SRC_DIR, filename)


@app.route("/api/proxy/", defaults={"path": ""}, methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"])
@app.route("/api/proxy/<path:path>", methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"])
def api_proxy(path):
	"""Прокси к FastAPI: браузер ходит на тот же origin, Docker-сеть — на fastapi:8000."""
	if request.method == "OPTIONS":
		return Response(status=204)
	headers = {}
	for k, v in request.headers.items():
		if k.lower() in ("host", "content-length"):
			continue
		headers[k] = v
	errors = []
	upstream = None
	for base_url in _upstream_candidates(API_INTERNAL, 8000):
		target = _build_proxy_target(base_url, path)
		try:
			upstream = requests.request(
				method=request.method,
				url=target,
				headers=headers,
				data=request.get_data(),
				timeout=60,
			)
			break
		except requests.RequestException as exc:
			errors.append(f"{target}: {exc}")
	if upstream is None:
		message = " | ".join(errors) if errors else f"upstream unavailable for {path}"
		app.logger.warning("API proxy failed: %s", message)
		return jsonify({"error": message}), 502
	skip = {"content-encoding", "content-length", "transfer-encoding", "connection"}
	out = [(k, v) for k, v in upstream.headers.items() if k.lower() not in skip]
	return Response(upstream.content, status=upstream.status_code, headers=out)


@app.route("/api/ml/", defaults={"path": ""}, methods=["GET", "OPTIONS"])
@app.route("/api/ml/<path:path>", methods=["GET", "OPTIONS"])
def ml_proxy(path):
	"""Прокси к сервису ml_dashboards (дашборды JSON)."""
	if request.method == "OPTIONS":
		return Response(status=204)
	target = f"{ML_ANALYTICS_URL}/{path}" if path else f"{ML_ANALYTICS_URL}/"
	if request.query_string:
		target += ("&" if "?" in target else "?") + request.query_string.decode()
	try:
		upstream = requests.get(target, timeout=120)
	except requests.RequestException as exc:
		return jsonify({"error": str(exc)}), 502
	skip = {"content-encoding", "content-length", "transfer-encoding", "connection"}
	out = [(k, v) for k, v in upstream.headers.items() if k.lower() not in skip]
	return Response(upstream.content, status=upstream.status_code, headers=out)


@app.route("/analytics")
def analytics_page():
	return render_template("analytics.html")


@app.route("/")
def index():
	return render_template("index.html")


@app.route("/login")
def login_page():
	return render_template("login.html")


@app.route("/register")
def register_page():
	return render_template("register.html", api_proxy_prefix="/api/proxy")


@app.route("/uploads/dogs/<path:filename>")
def serve_dog_photo(filename):
	base = os.path.abspath(UPLOAD_DOGS_DIR)
	path = os.path.abspath(os.path.join(base, filename))
	if not path.startswith(base + os.sep) and path != base:
		return jsonify({"error": "invalid path"}), 400
	if not os.path.isfile(path):
		return jsonify({"error": "not found"}), 404
	return send_from_directory(UPLOAD_DOGS_DIR, filename)


@app.route("/api/register", methods=["POST"])
def api_register():
	"""Регистрация владельца + питомца; фото → только DogID (эмбеддинг в БД), файлы не хранятся."""
	name = (request.form.get("owner_name") or "").strip()
	if not name:
		return jsonify({"detail": "Укажите имя владельца"}), 400
	email = (request.form.get("owner_email") or "").strip()
	if not email:
		return jsonify({"detail": "Укажите email"}), 400
	owner_body: dict[str, Any] = {
		"name": name,
		"email": email,
		"phone": (request.form.get("owner_phone") or "").strip() or None,
		"region": (request.form.get("owner_region") or "").strip() or None,
	}
	age_o = request.form.get("owner_age")
	if age_o not in (None, ""):
		try:
			owner_body["age"] = int(age_o)
		except ValueError:
			return jsonify({"detail": "Некорректный возраст владельца"}), 400
	g_o = request.form.get("owner_gender")
	if g_o in ("true", "false"):
		owner_body["gender"] = g_o == "true"

	try:
		r_own = requests.post(
			f"{API_INTERNAL}/owners/",
			json=owner_body,
			headers={"Content-Type": "application/json"},
			timeout=30,
		)
	except requests.RequestException as exc:
		return jsonify({"detail": str(exc)}), 502
	if not r_own.ok:
		try:
			detail = r_own.json()
		except ValueError:
			detail = r_own.text
		return jsonify({"detail": detail}), r_own.status_code
	owner = r_own.json()

	dog_name = (request.form.get("dog_name") or "").strip()
	if not dog_name:
		requests.delete(f"{API_INTERNAL}/owners/{owner['id']}", timeout=15)
		return jsonify({"detail": "Укажите кличку питомца"}), 400
	try:
		breed_id = int(request.form.get("breed_id") or 0)
	except ValueError:
		requests.delete(f"{API_INTERNAL}/owners/{owner['id']}", timeout=15)
		return jsonify({"detail": "Выберите породу"}), 400
	if breed_id <= 0:
		requests.delete(f"{API_INTERNAL}/owners/{owner['id']}", timeout=15)
		return jsonify({"detail": "Выберите породу"}), 400

	dog_body: dict[str, Any] = {
		"name": dog_name,
		"breed_id": breed_id,
		"owner_id": owner["id"],
	}
	age_d = request.form.get("dog_age")
	if age_d not in (None, ""):
		try:
			dog_body["age"] = int(age_d)
		except ValueError:
			requests.delete(f"{API_INTERNAL}/owners/{owner['id']}", timeout=15)
			return jsonify({"detail": "Некорректный возраст питомца"}), 400
	g_d = request.form.get("dog_gender")
	if g_d in ("true", "false"):
		dog_body["gender"] = g_d == "true"

	try:
		r_dog = requests.post(
			f"{API_INTERNAL}/dogs/",
			json=dog_body,
			headers={"Content-Type": "application/json"},
			timeout=30,
		)
	except requests.RequestException as exc:
		requests.delete(f"{API_INTERNAL}/owners/{owner['id']}", timeout=15)
		return jsonify({"detail": str(exc)}), 502
	if not r_dog.ok:
		try:
			detail = r_dog.json()
		except ValueError:
			detail = r_dog.text
		requests.delete(f"{API_INTERNAL}/owners/{owner['id']}", timeout=15)
		return jsonify({"detail": detail}), r_dog.status_code
	dog = r_dog.json()

	photo_files = [
		f
		for f in request.files.getlist("photos")
		if f and getattr(f, "filename", None) and str(f.filename).strip()
	]
	dog_embedding = None
	n_used = 0
	if photo_files:
		paths: list[str] = []
		try:
			import tempfile

			import numpy as np

			from ml.dog_detection import create_dogid

			for fs in photo_files:
				suf = os.path.splitext(getattr(fs, "filename", "") or ".jpg")[1].lower()
				if suf not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
					suf = ".jpg"
				fd, path = tempfile.mkstemp(suffix=suf)
				os.close(fd)
				data = fs.read()
				if not data:
					try:
						os.unlink(path)
					except OSError:
						pass
					continue
				with open(path, "wb") as out:
					out.write(data)
				paths.append(path)
			if not paths:
				requests.delete(f"{API_INTERNAL}/dogs/{dog['id']}", timeout=15)
				requests.delete(f"{API_INTERNAL}/owners/{owner['id']}", timeout=15)
				return jsonify({"detail": "Пустые файлы фото"}), 400
			lib_key = f"dog_{dog['id']}"
			vec = create_dogid(lib_key, paths, dog_id=dog["id"], display_name=dog["name"])
			n_used = len(paths)
			arr = np.asarray(vec, dtype=np.float64).reshape(-1)
			nrm = float(np.linalg.norm(arr))
			if nrm > 1e-12:
				arr = arr / nrm
			proto = arr.astype(np.float32).tolist()
		except Exception as exc:
			requests.delete(f"{API_INTERNAL}/dogs/{dog['id']}", timeout=15)
			requests.delete(f"{API_INTERNAL}/owners/{owner['id']}", timeout=15)
			return jsonify({"detail": f"Не удалось построить DogID (create_dogid): {exc}"}), 400
		finally:
			for p in paths:
				try:
					os.unlink(p)
				except OSError:
					pass
		try:
			r_emb = requests.put(
				f"{API_INTERNAL}/dogs/{dog['id']}/embedding",
				json={"mean_vector": proto},
				headers={"Content-Type": "application/json"},
				timeout=120,
			)
		except requests.RequestException as exc:
			requests.delete(f"{API_INTERNAL}/dogs/{dog['id']}", timeout=15)
			requests.delete(f"{API_INTERNAL}/owners/{owner['id']}", timeout=15)
			return jsonify({"detail": str(exc)}), 502
		if not r_emb.ok:
			try:
				detail = r_emb.json()
			except ValueError:
				detail = r_emb.text
			requests.delete(f"{API_INTERNAL}/dogs/{dog['id']}", timeout=15)
			requests.delete(f"{API_INTERNAL}/owners/{owner['id']}", timeout=15)
			return jsonify({"detail": detail}), r_emb.status_code
		dog_embedding = r_emb.json()
		if isinstance(dog_embedding, dict):
			dog_embedding = {**dog_embedding, "source_photo_count": n_used}

	recs, warn = _service_recommendations_from_association(
		dog.get("gender"),
		dog.get("age"),
		owner.get("region"),
	)
	out: dict[str, Any] = {"owner": owner, "dog": dog, "service_recommendations": recs}
	if dog_embedding is not None:
		out["dog_embedding"] = dog_embedding
	if warn:
		out["recommendations_warning"] = warn
	return jsonify(out), 201


@app.route("/api/owner-lookup", methods=["GET"])
def api_owner_lookup():
	"""Поиск по телефону: владелец, собаки, события, рекомендации услуг (дашборд association)."""
	phone = (request.args.get("phone") or "").strip()
	if not phone:
		return jsonify({"detail": "Укажите phone"}), 400
	try:
		r = requests.get(f"{API_INTERNAL}/owners/lookup", params={"phone": phone}, timeout=30)
	except requests.RequestException as exc:
		return jsonify({"detail": str(exc)}), 502
	if r.status_code == 404:
		return Response(r.content, status=404, content_type=r.headers.get("Content-Type", "application/json"))
	if not r.ok:
		return Response(r.content, status=r.status_code, content_type=r.headers.get("Content-Type", "application/json"))
	try:
		data = r.json()
	except ValueError:
		return jsonify({"detail": "Некорректный ответ API"}), 502
	return jsonify(_merge_lookup_with_recommendations(data))


@app.route("/admin")
def admin():
	return render_template("admin.html", api_proxy_prefix="/api/proxy")


@app.route("/feed")
def feed():
	cam_switch = "".join(
		[
			f'<div class="camera-thumb active" onclick="switchCamera(this, {i})"><img src="/src/image/hero.png" alt=""><div class="camera-name">Камера {i}</div></div>'
			for i in camera_list
		]
	)
	html = render_template("feed.html").replace("${cam_list}", cam_switch)
	return html


@app.route("/switch", methods=["POST"])
def switch():
	global current_idx
	idx = request.get_json().get("index", 0)
	if idx != current_idx:
		open_camera(idx)
		current_idx = idx
	return jsonify({"status": "ok", "index": current_idx})


@app.route("/video_feed")
def video_feed():
	return Response(get_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
	check_cameras()

	if len(camera_list) == 0:
		print("No cameras found")
	else:
		open_camera(camera_list[0])
	app.run(host="0.0.0.0", port=5000, threaded=True)
