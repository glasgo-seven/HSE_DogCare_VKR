"""
Вычисления для трёх дашбордов: association mining, кластеризация клиентов, временные паттерны.
Данные — из PetCare API /analytics/ml-dataset.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import httpx
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler

try:
	from mlxtend.frequent_patterns import apriori, association_rules
	from mlxtend.preprocessing import TransactionEncoder
except ImportError:  # pragma: no cover
	apriori = None
	association_rules = None
	TransactionEncoder = None

PETCARE_API_URL = os.getenv("PETCARE_API_URL", "http://localhost:8000").rstrip("/")


def fetch_ml_dataset() -> list[dict[str, Any]]:
	with httpx.Client(timeout=60.0) as client:
		r = client.get(f"{PETCARE_API_URL}/analytics/ml-dataset")
		r.raise_for_status()
		data = r.json()
	return data if isinstance(data, list) else []


def _synthetic_dataset() -> list[dict[str, Any]]:
	"""Демо-данные, если в БД мало визитов."""
	base = [
		("Золотистый ретривер", "2-4y", True, "winter", "Москва", "Груминг", 1, 3500),
		("Золотистый ретривер", "2-4y", True, "winter", "Москва", "Груминг", 2, 3200),
		("Лабрадор", "2-4y", False, "spring", "СПб", "Ветеринар", 3, 5000),
		("Лабрадор", "5-8y", False, "spring", "СПб", "Груминг", 4, 4000),
		("Хаски", "0-1y", True, "summer", "Москва", "Дрессировка", 5, 6000),
		("Хаски", "2-4y", True, "summer", "Москва", "Дрессировка", 6, 5500),
		("Такса", "9+y", False, "autumn", "Казань", "Груминг", 7, 2800),
		("Такса", "9+y", False, "winter", "Казань", "Ветеринар", 8, 4500),
		("Золотистый ретривер", "5-8y", True, "winter", "Москва", "Ветеринар", 9, 5200),
		("Корги", "0-1y", False, "spring", "Москва", "Груминг", 10, 3100),
		("Корги", "2-4y", False, "spring", "Москва", "Груминг", 11, 3300),
		("Лабрадор", "2-4y", True, "summer", "Москва", "Груминг", 12, 3600),
	]
	out: list[dict[str, Any]] = []
	for i, (breed, age_b, dog_g, season, region, svc, dog_id, amt) in enumerate(base):
		out.append(
			{
				"visit_id": 9000 + i,
				"dog_id": dog_id,
				"dog_name": f"Dog{dog_id}",
				"breed_id": 1,
				"breed_name": breed,
				"breed_size_group": "medium",
				"breed_coat_group": "long" if "ретривер" in breed or "Хаски" in breed else "short",
				"dog_age_years": 3,
				"dog_age_months": 36,
				"age_bucket": age_b,
				"dog_gender": dog_g,
				"owner_id": 100 + dog_id,
				"owner_gender": dog_g,
				"owner_region": region,
				"service_id": 1 if "Груминг" in svc else 2,
				"service_name": svc,
				"service_category": "care",
				"visited_at": f"2025-{3 + (i % 9):02d}-{(i % 28) + 1:02d}T10:00:00",
				"month": 3 + (i % 9),
				"season": season,
				"amount_rub": amt,
			}
		)
	return out


def _ensure_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
	if len(rows) < 8:
		rows = _synthetic_dataset()
	df = pd.DataFrame(rows)
	return df


def _apply_filters(
	df: pd.DataFrame,
	dog_gender: Optional[str] = None,
	age_bucket: Optional[str] = None,
	season: Optional[str] = None,
	region: Optional[str] = None,
) -> pd.DataFrame:
	out = df.copy()
	if dog_gender is not None and dog_gender != "":
		g = dog_gender.lower() in ("true", "1", "m", "male", "муж")
		out = out[out["dog_gender"] == g]
	if age_bucket:
		out = out[out["age_bucket"] == age_bucket]
	if season:
		out = out[out["season"].astype(str).str.lower() == season.lower()]
	if region:
		out = out[out["owner_region"].astype(str).str.contains(region, case=False, na=False)]
	return out


def compute_association_dashboard(
	dog_gender: Optional[str] = None,
	age_bucket: Optional[str] = None,
	season: Optional[str] = None,
	region: Optional[str] = None,
	min_support: float = 0.08,
	min_confidence: float = 0.35,
) -> dict[str, Any]:
	try:
		rows = fetch_ml_dataset()
	except Exception:
		rows = []
	df = _ensure_df(rows)
	df = _apply_filters(df, dog_gender, age_bucket, season, region)
	if len(df) < 4:
		return {
			"rules": [],
			"graph": {"nodes": [], "edges": []},
			"message": "Недостаточно данных после фильтров",
			"n_rows": int(len(df)),
		}

	transactions: list[list[str]] = []
	for _, r in df.iterrows():
		items = [
			f"breed:{r.get('breed_name', '?')}",
			f"age:{r.get('age_bucket', '?')}",
			f"dog_sex:{'M' if r.get('dog_gender') is True else 'F' if r.get('dog_gender') is False else '?'}",
			f"season:{r.get('season', '?')}",
			f"region:{r.get('owner_region', '?')}",
			f"service:{r.get('service_name', '?')}",
		]
		transactions.append(items)

	if apriori is None or not transactions:
		return {"rules": [], "graph": {"nodes": [], "edges": []}, "message": "mlxtend не установлен", "n_rows": len(df)}

	te = TransactionEncoder()
	te_ary = te.fit(transactions).transform(transactions)
	dfo = pd.DataFrame(te_ary, columns=te.columns_)
	try:
		fi = apriori(dfo, min_support=min_support, use_colnames=True)
		if fi.empty:
			fi = apriori(dfo, min_support=0.05, use_colnames=True)
		if fi.empty:
			return {"rules": [], "graph": {"nodes": [], "edges": []}, "n_rows": len(df)}
		rules = association_rules(fi, metric="confidence", min_threshold=min_confidence)
	except Exception:
		return {"rules": [], "graph": {"nodes": [], "edges": []}, "n_rows": len(df)}

	rules_list: list[dict[str, Any]] = []
	for _, row in rules.head(40).iterrows():
		rules_list.append(
			{
				"antecedents": list(row["antecedents"]),
				"consequents": list(row["consequents"]),
				"support": float(row["support"]),
				"confidence": float(row["confidence"]),
				"lift": float(row["lift"]),
			}
		)

	nodes_map: dict[str, dict] = {}
	edges: list[dict[str, Any]] = []
	for rl in rules_list[:25]:
		lift = rl["lift"]
		for a in rl["antecedents"]:
			if a not in nodes_map:
				nodes_map[a] = {"id": a, "label": a.split(":", 1)[-1] if ":" in a else a, "group": a.split(":")[0]}
		for c in rl["consequents"]:
			if c not in nodes_map:
				nodes_map[c] = {"id": c, "label": c.split(":", 1)[-1] if ":" in c else c, "group": c.split(":")[0]}
		for a in rl["antecedents"]:
			for c in rl["consequents"]:
				edges.append(
					{
						"from": a,
						"to": c,
						"lift": lift,
						"support": rl["support"],
						"confidence": rl["confidence"],
						"width": min(8.0, max(1.0, float(lift))),
					}
				)

	return {
		"rules": rules_list,
		"graph": {"nodes": list(nodes_map.values()), "edges": edges},
		"n_rows": int(len(df)),
		"filters": {"dog_gender": dog_gender, "age_bucket": age_bucket, "season": season, "region": region},
	}


def compute_segmentation_dashboard(n_clusters: int = 4, random_state: int = 42) -> dict[str, Any]:
	try:
		rows = fetch_ml_dataset()
	except Exception:
		rows = []
	df = _ensure_df(rows)
	if df.empty:
		return {"clusters": [], "scatter": [], "message": "Нет данных"}

	# агрегация по владельцу
	def breed_group(name: Any) -> str:
		s = str(name or "")
		return s[:24]

	df["breed_group"] = df["breed_name"].apply(breed_group)
	df["amt"] = pd.to_numeric(df["amount_rub"], errors="coerce").fillna(0)

	agg = (
		df.groupby("owner_id", dropna=True)
		.agg(
			breed_group=("breed_group", lambda s: s.mode().iloc[0] if len(s.mode()) else "?"),
			age_months=("dog_age_months", "mean"),
			gender=("dog_gender", lambda s: float(pd.Series(s.dropna()).astype(float).mean()) if s.notna().any() else 0.0),
			visit_freq=("visit_id", "count"),
			avg_check=("amt", "mean"),
		)
		.reset_index()
	)
	agg["age_months"] = agg["age_months"].fillna(24.0)
	agg["visit_freq"] = agg["visit_freq"].clip(lower=1)

	X = agg[["age_months", "gender", "visit_freq", "avg_check"]].values
	top_breeds = agg["breed_group"].value_counts().head(12).index.tolist()
	bcols: list[str] = []
	for i, b in enumerate(top_breeds):
		col = f"b_{i}"
		agg[col] = (agg["breed_group"] == b).astype(float)
		bcols.append(col)
	if bcols:
		X = np.hstack([X, agg[bcols].values])

	scaler = StandardScaler()
	Xs = scaler.fit_transform(X)
	k = min(n_clusters, max(2, len(agg)))
	if len(agg) < 2:
		return {"clusters": [], "scatter": [], "message": "Мало владельцев для кластеризации", "n_owners": len(agg)}
	km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
	agg["cluster"] = km.fit_predict(Xs)

	perp = min(30, max(2, len(agg) - 1))
	tsne = TSNE(n_components=2, random_state=random_state, perplexity=perp)
	xy = tsne.fit_transform(Xs)
	agg["x"] = xy[:, 0]
	agg["y"] = xy[:, 1]

	profiles: list[dict[str, Any]] = []
	for cid in range(k):
		sub = df[df["owner_id"].isin(agg.loc[agg["cluster"] == cid, "owner_id"])]
		top_svc = sub["service_name"].value_counts().head(3)
		profiles.append(
			{
				"cluster_id": int(cid),
				"size": int((agg["cluster"] == cid).sum()),
				"top_services": top_svc.index.tolist(),
				"top_service_counts": top_svc.values.tolist(),
				"avg_ltv": float(
					sub.groupby("owner_id")["amount_rub"].sum().fillna(0).mean()
				) if len(sub) else 0.0,
				"avg_age_months": float(agg.loc[agg["cluster"] == cid, "age_months"].mean()),
				"gender_ratio_m": float(agg.loc[agg["cluster"] == cid, "gender"].mean()),
			}
		)

	scatter = [
		{
			"owner_id": int(r.owner_id),
			"cluster": int(r.cluster),
			"x": float(r.x),
			"y": float(r.y),
			"label": str(r.breed_group),
		}
		for r in agg.itertuples()
	]

	return {"clusters": profiles, "scatter": scatter, "n_owners": int(len(agg))}


def compute_temporal_dashboard() -> dict[str, Any]:
	try:
		rows = fetch_ml_dataset()
	except Exception:
		rows = []
	df = _ensure_df(rows)
	if df.empty:
		return {"heatmap": [], "cohort": [], "message": "Нет данных"}

	df["month"] = pd.to_numeric(df["month"], errors="coerce").fillna(1).astype(int).clip(1, 12)
	df["breed_short"] = df["breed_name"].astype(str).str[:20]

	heat = (
		df.groupby(["breed_short", "month", "service_name"], dropna=False)
		.size()
		.reset_index(name="count")
	)
	heatmap = heat.rename(columns={"breed_short": "breed"}).to_dict(orient="records")

	df["age_bucket"] = df["age_bucket"].fillna("unknown")
	pivot = pd.crosstab(df["age_bucket"], df["service_name"].fillna("?"), normalize="index") * 100
	cohort = pivot.reset_index().to_dict(orient="records")
	service_columns = [c for c in pivot.columns if c != "age_bucket"]

	return {"heatmap": heatmap, "cohort": cohort, "service_columns": service_columns}
