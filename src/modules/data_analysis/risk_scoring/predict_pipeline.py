# -*- coding: utf-8 -*-
from pathlib import Path
import json, os, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

# 학습 파이프라인과 동일한 전처/스코어 생성 루틴 재사용
from .train_pipeline import (
    ensure_year_month, ensure_all_standardized_features, _build_proxy_scores, _ensure_default_scores,
    _resolve_col, load_centers, soft_membership
)

def _build_feature_matrix(df_lbl: pd.DataFrame, centers_path: str):
    # 학습 파이프라인의 BASE_STD 정의와 동일하게 구성
    base_std = [
        "평일 총 이동 거리 합계_std", "휴일 총 이동 거리 합계_std",
        "동영상/방송 서비스 사용일수_std", "게임 서비스 사용일수_std",
        "지하철이동일수 합계_std", "집 추정 위치 평일 총 체류시간_std",
        "평균 통화대상자 수_std", "평균 문자량_std",
        "평일 총 이동 횟수_std",
        "주간상주지 변경횟수 평균_std", "야간상주지 변경횟수 평균_std",
        "소액결재 사용금액 평균_std", "소액결재 사용횟수 평균_std",
        "최근 3개월 내 요금 연체 비율_std",
        "쇼핑 서비스 사용일수_std", "금융 서비스 사용일수_std",
        "배달 서비스 사용일수_std",
    ]
    BASE_STD = [c for c in [_resolve_col(df_lbl, name) for name in base_std] if c]
    DELTA3M = [c + "_delta3m" for c in BASE_STD if (c + "_delta3m") in df_lbl.columns]
    TREND12 = [c + "_trend12m" for c in BASE_STD if (c + "_trend12m") in df_lbl.columns]

    X = df_lbl[["year_month"] + BASE_STD + DELTA3M + TREND12].copy()

    # 소프트 페르소나
    X = X.drop(columns=[c for c in X.columns if str(c).startswith("persona_")], errors="ignore")
    try:
        centers = load_centers(centers_path)
        P = soft_membership(df_lbl, centers, temp=1.0)
    except Exception:
        n = len(df_lbl)
        P = pd.DataFrame({
            "persona_p0": np.zeros(n), "persona_p1": np.zeros(n), "persona_p2": np.zeros(n),
            "persona_label": np.zeros(n, dtype=int), "persona_conf": np.zeros(n)
        }, index=df_lbl.index)

    X = X.join(P, how="left")

    # 인구통계 OHE (훈련과 동일 후보)
    CAT = [c for c in ["자치구", "성별", "연령대"] if c in df_lbl.columns]
    X = X.join(df_lbl[CAT])
    X = pd.get_dummies(X, columns=CAT, dummy_na=False)

    return X

def predict_rows(
    csv_path: str,
    rules_path: str,
    centers_path: str,
    artifacts_dir: str,
    out_csv: str = None
):
    from joblib import load as joblib_load
    # 0) 데이터 로드 & 전처리
    df = pd.read_csv(csv_path)
    df = ensure_year_month(df)
    df = ensure_all_standardized_features(df, month_col="year_month")

    # 1) 규칙 스코어 생성(학습과 동일)
    import yaml, io
    with open(rules_path, "r", encoding="utf-8") as f:
        rules_meta = yaml.safe_load(f) or {}
    lbl_cols = [c for c in df.columns if c.startswith("LBL_") and df[c].dtype == bool]
    df = _build_proxy_scores(df, rules_meta, lbl_cols)
    df = _ensure_default_scores(df, lbl_cols)

    # 2) 특성 행렬 구성
    X = _build_feature_matrix(df, centers_path)
    X = X.fillna(0)

    # 3) 메타 & 임계값 로드
    meta_path = os.path.join(artifacts_dir, "meta.json")
    thr_path  = os.path.join(artifacts_dir, "thresholds.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    with open(thr_path, "r", encoding="utf-8") as f:
        thresholds = json.load(f)

    labels = [c for c in meta["labels"] if c in thresholds]  # 모델이 실제로 저장된 라벨만

    # 4) 라벨별 예측
    proba_df = pd.DataFrame(index=X.index)
    pred_df  = pd.DataFrame(index=X.index)
    for lbl in labels:
        model_file = os.path.join(artifacts_dir, f"model_{lbl}.joblib")
        if not os.path.exists(model_file):
            continue
        est = joblib_load(model_file)

        # 학습 시 사용한 피처 집합으로 얼라인
        feat_cols = meta["per_label_features"].get(lbl, [])
        # 예측 시, 없던 컬럼은 0으로 채우고, 추가 컬럼은 무시
        for c in feat_cols:
            if c not in X.columns:
                X[c] = 0.0
        X_aligned = X[feat_cols] if feat_cols else X.select_dtypes(include=[np.number])

        # 확률 및 컷 적용
        if hasattr(est, "predict_proba"):
            p = est.predict_proba(X_aligned)
            p = p[:, 1] if p.ndim == 2 and p.shape[1] > 1 else np.zeros(len(X_aligned))
        else:
            s = est.decision_function(X_aligned)
            p = (s - s.min()) / (s.max() - s.min() + 1e-12)

        thr = float(thresholds.get(lbl, 0.5))
        proba_df[f"proba_{lbl}"] = p
        pred_df[f"pred_{lbl}"]   = (p >= thr).astype(int)

    # 5) 결과 머지 & 저장
    out = pd.DataFrame({
        "year_month": df["year_month"].astype(str),
        **({} if "행정동코드" not in df.columns else {"행정동코드": df["행정동코드"]}),
        **({} if "자치구" not in df.columns else {"자치구": df["자치구"]}),
        **({} if "성별" not in df.columns else {"성별": df["성별"]}),
        **({} if "연령대" not in df.columns else {"연령대": df["연령대"]}),
    })
    # 페르소나도 같이
    for c in [c for c in X.columns if c.startswith("persona_")]:
        out[c] = X[c].values

    out = pd.concat([out, proba_df, pred_df], axis=1)

    if out_csv is None:
        out_csv = os.path.join(artifacts_dir, "row_predictions.csv")
    out.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"[OK] saved: {out_csv}")
    # 요약 프린트
    cols = [c for c in pred_df.columns]
    if cols:
        rate = out[cols].mean().round(4).to_dict()
        print("[Preview] positive rates:", rate)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv_path", required=True)
    ap.add_argument("--rules_path", required=True)
    ap.add_argument("--centers_path", required=True)
    ap.add_argument("--artifacts_dir", required=True)
    ap.add_argument("--out_csv", default=None)
    args = ap.parse_args()
    predict_rows(
        csv_path=args.csv_path,
        rules_path=args.rules_path,
        centers_path=args.centers_path,
        artifacts_dir=args.artifacts_dir,
        out_csv=args.out_csv
    )
