import os

import httpx
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from dashboard_engine import (
	compute_association_dashboard,
	compute_segmentation_dashboard,
	compute_temporal_dashboard,
)

PETCARE_API_URL = os.getenv("PETCARE_API_URL", "http://localhost:8000").rstrip("/")

app = FastAPI(title="PetCare ML / Analytics")
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/health")
def health():
	return {"status": "ok", "petcare_api": PETCARE_API_URL}


@app.get("/api/overview")
def api_overview():
	with httpx.Client(timeout=30.0) as client:
		r = client.get(f"{PETCARE_API_URL}/analytics/summary")
		r.raise_for_status()
		summary = r.json()
	return {"source": "petcare_api", "summary": summary}


@app.get("/api/recommendations")
def recommendations():
	with httpx.Client(timeout=30.0) as client:
		s = client.get(f"{PETCARE_API_URL}/analytics/summary").json()
	dogs = s.get("dogs", 0)
	events = s.get("events", 0)
	tips = []
	if dogs and not events:
		tips.append("Собаки есть в базе, но мероприятий нет — стоит запланировать групповое занятие.")
	if events > dogs * 2:
		tips.append("Много событий относительно числа собак — проверьте загрузку персонала.")
	if not tips:
		tips.append("Показатели в балансе; расширьте модель для персональных рекомендаций.")
	return {"recommendations": tips, "based_on": s}


@app.get("/dashboards/association")
def dashboards_association(
	dog_gender: str | None = Query(None, description="true=мужской пол собаки"),
	age_bucket: str | None = None,
	season: str | None = None,
	region: str | None = None,
	min_support: float = Query(0.08, ge=0.01, le=0.5),
	min_confidence: float = Query(0.35, ge=0.1, le=0.99),
):
	"""Association rules + graph for vis.js."""
	return compute_association_dashboard(
		dog_gender=dog_gender,
		age_bucket=age_bucket,
		season=season,
		region=region,
		min_support=min_support,
		min_confidence=min_confidence,
	)


@app.get("/dashboards/segmentation")
def dashboards_segmentation(n_clusters: int = Query(4, ge=2, le=12)):
	return compute_segmentation_dashboard(n_clusters=n_clusters)


@app.get("/dashboards/temporal")
def dashboards_temporal():
	return compute_temporal_dashboard()


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
	with httpx.Client(timeout=30.0) as client:
		summary = client.get(f"{PETCARE_API_URL}/analytics/summary").json()
	body = (
		"<!DOCTYPE html><html lang=\"ru\"><head><meta charset=\"utf-8\"/>"
		"<title>Аналитика PetCare</title>"
		"<style>body{font-family:system-ui,Segoe UI,sans-serif;max-width:800px;margin:40px auto;padding:0 16px}"
		"pre{background:#f5f7fa;border-radius:12px;padding:16px;overflow:auto}"
		"a{color:#2563eb}</style></head><body>"
		f"<h1>Аналитическая панель</h1>"
		f"<p>Источник данных: <code>{PETCARE_API_URL}</code> (FastAPI + PostgreSQL).</p>"
		f"<h2>Сводка</h2><pre>{summary}</pre>"
		"<p><a href=\"/api/overview\">JSON: /api/overview</a> · "
		"<a href=\"/dashboards/association\">Association</a> · "
		"<a href=\"/dashboards/segmentation\">Segmentation</a> · "
		"<a href=\"/dashboards/temporal\">Temporal</a></p>"
		"</body></html>"
	)
	return HTMLResponse(body)


@app.get("/")
def root():
	return {
		"service": "ml_dashboards",
		"petcare_api": PETCARE_API_URL,
		"endpoints": [
			"/health",
			"/dashboard",
			"/dashboards/association",
			"/dashboards/segmentation",
			"/dashboards/temporal",
		],
	}
