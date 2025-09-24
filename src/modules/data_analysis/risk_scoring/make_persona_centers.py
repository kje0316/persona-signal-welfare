# -*- coding: utf-8 -*-
# make_persona_centers.py
# 원본 CSV → ensure_all_standardized_features → 8개 *_std로 KMeans → clusters.csv 저장

import os, argparse
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.cluster import KMeans

# 학습 파이프라인의 표준화 유틸 재사용
from .train_pipeline import ensure_year_month, ensure_all_standardized_features
from .persona_soft import CLUST_FEATS

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="telecom_group_monthly_all.csv 경로")
    ap.add_argument("--out", required=True, help="clusters.csv 저장 경로")
    ap.add_argument("--months", type=int, default=12, help="최근 N개월만 사용(기본 12)")
    ap.add_argument("--k", type=int, default=3, help="클러스터 개수(기본 3)")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df = ensure_year_month(df)
    df = ensure_all_standardized_features(df, month_col="year_month")

    # 최근 N개월만 사용
    last_m = sorted(df["year_month"].unique())[-args.months:]
    df_sub = df[df["year_month"].isin(last_m)].copy()

    # 결측/미존재 컬럼 0 보간
    for c in CLUST_FEATS:
        if c not in df_sub.columns:
            df_sub[c] = 0.0
    X = df_sub[CLUST_FEATS].astype(float).fillna(0.0).to_numpy()

    # KMeans
    km = KMeans(n_clusters=args.k, n_init=10, random_state=42)
    km.fit(X)

    centers = pd.DataFrame(km.cluster_centers_, columns=CLUST_FEATS)
    centers.index = [f"persona_{i}" for i in range(len(centers))]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    centers.to_csv(out_path, encoding="utf-8-sig")

    # 간단 프리뷰
    print("[DONE] clusters.csv saved →", out_path)
    print(centers.round(3).head())

if __name__ == "__main__":
    main()
