# src/modules/data_analysis/clustering.py
# -*- coding: utf-8 -*-
"""
Clustering: 페르소나 군집화 모듈
- (선택) per-capita + 월내 표준화 후 월평균으로 축약
- K sweep (silhouette/CH/DB/최소비율) → 최적 K 선택
- KMeans 학습 → 하드 라벨 + 소프트 확률(거리 기반 softmax)
- 라벨 메타(중심/특징)와 함께 CSV로 저장
"""
from __future__ import annotations
import numpy as np, pandas as pd, argparse, sys, warnings
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
warnings.filterwarnings("ignore")

from .eda import ensure_year_month, make_per_capita, monthwise_robust_z_log1p

# ---------------- 전처리 ----------------
def aggregate_by_unit_month(df: pd.DataFrame, unit_cols: list[str], month_col: str, use_cols: list[str]) -> pd.DataFrame:
    """unit x month 수준에서 평균(또는 합계)로 축약. 여기선 평균 사용."""
    keep = [c for c in use_cols if c in df.columns]
    g = df.groupby(unit_cols + [month_col], dropna=False)[keep].mean().reset_index()
    return g

def month_to_overall(dfm: pd.DataFrame, unit_cols: list[str], month_col: str, use_cols: list[str]) -> pd.DataFrame:
    """월 차원 제거(평균) → 최종 군집 입력 테이블"""
    return dfm.groupby(unit_cols, dropna=False)[use_cols].mean().reset_index()

def k_sweep_score(X: np.ndarray, K_list: list[int]) -> pd.DataFrame:
    rows=[]
    for k in K_list:
        if k <= 1 or k >= len(X):
            continue
        km = KMeans(n_clusters=k, n_init="auto", random_state=42)
        lab = km.fit_predict(X)
        # 빈 클러스터 방지 체크
        counts = np.bincount(lab, minlength=k)
        min_ratio = counts.min() / counts.sum()
        # 지표
        sil = silhouette_score(X, lab)
        ch  = calinski_harabasz_score(X, lab)
        db  = davies_bouldin_score(X, lab)
        rows.append([k, sil, ch, db, float(min_ratio)])
    return pd.DataFrame(rows, columns=["K","silhouette","calinski_harabasz","davies_bouldin","min_ratio"]).sort_values("silhouette", ascending=False)

def soft_membership_from_dist(dists: np.ndarray, temperature: float=1.0) -> np.ndarray:
    """
    KMeans.transform으로 얻은 거리(d_ik) → '가까울수록 확률↑' 되도록 softmax(-d/T)
    """
    logits = -dists / max(1e-8, temperature)
    logits -= logits.max(axis=1, keepdims=True)
    probs = np.exp(logits); probs /= probs.sum(axis=1, keepdims=True)
    return probs

# ---------------- 상위 API ----------------
def persona_clustering(
    df: pd.DataFrame,
    unit_cols: list[str],
    month_col: str="year_month",
    one_col: str|None=None,
    feature_cols: list[str]|None=None,
    do_per_capita: bool=True,
    do_month_std: bool=True,
    K_list: list[int]|None=None,
    pick_rule: str="best_silhouette",   # or "balance" (=silhouette 우선 + min_ratio 페널티)
    temperature: float=1.0,
):
    """
    반환:
      labels_df: unit 키 + 하드라벨 + 소프트확률 컬럼
      model_info: {centers, scaler_mean/scale, K, scores_table}
    """
    if K_list is None:
        K_list = [3,4,5,6,7,8,9]

    df = ensure_year_month(df, month_col)

    # feature 선택
    if feature_cols is None:
        # 기본 후보(예시): 이동/디지털/통화/체류 등
        candidates = [
            "평일 총 이동 거리 합계",
            "지하철이동일수 합계",
            "배달 서비스 사용일수",
            "동영상/방송 서비스 사용일수",
            "평균 통화량",
            "집 추정 위치 평일 총 체류시간",
        ]
        feature_cols = [c for c in candidates if c in df.columns]

    # per-capita
    work = df.copy()
    if do_per_capita and one_col:
        work = make_per_capita(work, feature_cols, one_col)
        feature_cols = [c+"_pc" for c in feature_cols]

    # 월내 표준화
    if do_month_std:
        work = monthwise_robust_z_log1p(work, feature_cols, month_col)
        feature_cols = [c+"_std" for c in feature_cols]

    # unit x month 축약 → unit 레벨 평균
    dfm = aggregate_by_unit_month(work, unit_cols, month_col, feature_cols)
    base = month_to_overall(dfm, unit_cols, month_col, feature_cols)

    # 스케일
    scaler = StandardScaler()
    X = scaler.fit_transform(base[feature_cols].fillna(0.0).values)

    # K sweep
    sweep = k_sweep_score(X, K_list)
    if sweep.empty:
        raise ValueError("K sweep 결과가 비었습니다. feature/표본 수를 확인하세요.")

    if pick_rule == "balance":
        # silhouette 우선 + min_ratio(0.03 미만 패널티) 간단히 적용
        sc = sweep.copy()
        sc["score"] = sc["silhouette"] - (sc["min_ratio"] < 0.03) * 0.1
        bestK = int(sc.sort_values(["score","silhouette"], ascending=False).iloc[0]["K"])
    else:
        bestK = int(sweep.iloc[0]["K"])

    # 최종 학습
    km = KMeans(n_clusters=bestK, n_init="auto", random_state=42)
    labels = km.fit_predict(X)
    dists  = km.transform(X)
    probs  = soft_membership_from_dist(dists, temperature=temperature)  # (N, K)

    # 결과 정리
    out = base[unit_cols].copy()
    out["persona_id"] = labels
    for k in range(bestK):
        out[f"persona_p{k}"] = probs[:,k]

    model_info = {
        "K": bestK,
        "centers": km.cluster_centers_.tolist(),
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "scores_table": sweep.to_dict(orient="list"),
        "feature_cols": feature_cols,
    }
    return out, model_info

# ---------------- CLI ----------------
def _build_argparser():
    ap = argparse.ArgumentParser(description="페르소나 군집화 (KMeans, soft membership)")
    ap.add_argument("--csv_path", default="telecom_group_monthly_all.csv")
    ap.add_argument("--unit_cols", default="자치구,행정동,성별,연령대")
    ap.add_argument("--month_col", default="year_month")
    ap.add_argument("--one_col", default="1인가구수")
    ap.add_argument("--features", default="")  # 콤마구분. 비우면 기본 후보 자동 선택
    ap.add_argument("--no_per_capita", action="store_true")
    ap.add_argument("--no_month_std", action="store_true")
    ap.add_argument("--K_list", default="3,4,5,6,7,8,9")
    ap.add_argument("--pick_rule", default="best_silhouette", choices=["best_silhouette","balance"])
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--out_csv", default="persona_labels.csv")
    ap.add_argument("--out_info_json", default=None)
    return ap

def main():
    import json
    args = _build_argparser().parse_args()
    df = pd.read_csv(args.csv_path)
    unit_cols = [c for c in args.unit_cols.split(",") if c]
    feature_cols = [c for c in args.features.split(",") if c] if args.features else None
    K_list = [int(k) for k in args.K_list.split(",") if k]

    labels_df, info = persona_clustering(
        df=df,
        unit_cols=unit_cols,
        month_col=args.month_col,
        one_col=None if args.no_per_capita else args.one_col,
        feature_cols=feature_cols,
        do_per_capita=not args.no_per_capita and bool(args.one_col),
        do_month_std=not args.no_month_std,
        K_list=K_list,
        pick_rule=args.pick_rule,
        temperature=args.temperature,
    )
    labels_df.to_csv(args.out_csv, index=False, encoding="utf-8-sig")
    print(f"✅ 라벨 저장: {args.out_csv} (rows={len(labels_df)})")

    if args.out_info_json:
        with open(args.out_info_json, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        print(f"✅ 모델 정보 저장: {args.out_info_json}")

if __name__ == "__main__":
    main()
