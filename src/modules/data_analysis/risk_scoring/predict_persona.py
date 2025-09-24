# -*- coding: utf-8 -*-
# 사용법:
#   python predict_persona.py --csv new_month.csv --artifacts artifacts --centers project/cluster_centers.csv
#
# 산출물:
#   pred_out/
#     - scores_wide.parquet      (행 x 라벨 위험확률)
#     - labels_wide.parquet      (행 x 라벨 0/1)
#     - thresholds_wide.parquet  (행 x 라벨 적용 임계값)
#     - predictions_long.parquet (row_id, label, score, pred, thr)
#     - persona.parquet          (row_id, persona)
#     - feature_drift_warn.csv   (옵션: 분포 드리프트 경고)

import os, json, argparse
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import load as joblib_load

# ==== 학습 파이프라인과 동일한 전처리 유틸 ====
from train_pipeline import (
    ensure_year_month,
    ensure_all_standardized_features,
    _safe_proba,
)
from persona_soft import load_centers, soft_membership


# ---------------------------
# 내부 유틸
# ---------------------------
def _dominant_persona_from_matrix(df_like: pd.DataFrame) -> pd.Series:
    """persona_p* 중 최대값의 인덱스를 dominant persona로 변환."""
    pcols = [c for c in df_like.columns if isinstance(c, str) and c.startswith("persona_p")]
    if not pcols:
        return pd.Series(["persona_0"] * len(df_like), index=df_like.index)
    idx = np.argmax(df_like[pcols].values, axis=1)
    return pd.Series([f"persona_{i}" for i in idx], index=df_like.index)


def _one_hot_if_needed(df: pd.DataFrame) -> pd.DataFrame:
    """학습 시 OHE 되었던 '자치구/성별/연령대'가 원천에 있다면 OHE 수행."""
    cats = [c for c in ["자치구", "성별", "연령대"] if c in df.columns]
    if cats:
        df = pd.get_dummies(df, columns=cats, dummy_na=False)
    return df


def _force_schema(X: pd.DataFrame, columns: list) -> pd.DataFrame:
    """메타 스키마 강제: 누락 컬럼 0 채움, 여분 제거, 순서 동일."""
    return X.reindex(columns=columns, fill_value=0)


# ---------------------------
# 피처 준비
# ---------------------------
def prepare_features_for_inference(
    df_raw: pd.DataFrame,
    meta_path: str,
    centers_path: str = None,
) -> pd.DataFrame:
    """
    학습과 동일하게:
    - year_month 보장
    - 모든 숫자형 월별 강건 표준화(_std) + Δ/Trend 파생
    - soft persona join
    - 카테고리 OHE
    - meta['all_features'] 스키마로 정렬
    """
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # 1) year_month + 표준화 + 파생
    df = ensure_year_month(df_raw.copy())
    df = ensure_all_standardized_features(df, month_col="year_month")

    # 2) soft persona
    if centers_path and os.path.exists(centers_path):
        centers = load_centers(centers_path)
        P = soft_membership(df, centers, temp=1.0)
        df = df.join(P)
    else:
        # 학습에 persona_p0..가 있었다면 메타 스키마에서 채워지므로 여기서는 폴백만
        for c in ["persona_p0", "persona_p1", "persona_p2"]:
            if c not in df.columns:
                df[c] = 0.0

    # 3) OHE
    df = _one_hot_if_needed(df)

    # 4) 스키마 강제 (year_month 포함하여 정렬 후 제거)
    all_features = meta.get("all_features", [])
    X = df.reindex(columns=["year_month"] + all_features, fill_value=0)

    # 5) 모델 입력에서는 year_month 제거
    X = X.drop(columns=["year_month"], errors="ignore").fillna(0)
    return X


# ---------------------------
# 예측: 위험확률 + (옵션) 페르소나별 임계값 라벨
# ---------------------------
def predict_scores_and_labels(
    X: pd.DataFrame,
    artifacts_dir: str,
    apply_persona_thresholds: bool = True,
):
    """
    returns:
      scores:        (n_rows x n_labels) 위험확률
      labels_bin:    (n_rows x n_labels) 0/1
      persona_ids:   (n_rows,)           dominant persona 키
      applied_thr:   (n_rows x n_labels) 각 행/라벨에 실제 적용된 임계값
    """
    art = Path(artifacts_dir)

    # meta.json
    with open(art / "meta.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    # 라벨→피처 목록
    per_label_features = meta.get("per_label_features", {})
    labels = sorted([k for k in per_label_features.keys() if k.startswith("LBL_")])

    # thresholds_by_persona.json (선택)
    thr_by_persona_map = {}
    thr_persona_path = art / "thresholds_by_persona.json"
    if thr_persona_path.exists():
        with open(thr_persona_path, "r", encoding="utf-8") as f:
            thr_by_persona_map = json.load(f)

    # thresholds.json (전역 폴백)
    thr_global = {}
    thr_global_path = art / "thresholds.json"
    if thr_global_path.exists():
        with open(thr_global_path, "r", encoding="utf-8") as f:
            thr_global = json.load(f)

    # 결과 컨테이너
    scores = pd.DataFrame(index=X.index, dtype=float)
    labels_bin = pd.DataFrame(index=X.index, dtype=int)
    applied_thresholds = pd.DataFrame(index=X.index, dtype=float)

    # dominant persona (X에 persona_p*가 포함되어 있어야 함; meta 스키마로 강제됨)
    persona_ids = _dominant_persona_from_matrix(X)

    # 라벨별 예측
    for lbl in labels:
        feats = per_label_features.get(lbl, [])
        if not feats:
            print(f"[WARN] {lbl}: no feature list in meta → skip")
            continue

        # 스키마 가드
        missing = [c for c in feats if c not in X.columns]
        if missing:
            print(f"[WARN] {lbl}: {len(missing)} missing features; will fill 0")

        model_path = art / f"model_{lbl}.joblib"
        if not model_path.exists():
            print(f"[WARN] {lbl}: model file not found → skip")
            continue

        try:
            model = joblib_load(model_path)
        except Exception as e:
            print(f"[WARN] {lbl}: failed to load model → {e}")
            continue

        Xin = _force_schema(X[feats], feats)

        # 위험확률 = predict_proba(1)
        p = _safe_proba(model, Xin)
        scores[lbl] = p

        # 임계값(페르소나별 → _global → thresholds.json → 0.5)
        if apply_persona_thresholds:
            thr_table = thr_by_persona_map.get(lbl, {})
            thr_def = float(thr_table.get("_global", thr_global.get(lbl, 0.5)))
            row_thr = persona_ids.map(lambda k: float(thr_table.get(k, thr_def)))
        else:
            row_thr = float(thr_global.get(lbl, 0.5))

        applied_thresholds[lbl] = np.asarray(row_thr)
        labels_bin[lbl] = (p >= np.asarray(row_thr)).astype(int)

    return scores, labels_bin, persona_ids, applied_thresholds


# ---------------------------
# 드리프트(간단) 점검
# ---------------------------
def quick_drift_check(X: pd.DataFrame, artifacts_dir: str, out_dir: str):
    """
    monitor_baseline.json에 저장된 학습 분포 분위수와 비교.
    상/하 5% 분위수 밖 비율이 20% 이상인 피처를 경고로 저장.
    """
    base_path = Path(artifacts_dir) / "monitor_baseline.json"
    if not base_path.exists():
        return

    try:
        with open(base_path, "r", encoding="utf-8") as f:
            base = json.load(f)
    except Exception:
        return

    drift_flags = {}
    feat_hist = base.get("feature_hist", {})
    for c in X.columns[:200]:
        if c not in feat_hist:
            continue
        try:
            qs = np.array(feat_hist[c]["q"]).astype(float)  # 길이 21 (0~100 분위수)
            # 5% / 95% 분위수 근사치 (인덱스 1, 19이 5/95%에 해당)
            q_lo = qs[1] if len(qs) >= 20 else np.nanpercentile(qs, 5)
            q_hi = qs[19] if len(qs) >= 20 else np.nanpercentile(qs, 95)

            x = pd.to_numeric(X[c], errors="coerce")
            oob = ((x < q_lo) | (x > q_hi)).mean()
            if oob > 0.2:  # 20% 이상 범위를 벗어나면 경고
                drift_flags[c] = float(oob)
        except Exception:
            continue

    if drift_flags:
        out_path = Path(out_dir) / "feature_drift_warn.csv"
        pd.Series(drift_flags).sort_values(ascending=False).to_csv(out_path, encoding="utf-8-sig")
        print(f"[DRIFT] {len(drift_flags)} features show potential drift → {out_path}")


# ---------------------------
# CLI
# ---------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="신규 월 CSV 경로")
    ap.add_argument("--artifacts", default="artifacts", help="학습 산출물 폴더")
    ap.add_argument("--centers", default="project/cluster_centers.csv", help="soft persona center csv")
    ap.add_argument("--out_dir", default="pred_out", help="출력 폴더")
    ap.add_argument("--no_persona_thr", action="store_true", help="페르소나별 임계값 적용 끄기")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    meta_path = str(Path(args.artifacts) / "meta.json")

    # 0) 원천 로드
    df_raw = pd.read_csv(args.csv)

    # 1) 피처 준비
    X = prepare_features_for_inference(
        df_raw=df_raw,
        meta_path=meta_path,
        centers_path=args.centers
    )

    # 2) 예측
    scores, labels_bin, persona_ids, applied_thr = predict_scores_and_labels(
        X,
        artifacts_dir=args.artifacts,
        apply_persona_thresholds=not args.no_persona_thr
    )

    # 3) 저장 (wide + long)
    #   - wide
    scores.reset_index(names="row_id").to_parquet(Path(args.out_dir) / "scores_wide.parquet", index=False)
    labels_bin.reset_index(names="row_id").to_parquet(Path(args.out_dir) / "labels_wide.parquet", index=False)
    applied_thr.reset_index(names="row_id").to_parquet(Path(args.out_dir) / "thresholds_wide.parquet", index=False)
    persona_ids.to_frame("persona").reset_index(names="row_id").to_parquet(Path(args.out_dir) / "persona.parquet", index=False)

    #   - long
    scores_long = (
        scores.stack()
            .to_frame("score")
            .reset_index()
            .rename(columns={"level_0": "row_id", "level_1": "label"})
    )

    labels_long = (
        labels_bin.stack()
                .to_frame("pred")
                .reset_index()
                .rename(columns={"level_0": "row_id", "level_1": "label"})
    )
    thr_long = (
        applied_thr.stack()
                .to_frame("thr")
                .reset_index()
                .rename(columns={"level_0": "row_id", "level_1": "label"})
    )
    pd.merge(pd.merge(scores_long, labels_long, on=["row_id", "label"]), thr_long, on=["row_id", "label"]) \
        .to_parquet(Path(args.out_dir) / "predictions_long.parquet", index=False)

    # 4) 간단 드리프트 리포트
    quick_drift_check(X, artifacts_dir=args.artifacts, out_dir=args.out_dir)

    print(f"[DONE] saved to {args.out_dir}/")
    print(" - scores_wide.parquet, labels_wide.parquet, thresholds_wide.parquet")
    print(" - predictions_long.parquet, persona.parquet")
    print(" - (optional) feature_drift_warn.csv")


if __name__ == "__main__":
    main()
