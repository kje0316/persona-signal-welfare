# -*- coding: utf-8 -*-
"""
clustering.py — 군집화 파이프라인 (K-sweep/안정성/커버리지/분리도/해석성)
"""
from __future__ import annotations

import os
import itertools
import warnings
from typing import List, Tuple, Dict
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import dump as joblib_dump

from sklearn.cluster import KMeans
from sklearn.metrics import (
    silhouette_score, calinski_harabasz_score, davies_bouldin_score,
    adjusted_rand_score, normalized_mutual_info_score,
)

from preprocess import ensure_year_month, prepare_features

# ── SciPy small-sample 경고 무시 (ks_2samp 등) ───────────────────────────────
try:
    from scipy.stats._warnings import SmallSampleWarning  # type: ignore
except Exception:
    try:
        from scipy.stats import SmallSampleWarning  # type: ignore
    except Exception:
        class SmallSampleWarning(Warning):
            pass

warnings.filterwarnings("ignore", category=SmallSampleWarning)
warnings.filterwarnings("ignore", message="One or more sample arguments is too small")

# ── 한글 폰트 (mac 기본 폰트 우선) ───────────────────────────────────────────
from matplotlib import font_manager, rcParams

APPLE_SD_PATHS = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
]

def use_korean_font():
    for p, name in [
        (APPLE_SD_PATHS[0], "Apple SD Gothic Neo"),
        (APPLE_SD_PATHS[1], "AppleGothic"),
    ]:
        if os.path.exists(p):
            try:
                font_manager.fontManager.addfont(p)
            except Exception:
                pass
            rcParams["font.family"] = name
            rcParams["font.sans-serif"] = [name]
            rcParams["axes.unicode_minus"] = False
            return
    rcParams["font.family"] = "DejaVu Sans"
    rcParams["axes.unicode_minus"] = False

use_korean_font()

# ── 하이퍼파라미터 ─────────────────────────────────────────────────────────
QUALITY_EXCLUDE_MONTHS = [
    pd.Timestamp("2024-06-01"),
    pd.Timestamp("2024-08-01"),
    pd.Timestamp("2024-09-01"),
]
K_RANGE = list(range(3, 13))
SAMPLE_MAX = 120_000
BOOT_ITERS = 10
BOOT_SAMPLE_FRAC = 0.7
HOLDOUT_START = pd.Timestamp("2024-07-01")
RECENT_COVER_MONTHS = 12
MIN_CLUSTER_RATIO = 0.03
RANDOM_STATE = 42


# ── 함수들 ──────────────────────────────────────────────────────────────────
def k_sweep(train_X: pd.DataFrame, train_month: pd.Series, k_list: List[int]) -> pd.DataFrame:
    out = []
    for K in k_list:
        km = KMeans(n_clusters=K, random_state=RANDOM_STATE, n_init="auto")
        labels = km.fit_predict(train_X)
        sil = silhouette_score(train_X, labels)
        ch = calinski_harabasz_score(train_X, labels)
        db = davies_bouldin_score(train_X, labels)

        size_ratio = pd.Series(labels).value_counts(normalize=True)
        recent_from = train_month.max() - pd.offsets.MonthBegin(RECENT_COVER_MONTHS - 1)
        recent_mask = train_month >= recent_from
        cov_ratio = (
            len(pd.Series(labels[recent_mask.values]).value_counts()) / K
            if recent_mask.any() else np.nan
        )

        out.append({
            "K": K,
            "silhouette": sil,
            "calinski_harabasz": ch,
            "davies_bouldin": db,
            "min_ratio": float(size_ratio.min()),
            "recent_coverage": cov_ratio,
        })
    return pd.DataFrame(out).sort_values("silhouette", ascending=False)


def stability_for_k(K: int, X: pd.DataFrame, months: pd.Series, iters: int = BOOT_ITERS) -> Dict[str, float]:
    rng = np.random.RandomState(RANDOM_STATE)

    base = KMeans(n_clusters=K, random_state=RANDOM_STATE, n_init="auto").fit(X)
    val_idx = X.sample(min(len(X) // 2, 50_000), random_state=RANDOM_STATE).index
    base_pred = base.predict(X.loc[val_idx])

    ari_list, nmi_list = [], []
    for _ in range(iters):
        boot_idx = X.sample(frac=BOOT_SAMPLE_FRAC, replace=True, random_state=rng.randint(0, 10**9)).index
        km = KMeans(n_clusters=K, random_state=rng.randint(0, 10**9), n_init="auto").fit(X.loc[boot_idx])
        pred = km.predict(X.loc[val_idx])
        ari_list.append(adjusted_rand_score(base_pred, pred))
        nmi_list.append(normalized_mutual_info_score(base_pred, pred))

    cut1 = HOLDOUT_START
    mask_recent = months >= cut1
    if mask_recent.any() and (~mask_recent).any():
        km_past = KMeans(n_clusters=K, random_state=RANDOM_STATE, n_init="auto").fit(X.loc[~mask_recent])
        lab_past = km_past.predict(X.loc[mask_recent])
        km_all = KMeans(n_clusters=K, random_state=RANDOM_STATE, n_init="auto").fit(X)
        lab_all = km_all.predict(X.loc[mask_recent])
        ari_hold = adjusted_rand_score(lab_all, lab_past)
        nmi_hold = normalized_mutual_info_score(lab_all, lab_past)
    else:
        ari_hold = nmi_hold = np.nan

    return {
        "ARI_boot_mean": float(np.mean(ari_list)),
        "ARI_boot_std": float(np.std(ari_list)),
        "NMI_boot_mean": float(np.mean(nmi_list)),
        "NMI_boot_std": float(np.std(nmi_list)),
        "ARI_holdout": float(ari_hold) if not np.isnan(ari_hold) else np.nan,
        "NMI_holdout": float(nmi_hold) if not np.isnan(nmi_hold) else np.nan,
    }


def size_coverage_report(train_X: pd.DataFrame, train_month: pd.Series, K: int) -> Tuple[pd.Series, np.ndarray]:
    km = KMeans(n_clusters=K, random_state=RANDOM_STATE, n_init="auto").fit(train_X)
    labels = km.labels_
    size = pd.Series(labels).value_counts(normalize=True).sort_index()

    recent_from = train_month.max() - pd.offsets.MonthBegin(RECENT_COVER_MONTHS - 1)
    denom = pd.Index(pd.period_range(recent_from, train_month.max(), freq="M")).to_timestamp()

    cover = []
    for k in range(K):
        months_k = train_month[labels == k].unique()
        cover.append(np.mean(denom.isin(months_k)))
    return size, np.array(cover)


def separability_table(train_X: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
    km = KMeans(n_clusters=len(np.unique(labels)), random_state=RANDOM_STATE, n_init="auto").fit(train_X)
    centers = pd.DataFrame(km.cluster_centers_, columns=train_X.columns)

    within_std = pd.DataFrame(index=sorted(np.unique(labels)), columns=train_X.columns)
    for k in sorted(np.unique(labels)):
        within_std.loc[k] = train_X[labels == k].std(ddof=0)

    pairs = []
    for a, b in itertools.combinations(sorted(np.unique(labels)), 2):
        dist = np.linalg.norm(centers.loc[a] - centers.loc[b])
        w = np.linalg.norm((within_std.loc[a] + within_std.loc[b]) / 2)
        pairs.append((a, b, dist / (w if w > 0 else 1e-6)))
    return pd.DataFrame(pairs, columns=["c1", "c2", "d_like"]).sort_values("d_like", ascending=False)


def run_clustering_pipeline(csv_path: str, exclude_months=None, k_range=K_RANGE):
    exclude_months = exclude_months if exclude_months is not None else QUALITY_EXCLUDE_MONTHS

    df = pd.read_csv(csv_path)
    df = ensure_year_month(df)
    if exclude_months:
        df = df[~df["year_month"].isin(exclude_months)].copy()

    df_norm, norm_cols = prepare_features(df)
    X = df_norm[norm_cols].replace([np.inf, -np.inf], np.nan).dropna()
    months = df_norm.loc[X.index, "year_month"]

    if len(X) > SAMPLE_MAX:
        X = X.sample(SAMPLE_MAX, random_state=RANDOM_STATE)
        months = months.loc[X.index]

    k_table = k_sweep(X, months, k_range)
    print("\n[K sweep 결과(상위 silhouette 순)]")
    print(k_table.head(10))

    topK = k_table.sort_values("silhouette", ascending=False).head(3)["K"].tolist()
    stab_rows = []
    for K in topK:
        s = stability_for_k(K, X, months, BOOT_ITERS)
        s["K"] = K
        stab_rows.append(s)
    stab_table = pd.DataFrame(stab_rows).set_index("K")
    print("\n[안정성(bootstrap/홀드아웃) 요약]")
    print(stab_table)

    K_pick = topK[0] if topK else k_range[0]
    size_ratio, cover_arr = size_coverage_report(X, months, K_pick)
    print(f"\n[크기/커버리지] K={K_pick}")
    print("클러스터 비중:", size_ratio.round(4).to_dict())
    print("최근 커버리지:", {i: round(float(v), 3) for i, v in enumerate(cover_arr)})

    km_pick = KMeans(n_clusters=K_pick, random_state=RANDOM_STATE, n_init="auto").fit(X)
    labels = km_pick.labels_
    sep_tbl = separability_table(X, labels)
    print("\n[분리도 상위 페어(d'-like)]")
    print(sep_tbl.head(10))

    row = k_table[k_table["K"] == K_pick].iloc[0]
    summary = {
        "K": K_pick,
        "silhouette_ok": bool(row["silhouette"] >= 0.25),
        "min_ratio_ok": bool(float(size_ratio.min()) >= MIN_CLUSTER_RATIO),
        "coverage_ok": bool((cover_arr > 0).all()),
        "stability_ok": bool(K_pick in stab_table.index and stab_table.loc[K_pick, "ARI_boot_mean"] >= 0.6),
        "holdout_ok": bool(
            (K_pick in stab_table.index)
            and (np.isnan(stab_table.loc[K_pick, "ARI_holdout"]) or stab_table.loc[K_pick, "ARI_holdout"] >= 0.6)
        ),
    }
    print("\n[합격선 체크 요약]")
    for k, v in summary.items():
        print(f"- {k}: {v}")

    return {
        "k_table": k_table,
        "stab_table": stab_table,
        "K_pick": K_pick,
        "labels": labels,
        "model": km_pick,
        "size_ratio": size_ratio,
        "cover_arr": cover_arr,
        "sep_table": sep_tbl,
        "summary": summary,
        "features": norm_cols,
        "X_index": X.index,
        "months": months,  # 저장 편의를 위해 포함
    }


# ── CLI ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Clustering pipeline")
    p.add_argument("--csv", default="telecom_group_monthly_all.csv")
    p.add_argument("--no-exclude", action="store_true", help="품질 이슈 월 제외하지 않음")
    p.add_argument("--kmin", type=int, default=3)
    p.add_argument("--kmax", type=int, default=12)
    # 저장 옵션 추가
    p.add_argument("--save-labels", type=str, default=None, help="클러스터 라벨 CSV 저장 경로")
    p.add_argument("--save-model", type=str, default=None, help="KMeans 모델 joblib 저장 경로")
    args = p.parse_args()

    exclude = [] if args.no_exclude else QUALITY_EXCLUDE_MONTHS
    res = run_clustering_pipeline(args.csv, exclude, list(range(args.kmin, args.kmax + 1)))

    # 라벨 저장 (샘플링이 적용된 경우, 해당 샘플 행만 저장됨)
    if args.save_labels:
        out_path = Path(args.save_labels)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df_lab = pd.DataFrame(index=res["X_index"])
        df_lab["cluster"] = res["labels"]
        df_lab["year_month"] = pd.to_datetime(res["months"]).dt.strftime("%Y-%m-%d")
        df_lab["K"] = res["K_pick"]
        df_lab.reset_index(names="row_id").to_csv(out_path, index=False)
        print(f"\n[저장] 라벨 → {out_path}")

    # 모델 저장
    if args.save_model:
        out_path = Path(args.save_model)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        joblib_dump(res["model"], out_path)
        print(f"[저장] 모델 → {out_path}")
