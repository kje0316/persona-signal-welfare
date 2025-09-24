# train_pipeline.py
# -*- coding: utf-8 -*-
"""
멀티라벨 학습 파이프라인
- 규칙 라벨링(hybrid) → (자동 분할: single-class 라벨 GMM/KMeans) → (선택) 컷 튜닝(라벨율 목표)
  → 시간 분할(train/cal/test) → LGBM(LogReg 폴백) 학습
- 단일 클래스/저양성, 상수 피처/누수 자동 방어
- 규칙-피처 강제 제외(Fallback): signals + gate 전부 제거
- 캘리브레이션(isotonic→sigmoid 폴백)
- 임계값 선택 전략: cost / f1 / rec_at_prec(target) (+라벨별 비용지도)
- 메트릭/임계값/메타/모니터링 히스토그램/라벨율/중요도/PR커브 저장
- (옵션) 개인 기준 Δ3m/Trend12m 계산 지원
- CLI 인자 지원
"""
from pathlib import Path
from typing import Optional, List, Tuple, Dict
import os, json, warnings
from datetime import datetime

import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

# --- 프로젝트 모듈 ---
from .rules_loader import load_rules, rules_version
from .label_rules import apply_rule_hybrid
from .persona_soft import load_centers, soft_membership


# ========== 유틸 ==========
def _resolve_col(df: pd.DataFrame, name: str):
    if not isinstance(name, str) or not name:
        return None
    base = name
    for suf in ["_pc_std", "_pc", "_std"]:
        if base.endswith(suf):
            base = base[: -len(suf)]
            break

    # 1차: 정확/표준 후보
    candidates = [name, f"{base}_std", base]
    seen = set()
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            if c in df.columns:
                return c

    # 2차: 느슨 매칭(길이 짧은 것 우선, *_std 우선)
    pool = [c for c in df.columns if isinstance(c, str) and base in c]
    if not pool:
        return None
    pool_std = [c for c in pool if c.endswith("_std")]
    if pool_std:
        pool = pool_std
    # '평균' 우선, 그 다음 전체 길이 짧은 순
    pool.sort(key=lambda x: (0 if "평균" in x else 1, len(x)))
    return pool[0]


def run_diagnostic_check(df_lbl, rules_meta, lbl_cols, mask_train):
    """
    각 라벨별로 rules.yml에 정의된 신호 컬럼의 존재 여부와
    학습 데이터셋 내에서의 분산(표준편차)을 점검하여 출력합니다.
    """
    print("\n" + "="*50)
    print("🕵️  STARTING DIAGNOSTIC CHECK...")
    print("="*50)

    for lbl in lbl_cols:
        print(f"\n[진단] 라벨: {lbl}")
        tgt = lbl.replace("LBL_", "")
        obj = (rules_meta or {}).get("targets", {}).get(tgt, {}) or {}
        sigs = obj.get("signals", []) or []

        if not sigs:
            print("  - ⚠️  rules.yml에 정의된 신호(signals)가 없습니다.")
            continue

        for sig in sigs:
            col_name = sig.get("col")
            if not col_name:
                continue

            resolved = _resolve_col(df_lbl, col_name)
            if resolved is None:
                print(f"  - ❌  '{col_name}' (매칭 실패) | df에 대응 컬럼 없음")
                continue

            # 학습 기간 내 분산 확인
            train_series = pd.to_numeric(df_lbl.loc[mask_train, resolved], errors='coerce')
            std_dev = train_series.std()

            if pd.isna(std_dev) or std_dev < 1e-6:
                print(f"  - ⚠️  '{col_name}' → 사용: '{resolved}' | 학습 기간 분산 거의 없음 (std={std_dev:.4f})")
            else:
                print(f"  - ✅  '{col_name}' → 사용: '{resolved}' | 유효 (std={std_dev:.4f})")

    print("\n" + "="*50)
    print("🕵️  DIAGNOSTIC CHECK COMPLETE.")
    print("="*50 + "\n")




def ensure_year_month(df: pd.DataFrame) -> pd.DataFrame:
    """year_month(datetime64) 컬럼 보장."""
    if "year_month" in df and np.issubdtype(df["year_month"].dtype, np.datetime64):
        return df
    if "month" in df:
        try:
            df["year_month"] = pd.to_datetime(df["month"]).dt.to_period("M").dt.to_timestamp()
            return df
        except Exception:
            pass
    if {"year", "month_num"}.issubset(df.columns):
        df["year_month"] = pd.to_datetime(
            dict(year=df["year"].astype(int), month=df["month_num"].astype(int), day=1)
        )
        return df
    raise ValueError("year_month 생성 실패")


def as_pyfloat_list(arr) -> List[float]:
    return [float(x) for x in np.asarray(arr).ravel().tolist()]


# 기존 _monthwise_robust_z_log1p 와 ensure_pc_std_all 함수를 지우고 아래 코드로 교체

def ensure_all_standardized_features(df: pd.DataFrame, month_col: str = "year_month") -> pd.DataFrame:
    """
    데이터프레임의 모든 숫자형 컬럼에 대해 월별 강건한 표준화(_std)를 적용하는 최종 함수.
    - 원본 컬럼이름에 _std를 붙여 새 컬럼을 생성.
    - ID, 날짜, 카테고리성 컬럼은 제외.
    """
    print("모든 숫자형 피처에 대한 표준화(_std)를 시작합니다...")
    out = df.copy()
    
    # 표준화에서 제외할 컬럼들
    exclude_cols = {month_col, "year", "month_num", "행정동코드", "자치구", "성별", "연령대"}

    
    # df에 있는 모든 컬럼을 순회
    for col in df.columns:
        if col in exclude_cols or col.endswith("_std"):
            continue
            
        # 숫자형으로 변환 가능한 컬럼인지 확인 (메모리 효율적)
        if pd.api.types.is_numeric_dtype(df[col]):
            std_col_name = f"{col}_std"
            if std_col_name in out.columns:
                continue

            # 월별 강건한 표준화 (log1p + z-score)
            x = np.log1p(pd.to_numeric(df[col], errors="coerce").clip(lower=0))
            g = x.groupby(df[month_col])
            med = g.transform("median")
            iqr = g.transform(lambda v: v.quantile(0.75) - v.quantile(0.25))
            scale = iqr.where(iqr > 0, g.transform("std")).fillna(1.0)
            
            out[std_col_name] = ((x - med) / scale.where(scale > 0, 1.0)).fillna(0)
            print(f"  - '{std_col_name}' 생성 완료.")

    # Δ/Trend 피처들은 원본이 아닌 _std 피처를 기반으로 생성하도록 수정
    base_std_cols_for_derived = [c for c in out.columns if c.endswith("_std")]
    out = ensure_delta3m(out, base_std_cols_for_derived, month_col)
    out = ensure_trend12m(out, base_std_cols_for_derived, month_col)

    return out


# ===== Δ3m/Trend12m: (A) 월평균 기반 스냅샷  =====
def ensure_delta3m(df: pd.DataFrame, base_cols: List[str], month_col: str = "year_month") -> pd.DataFrame:
    """월평균 기반 3개월 변화(현재3M-직전3M). (개인ID 없을 때의 안전한 폴백)"""
    out = df.copy()
    base_cols = [c for c in base_cols if c in out.columns]
    if not base_cols: return out
    mdf = out.groupby([month_col], as_index=False)[base_cols].mean().sort_values(month_col)
    for c in base_cols:
        cur3 = mdf[c].rolling(3, min_periods=3).mean()
        prev3 = mdf[c].shift(3).rolling(3, min_periods=3).mean()
        mdf[c + "_delta3m"] = cur3 - prev3
    out = out.merge(mdf[[month_col] + [c + "_delta3m" for c in base_cols]], on=month_col, how="left")
    return out


def ensure_trend12m(df: pd.DataFrame, base_cols: List[str], month_col: str = "year_month") -> pd.DataFrame:
    """월평균 기반 12개월 트렌드(6M-6M). (개인ID 없을 때의 안전한 폴백)"""
    out = df.copy()
    base_cols = [c for c in base_cols if c in out.columns]
    if not base_cols: return out
    mdf = out.groupby([month_col], as_index=False)[base_cols].mean().sort_values(month_col)
    for c in base_cols:
        cur6 = mdf[c].rolling(6, min_periods=6).mean()
        prev6 = mdf[c].shift(6).rolling(6, min_periods=6).mean()
        mdf[c + "_trend12m"] = cur6 - prev6
    out = out.merge(mdf[[month_col] + [c + "_trend12m" for c in base_cols]], on=month_col, how="left")
    return out


# ===== Δ3m/Trend12m: (B) 개인 기준 버전 (권장) =====
def ensure_delta3m_per_id(df: pd.DataFrame, base_cols: List[str], id_col: str, month_col: str = "year_month") -> pd.DataFrame:
    """개인기준 3개월 변화(현재3M-직전3M)."""
    out = df.sort_values([id_col, month_col]).copy()
    for c in [x for x in base_cols if x in out.columns]:
        g = out.groupby(id_col)[c]
        cur3  = g.transform(lambda s: s.rolling(3, min_periods=3).mean())
        prev3 = g.transform(lambda s: s.shift(3).rolling(3, min_periods=3).mean())
        out[c + "_delta3m"] = cur3 - prev3
    return out


def ensure_trend12m_per_id(df: pd.DataFrame, base_cols: List[str], id_col: str, month_col: str = "year_month") -> pd.DataFrame:
    """개인기준 12개월 트렌드(6M-6M)."""
    out = df.sort_values([id_col, month_col]).copy()
    for c in [x for x in base_cols if x in out.columns]:
        g = out.groupby(id_col)[c]
        cur6  = g.transform(lambda s: s.rolling(6, min_periods=6).mean())
        prev6 = g.transform(lambda s: s.shift(6).rolling(6, min_periods=6).mean())
        out[c + "_trend12m"] = cur6 - prev6
    return out


# ===== 임계값 선택 =====
def pick_threshold_cost(y_true, p_pred, cost_fn: float = 20.0, cost_fp: float = 1.0) -> float:
    y = np.asarray(y_true).astype(int)
    p = np.asarray(p_pred).astype(float)
    thr_grid = np.linspace(0.01, 0.99, 99)
    best_thr, best_cost = 0.5, 1e18
    for t in thr_grid:
        yhat = (p >= t).astype(int)
        fn = ((y == 1) & (yhat == 0)).sum()
        fp = ((y == 0) & (yhat == 1)).sum()
        cost = cost_fn * fn + cost_fp * fp
        if cost < best_cost:
            best_cost, best_thr = cost, t
    return float(best_thr)


def pick_threshold_f1(y_true, p_pred) -> float:
    from sklearn.metrics import f1_score
    y = np.asarray(y_true).astype(int)
    p = np.asarray(p_pred).astype(float)
    thr_grid = np.unique(np.clip(np.r_[np.linspace(0.01, 0.99, 99), p], 1e-4, 1-1e-4))
    best_thr, best_f1 = 0.5, -1.0
    for t in thr_grid:
        yhat = (p >= t).astype(int)
        f1 = f1_score(y, yhat, zero_division=0)
        if f1 > best_f1:
            best_f1, best_thr = f1, t
    return float(best_thr)


def pick_threshold_rec_at_prec(y_true, p_pred, target_prec: float = 0.6) -> float:
    from sklearn.metrics import precision_recall_curve
    y = np.asarray(y_true).astype(int)
    p = np.asarray(p_pred).astype(float)
    prec, rec, thr = precision_recall_curve(y, p)

    # precision 배열은 길이가 recall보다 1 길며, thr는 recall/precision보다 1 짧음
    valid = np.where(prec[:-1] >= target_prec)[0]
    if len(valid) > 0:
        # 목표 정밀도 이상인 후보들 중 리콜이 최대인 지점 선택
        best = valid[np.argmax(rec[valid])]
        return float(thr[best])

    # 목표 정밀도를 만족 못하면 F1 기준으로 폴백
    return pick_threshold_f1(y, p)


# ===== 피처/누수 =====
def drop_low_variance_features(
    X_train: pd.DataFrame, X_cal: pd.DataFrame, X_test: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, List[str]]:
    """Train 기준 상수/준상수(유니크<=1) 피처 제거."""
    const_cols = [c for c in X_train.columns if pd.Series(X_train[c]).nunique(dropna=False) <= 1]
    if const_cols:
        X_train = X_train.drop(columns=const_cols, errors="ignore")
        X_cal = X_cal.drop(columns=const_cols, errors="ignore")
        X_test = X_test.drop(columns=const_cols, errors="ignore")
    return X_train, X_cal, X_test, const_cols


def _safe_proba(est, X: pd.DataFrame) -> np.ndarray:
    """predict_proba/decision_function 유무와 단일클래스까지 안전 처리."""
    if hasattr(est, "predict_proba"):
        proba = est.predict_proba(X)
        if proba.ndim == 1:
            return proba.astype(float)
        if proba.shape[1] == 1:
            return np.zeros(len(X), dtype=float)
        return proba[:, 1].astype(float)
    s = est.decision_function(X)
    s = (s - np.min(s)) / (np.max(s) - np.min(s) + 1e-12)
    return s.astype(float)


def _find_trivial_leak_cols(X: pd.DataFrame, y: np.ndarray, max_report: int = 5) -> List[str]:
    """피처가 라벨과 완전히 동일/보색이면 누수로 간주."""
    leaks = []
    yf = y.astype(float)
    for c in X.columns:
        xc = pd.to_numeric(X[c], errors="coerce").astype(float).fillna(-9999).values
        if np.array_equal(xc, yf):
            leaks.append(c)
        elif set(np.unique(yf)).issubset({0.0, 1.0}) and np.array_equal(1.0 - xc, yf):
            leaks.append(c)
        if len(leaks) >= max_report:
            break
    return leaks


# === 규칙-피처 추출: signals + gate + RULESRC_/REASON_ ===
# === 규칙-피처 추출: signals + gate + RULESRC_/REASON_ ===
def _rule_cols_for(label_name, rules_meta, candidate_feats, drop_ohe_from_gates=False):
    """
    규칙에 쓰인 컬럼 중 '원본'과 '원본_std'만 드롭하고,
    delta/trend 등 파생은 보존한다.
    예) 규칙에 "평일 총 이동 거리 합계_std_delta3m"가 있어도
        모델에서는 "평일 총 이동 거리 합계" / "평일 총 이동 거리 합계_std"만 드롭.
    """
    tgt = label_name.replace("LBL_", "")
    cols = set()

    def base_root(name: Optional[str]) -> Optional[str]:
        if not isinstance(name, str) or not name:
            return None
        s = name
        # 파생 접미어 제거 우선(파생을 보존하기 위해 root만 구한다)
        for suf in ["_delta3m", "_trend12m"]:
            if s.endswith(suf):
                s = s[: -len(suf)]
                break
        # 표준 접미어 제거
        if s.endswith("_std"):
            s = s[: -len("_std")]
        return s

    def add_base(name: Optional[str]):
        """
        candidate_feats에서 'root'와 'root_std'만 드롭 대상에 넣는다.
        파생( _delta3m / _trend12m )은 드롭하지 않는다.
        """
        root = base_root(name)
        if not root:
            return
        # 원본/표준만 드롭
        for f in candidate_feats:
            if f == root or f == f"{root}_std":
                cols.add(f)
        # 게이트의 원-핫 드롭 옵션
        if drop_ohe_from_gates:
            prefix = root + "_"
            for f in candidate_feats:
                if not isinstance(f, str):
                    continue
                if f.startswith(prefix):
                    # 파생 피처는 유지
                    if any(k in f for k in ["_std", "_delta3m", "_trend12m"]):
                        continue
                    cols.add(f)

    obj = (rules_meta or {}).get("targets", {}).get(tgt, {}) or {}

    # signals
    for s in obj.get("signals", []) or []:
        add_base((s or {}).get("col"))

    # gates / filters
    gates = obj.get("gate") or obj.get("gates") or obj.get("filters") or obj.get("conditions")
    if isinstance(gates, dict):
        for k in gates.keys():
            add_base(k)
    elif isinstance(gates, list):
        for g in gates:
            if isinstance(g, dict):
                add_base(g.get("col") or g.get("field") or next(iter(g.keys()), None))
            elif isinstance(g, str):
                add_base(g)

    # RULESRC_/REASON_은 항상 드롭
    for f in candidate_feats:
        if isinstance(f, str) and (f.startswith("RULESRC_") or f.startswith("REASON_")):
            cols.add(f)

    return sorted(cols)



# ====== SCORE 합성 (규칙 기반) ======
def _build_proxy_scores(df_in: pd.DataFrame, rules_meta: dict, lbl_cols: List[str]) -> pd.DataFrame:
    """
    rules.yml의 signals(col, direction, weight)를 이용해 SCORE_<TARGET>을 합성.
    - 이미 SCORE_*가 있으면 건드리지 않음
    - direction: high(+), low(-)로 부호만 반영, weight 가중합
    - 모든 입력은 견고 스케일(1~99%) 후 합산
    - 규칙 컬럼명이 _pc/_pc_std/_std 등이어도 _resolve_col로 실제 컬럼에 매핑
    """
    df = df_in.copy()
    targets = (rules_meta or {}).get("targets", {}) or {}

    def robust_minmax(x: pd.Series) -> pd.Series:
        x = pd.to_numeric(x, errors="coerce").astype(float)
        q1, q99 = x.quantile(0.01), x.quantile(0.99)
        denom = (q99 - q1) if (q99 > q1) else (x.std() or 1.0)
        out = (x - q1) / (denom if denom != 0 else 1.0)
        return out.fillna(0.0).clip(-5, 5)

    for lbl in lbl_cols:
        tgt = lbl.replace("LBL_", "")
        sname = f"SCORE_{tgt}"
        if sname in df.columns:
            continue

        obj = targets.get(tgt, {}) or {}
        sigs = obj.get("signals", []) or []
        if not sigs:
            # 신호가 전혀 없으면 점수 생성을 패스(튜너/오토스플릿이 알아서 스킵)
            continue

        s_acc = pd.Series(0.0, index=df.index, dtype=float)
        used_any = False
        for sig in sigs:
            col_req = sig.get("col")
            col = _resolve_col(df, col_req)
            if not col:
                print(f"[SCORE] {lbl}: '{col_req}' → 매칭 실패(컬럼 없음)")
                continue
            w = float(sig.get("weight", 1.0))
            direction = (sig.get("direction") or "high").lower().strip()
            sign = 1.0 if direction == "high" else -1.0
            s_raw = robust_minmax(df[col])
            s_acc = s_acc + w * sign * s_raw
            used_any = True

        if used_any:
            # 합성 점수도 다시 견고 스케일 0~1로 정규화
            acc_scaled = robust_minmax(s_acc)
            acc_scaled = (acc_scaled - acc_scaled.min()) / (acc_scaled.max() - acc_scaled.min() + 1e-12)
            df[sname] = acc_scaled.fillna(0.0)
        else:
            # 사용할 신호가 하나도 없으면 생성 안 함(진단/오토스플릿에서 안내)
            print(f"[SCORE] {lbl}: 사용 가능한 신호가 없어 SCORE 생성 스킵")
    return df

# ====== SCORE 기본값 강제 생성기(규칙 비어도 동작) ======
def _ensure_default_scores(df_in: pd.DataFrame, lbl_cols: List[str]) -> pd.DataFrame:
    def cols_like(df, *patterns):
        pats = [p for p in patterns if isinstance(p, str)]
        return [c for c in df.columns if isinstance(c, str) and any(p in c for p in pats)]

    def robust_minmax(s: pd.Series) -> pd.Series:
        s = pd.to_numeric(s, errors="coerce").astype(float).fillna(0.0)
        q1, q99 = s.quantile(0.01), s.quantile(0.99)
        denom = (q99 - q1) if (q99 > q1) else (s.std() or 1.0)
        return ((s - q1) / (denom if denom != 0 else 1.0)).clip(0, 1)

    out = df_in.copy()

    # <- 전부 *_std 패턴으로 맞춤
    HOME   = cols_like(out, "집 추정 위치 평일 총 체류시간_std")
    MOVE_D = cols_like(out, "평일 총 이동 거리 합계_std")
    MOVE_N = cols_like(out, "평일 총 이동 횟수_std")
    SUBWAY = cols_like(out, "지하철이동일수 합계_std")
    CHAT_N = cols_like(out, "평균 통화대상자 수_std", "평균 문자대상자 수_std")
    CHAT_V = cols_like(out, "평균 통화량_std", "평균 문자량_std")
    SNS    = cols_like(out, "SNS 사용횟수_std")
    MEDIA  = cols_like(out, "동영상/방송 서비스 사용일수_std", "유튜브 사용일수_std", "넷플릭스 사용일수_std")
    DELTA3 = cols_like(out, "_delta3m")
    TREND12= cols_like(out, "_trend12m")
    HOME_D = [c for c in DELTA3 if "체류시간" in c]
    MOVE_DD= [c for c in DELTA3 if "이동" in c]
    WEEK_HOME = HOME
    HOUSING_CHG = cols_like(out, "주간상주지 변경횟수 평균_std", "야간상주지 변경횟수 평균_std")

    plans: Dict[str, Dict] = {
        "LBL_HOUSING": {"plus": HOUSING_CHG + HOME_D, "minus": [], "name": "SCORE_HOUSING"},
        "LBL_EMPLOYMENT": {"plus": MOVE_D + MOVE_N + SUBWAY, "minus": [], "name": "SCORE_EMPLOYMENT"},
        "LBL_ISOLATION": {"plus": WEEK_HOME, "minus": CHAT_N + CHAT_V + SNS, "name": "SCORE_ISOLATION"},
        "LBL_DAILY_LONGTERM": {"plus": WEEK_HOME + MEDIA, "minus": MOVE_D + MOVE_N + SUBWAY, "name": "SCORE_DAILY_LONGTERM"},
        "LBL_HEALTH_MENTAL_DELTA": {
            "plus": [*HOME_D, *MOVE_DD] + [c for c in TREND12 if any(k in c for k in ["이동","체류","동영상","지하철"])],
            "minus": [], "absval": True, "name": "SCORE_HEALTH_MENTAL_DELTA",
        },
    }

    for lbl in lbl_cols:
        plan = plans.get(lbl)
        if not plan: continue
        sname = plan["name"]
        if sname in out.columns: continue

        plus  = [c for c in plan.get("plus", [])  if c in out.columns]
        minus = [c for c in plan.get("minus", []) if c in out.columns]
        if not plus and not minus:
            print(f"[SCORE/DEFAULT] {lbl}: 사용할 *_std 피처가 없어 기본 SCORE 생성 스킵")
            continue

        score = pd.Series(0.0, index=out.index, dtype=float)

        def add(cols, sign=1.0, use_abs=False):
            w = 1.0 / max(len(cols), 1)
            for c in cols:
                v = pd.to_numeric(out[c], errors="coerce").astype(float).fillna(0.0)
                if use_abs: v = v.abs()
                score[:] = score.values + sign * w * v.values

        add(plus, +1.0, plan.get("absval", False))
        add(minus, -1.0, False)
        out[sname] = robust_minmax(score)

    return out




# ===== cut 튜너: 목표 라벨율로 컷을 분위수로 설정 =====
def _tune_labels_by_scores(
    df_lbl: pd.DataFrame,
    lbl_cols: List[str],
    target_rate_map: Dict[str, float]
) -> pd.DataFrame:
    """
    SCORE_<TARGET> 분포의 (1 - rate) 분위수를 컷으로 잡아 라벨율을 맞춥니다.
    - 외부 변수 참조 없음
    - 재귀 호출 없음
    - 단일클래스 방지 가드 포함
    """
    out = df_lbl.copy()

    # before preview
    try:
        before = {lbl: round(100.0 * float(out[lbl].astype(int).mean()), 3) for lbl in lbl_cols if lbl in out.columns}
        print(f"[TUNE] before rates(%) → {before}")
    except Exception:
        pass

    for lbl in lbl_cols:
        if lbl not in out.columns:
            continue

        tgt = lbl.replace("LBL_", "")
        sname = f"SCORE_{tgt}"
        if sname not in out.columns:
            print(f"[TUNE/skip] {lbl}: '{sname}' 없음 → 스킵")
            continue

        s = pd.to_numeric(out[sname], errors="coerce").astype(float)
        if s.notna().sum() == 0:
            print(f"[TUNE/skip] {lbl}: 점수가 모두 NaN → 스킵")
            continue

        # 목표 라벨율 (안전 클리핑)
        rate = float(target_rate_map.get(lbl, 0.05))
        rate = min(max(rate, 0.01), 0.99)

        thr = np.quantile(s.dropna(), 1.0 - rate)
        lab = (s >= thr).astype(bool)

        # 단일클래스 방지 가드
        m = float(lab.mean())
        if m in (0.0, 1.0):
            # 더 완화/강화해서 재시도
            r2 = 0.01 if m == 1.0 else 0.99
            thr2 = np.quantile(s.dropna(), 1.0 - r2)
            lab = (s >= thr2).astype(bool)

        out[lbl] = lab

    # after preview
    try:
        after = {lbl: round(100.0 * float(out[lbl].astype(int).mean()), 2) for lbl in lbl_cols if lbl in out.columns}
        print(f"[TUNE] after rates(%)  → {after}")
    except Exception:
        pass

    return out


# ===== single-class 자동 분할기 (1D: GMM → KMeans → Quantile) =====
def auto_split_gmm_1d(scores: np.ndarray) -> Tuple[np.ndarray, float]:
    from sklearn.mixture import GaussianMixture
    x = scores.reshape(-1, 1)
    gmm = GaussianMixture(n_components=2, covariance_type='full', random_state=42)
    gmm.fit(x)
    means = gmm.means_.ravel()
    hi = int(np.argmax(means))
    post = gmm.predict_proba(x)[:, hi]
    # 0.5 기준 분류, 임계값은 두 평균의 중간 정도로 리포트
    thr = float(np.mean(means))
    y = (post >= 0.5).astype(bool)
    return y, thr


def auto_split_kmeans_1d(scores: np.ndarray) -> Tuple[np.ndarray, float]:
    from sklearn.cluster import KMeans
    x = scores.reshape(-1, 1)
    km = KMeans(n_clusters=2, n_init=10, random_state=42)
    lab = km.fit_predict(x)
    centers = km.cluster_centers_.ravel()
    hi = int(np.argmax(centers))
    y = (lab == hi)
    thr = float(np.mean(centers))
    return y, thr


def auto_split_single_class_labels(
    df_lbl: pd.DataFrame,
    lbl_cols: List[str],
    mask_train: pd.Series,
    min_pos_rate: float = 0.02,
    max_pos_rate: float = 0.20,
) -> pd.DataFrame:
    out = df_lbl.copy()
    single = []
    for lbl in lbl_cols:
        y_tr = out.loc[mask_train, lbl].astype(int)
        n_tr, n_pos = int(len(y_tr)), int(y_tr.sum())
        if n_tr == 0:
            continue
        if n_pos == 0 or n_pos == n_tr:
            single.append(lbl)
    if single:
        print("[AUTO] single-class labels →", single)
    else:
        return out

    for lbl in single:
        sname = f"SCORE_{lbl.replace('LBL_', '')}"
        if sname not in out.columns:
            print(f"[AUTO] {lbl}: auto-split skipped (not enough signals/score)")
            continue
        s_train = pd.to_numeric(out.loc[mask_train, sname], errors="coerce").astype(float)
        s_all   = pd.to_numeric(out[sname], errors="coerce").astype(float)
        valid_tr = s_train.notna().values
        if valid_tr.sum() < 100:
            print(f"[AUTO] {lbl}: auto-split skipped (too few valid scores)")
            continue
        try:
            y_split, thr = auto_split_gmm_1d(s_train[valid_tr].values)
        except Exception:
            try:
                y_split, thr = auto_split_kmeans_1d(s_train[valid_tr].values)
            except Exception:
                # 최후: 중앙값 기준
                thr = float(np.nanmedian(s_train))
                y_split = (s_train[valid_tr].values >= thr)

        # 전체 데이터에 임계값 적용
        new_lab = (s_all.values >= thr)
        rate = float(np.nanmean(new_lab))
        # 과도한 비율이면 clip (분할 탐욕도 제어)
        if rate < min_pos_rate:
            qthr = np.nanquantile(s_all, 1.0 - min_pos_rate)
            new_lab = (s_all.values >= qthr)
            rate = float(np.nanmean(new_lab))
        elif rate > max_pos_rate:
            qthr = np.nanquantile(s_all, 1.0 - max_pos_rate)
            new_lab = (s_all.values >= qthr)
            rate = float(np.nanmean(new_lab))

        out[lbl] = pd.Series(new_lab, index=out.index).astype(bool)
        print(f"[AUTO] {lbl}: auto-split done (rate={rate*100:.2f}%, thr≈{thr:.4f})")

    return out



def timeaware_backstop_tuner(df_lbl, lbl, score_col, month_col="year_month",
                             base_rate=0.0513, min_pos_per_month=15,
                             max_relax_quantile=0.95):
    out = df_lbl.copy()
    if score_col not in out.columns or lbl not in out.columns:
        return out

    y = out[lbl].astype(bool).copy()

    for m, idx in out.groupby(month_col).groups.items():
        sub = out.loc[idx]
        n = len(sub)
        if n == 0:
            continue

        p_now = int(sub[lbl].sum())
        if p_now >= min_pos_per_month:
            continue

        s = pd.to_numeric(sub[score_col], errors="coerce")
        valid = s.notna()
        n_valid = int(valid.sum())
        if n_valid == 0:
            continue

        k_rate = int(np.ceil(base_rate * n_valid))
        k_cap  = max(1, int(np.ceil((1.0 - max_relax_quantile) * n_valid)))  # 예: q=0.95 → 상위 5%
        k_goal = min(max(min_pos_per_month, min(k_rate, k_cap)), n_valid)

        if p_now >= k_goal:
            continue

        need = k_goal - p_now
        not_pos_mask = ~sub[lbl].astype(bool) & valid
        if not_pos_mask.sum() == 0 or need <= 0:
            continue

        s_candidates = s[not_pos_mask]
        order = np.argsort(s_candidates.values)
        chosen = s_candidates.iloc[order[-need:]].index  # 상위 need개만

        new_mask = pd.Series(False, index=sub.index)
        new_mask.loc[chosen] = True
        y.loc[idx] = (sub[lbl].astype(bool) | new_mask).values

    out[lbl] = y.astype(bool)
    return out





def apply_persistence(df_lbl, lbl, id_col=None, month_col="year_month",
                      window=3, min_hits=2, group_col=None):
    """
    최근 'window'개월 중 'min_hits'개월 이상 양성이면 그 달을 양성으로 '유지' (과확대 금지).
    - id_col이 있으면 id 기준
    - 없으면 가능한 카테고리(행정동/자치구/성별/연령대)를 모두 묶어 복합키로 사용
    - 키가 없으면 no-op
    """
    out = df_lbl.copy()

    # 0) 키 확정
    if id_col and id_col in out.columns:
        key_cols = [id_col]
    else:
        # group_col 인자가 리스트/문자열 모두 지원
        if isinstance(group_col, (list, tuple)):
            cand = [c for c in group_col if c in out.columns]
        elif isinstance(group_col, str):
            cand = [c for c in [group_col] if c in out.columns]
        else:
            cand = []
        # 기본 후보(있는 것만)
        fallback = [c for c in ["행정동코드", "자치구", "성별", "연령대"] if c in out.columns]
        key_cols = cand or fallback

    if not key_cols:
        return out

    # 1) 키+월 단위 월 플래그(그 키-월에 1건이라도 양성인지)
    out = out.sort_values(key_cols + [month_col])
    month_flag = (
        out.groupby(key_cols + [month_col])[lbl]
           .max()
           .reset_index(name="__mflag__")
           .sort_values(key_cols + [month_col])
    )

    # 2) 키별 롤링합 → min_hits 이상이면 '그 키'에서 그 달은 유지(True)
    month_flag["__hits__"] = (
        month_flag.groupby(key_cols)["__mflag__"]
                  .transform(lambda s: s.rolling(window, min_periods=window).sum())
    )
    month_flag["__persist__"] = month_flag["__hits__"] >= float(min_hits)

    # 3) 원본으로 브로드캐스트 (교집합으로만 유지, 과확대 방지)
    out = out.merge(
        month_flag[key_cols + [month_col, "__persist__"]],
        on=key_cols + [month_col], how="left"
    )
    out[lbl] = out[lbl].astype(bool) & out["__persist__"].fillna(False)
    out.drop(columns=["__persist__", "__hits__", "__mflag__"], errors="ignore", inplace=True)
    return out

# ========== 메인 ==========
def train_multilabel_with_calibration(
    csv_path: str = "telecom_group_monthly_all.csv",
    rules_path: Optional[str] = None,
    centers_path: Optional[str] = None,
    out_dir: str = "artifacts",
    exclude_months: List[pd.Timestamp] = None,
    cut_cal_from: pd.Timestamp = pd.Timestamp("2024-07-01"),
    cut_test_from: pd.Timestamp = pd.Timestamp("2025-01-01"),
    cost_fn: float = 20.0,
    cost_fp: float = 1.0,
    thr_strategy: str = "cost",          # "cost" | "f1" | "rec_at_prec"
    target_prec: float = 0.6,
    label_cost_map: Optional[Dict[str, float]] = None,  # {"LBL_CARE": 6, ...}
    dump_importance: bool = True,
    dump_prcurve: bool = True,
    id_col: Optional[str] = None,        # 개인기준 Δ/Trend 계산용 (없으면 집계기준 사용)
    use_target_rate_tuner: bool = True,  # 컷 튜너 on/off
    prec_labels: Optional[set] = None,
    per_label_target_map: Optional[Dict[str, float]] = None,
):
    # 기본 경로: 이 파일 기준(project/)
    here = Path(__file__).resolve().parent
    if rules_path is None:
        rules_path = str(here / "rules.yml")
    if centers_path is None:
        centers_path = str(here / "cluster_centers.csv")
    if exclude_months is None:
        exclude_months = [
            pd.Timestamp("2024-06-01"),
            pd.Timestamp("2024-08-01"),
            pd.Timestamp("2024-09-01"),
        ]
    os.makedirs(out_dir, exist_ok=True)

    # 0) 로드 & year_month 보장
    df = pd.read_csv(csv_path)
    df = ensure_year_month(df)
    
    df = ensure_all_standardized_features(df, month_col="year_month")


    # 1) 규칙 라벨 + SCORE 생성
    df_lbl = apply_rule_hybrid(df.copy())
    lbl_cols = [c for c in df_lbl.columns if c.startswith("LBL_") and df_lbl[c].dtype == bool]
    rules_meta_for_scores = load_rules(rules_path)
    df_lbl = _build_proxy_scores(df_lbl, rules_meta_for_scores, lbl_cols)
    df_lbl = _ensure_default_scores(df_lbl, lbl_cols)  # 규칙 없어도 SCORE_* 강제 생성

    # 1-1) 품질월 제외 및 시간 마스크 (자동 분할에 사용)
    mask_ex = ~df_lbl["year_month"].isin(exclude_months)
    mask_train = (df_lbl["year_month"] < cut_cal_from) & mask_ex

    run_diagnostic_check(df_lbl, rules_meta_for_scores, lbl_cols, mask_train)

    # 1-2) single-class 라벨 자동 분할(GMM/KMeans)
    df_lbl = auto_split_single_class_labels(df_lbl, lbl_cols, mask_train,
                                            min_pos_rate=0.02, max_pos_rate=0.20)

    # 1-3) (선택) 라벨율 목표 맞추는 튜너
    if use_target_rate_tuner:
        target_rate_map = {
            "LBL_LIVELIHOOD": 0.05,
            "LBL_CARE": 0.08,
            "LBL_HEALTH_MENTAL_DELTA": 0.05,
            "LBL_DAILY_LONGTERM": 0.05,
            "LBL_HOUSING": 0.05,
            "LBL_EMPLOYMENT": 0.07,
            "LBL_DEBT_LAW": 0.032,
            "LBL_ISOLATION": 0.05,
        }
        df_lbl = _tune_labels_by_scores(df_lbl, lbl_cols, target_rate_map)

    # 1-4) 시간 인지형 백스톱 + 지속성 필터 (라벨 소멸 방지)
    # Δ/Trend 안정 구간(최초 6/12개월)은 보수적으로 False 처리 (초기 흔들림 제거)
    min_month_delta = df_lbl["year_month"].min() + pd.DateOffset(months=6)
    min_month_trend = df_lbl["year_month"].min() + pd.DateOffset(months=12)

    if "LBL_HEALTH_MENTAL_DELTA" in df_lbl.columns:
        df_lbl.loc[df_lbl["year_month"] < min_month_delta, "LBL_HEALTH_MENTAL_DELTA"] = False

    if "LBL_DAILY_LONGTERM" in df_lbl.columns:
        df_lbl.loc[df_lbl["year_month"] < min_month_trend, "LBL_DAILY_LONGTERM"] = False

    # 두 라벨에 한정해 월별 백스톱 튜닝 적용 (월별 최소 양성 보장 - 다소 보수화)
    for LBL, SCORE, base_rate, min_pos, relax_q in [
        ("LBL_HEALTH_MENTAL_DELTA", "SCORE_HEALTH_MENTAL_DELTA", 0.0513, 15, 0.95),
        ("LBL_DAILY_LONGTERM",      "SCORE_DAILY_LONGTERM",      0.0513, 15, 0.95),
    ]:
        if LBL in df_lbl.columns and SCORE in df_lbl.columns:
            df_lbl = timeaware_backstop_tuner(
                df_lbl, LBL, SCORE,
                month_col="year_month",
                base_rate=base_rate,
                min_pos_per_month=min_pos,
                max_relax_quantile=relax_q
            )

  # 복합 키 구성: id가 있으면 id만, 없으면 가능한 카테고리들을 모두 사용
    persistence_keys = ([id_col] if (id_col and id_col in df_lbl.columns) else
                        [c for c in ["행정동코드", "자치구", "성별", "연령대"] if c in df_lbl.columns])

    # Δ 급변
    if "LBL_HEALTH_MENTAL_DELTA" in df_lbl.columns:
        df_lbl = apply_persistence(
            df_lbl, "LBL_HEALTH_MENTAL_DELTA",
            id_col=id_col, group_col=persistence_keys, month_col="year_month",
            window=4, min_hits=3
        )

    # 장기
    if "LBL_DAILY_LONGTERM" in df_lbl.columns:
        df_lbl = apply_persistence(
            df_lbl, "LBL_DAILY_LONGTERM",
            id_col=id_col, group_col=persistence_keys, month_col="year_month",
            window=7, min_hits=4
        )

    if {"LBL_HEALTH_MENTAL_DELTA", "LBL_DAILY_LONGTERM"}.issubset(df_lbl.columns):
        _chk = (
            df_lbl.groupby("year_month")[["LBL_HEALTH_MENTAL_DELTA", "LBL_DAILY_LONGTERM"]]
                  .mean()
                  .tail(6)
        )
        print("\n[CHECK] 최근 6개월 라벨율(월 평균):")
        print(_chk.to_string())
        print("[CHECK] 최근 6개월 평균율:",
              {c: round(float(_chk[c].mean()), 4) for c in _chk.columns})
    else:
        for c in ["LBL_HEALTH_MENTAL_DELTA", "LBL_DAILY_LONGTERM"]:
            if c in df_lbl.columns:
                print(f"[CHECK] {c} 최근 6개월:",
                      df_lbl.groupby("year_month")[c].mean().tail(6).to_string())    
 

    # 2) 피처셋(표준화 + Δ/Trend + 소프트페르소나 + 인구통계)
    base_std = [
        # 기존 핵심
        "평일 총 이동 거리 합계_std", "휴일 총 이동 거리 합계_std",
        "동영상/방송 서비스 사용일수_std", "게임 서비스 사용일수_std",
        "지하철이동일수 합계_std", "집 추정 위치 평일 총 체류시간_std",
        "평균 통화대상자 수_std", "평균 문자량_std",
        "평일 총 이동 횟수_std",
        "주간상주지 변경횟수 평균_std", "야간상주지 변경횟수 평균_std",

        # 그룹 C(생계/채무) 보강: 금융/소비
        "소액결재 사용금액 평균_std", "소액결재 사용횟수 평균_std",
        "최근 3개월 내 요금 연체 비율_std",
        "쇼핑 서비스 사용일수_std", "금융 서비스 사용일수_std",
        "배달 서비스 사용일수_std",
    ]
    # 실제 존재 컬럼으로 안전 매핑(_resolve_col 사용)
    BASE_STD = [c for c in [_resolve_col(df_lbl, name) for name in base_std] if c]

    # Δ3m, Trend12m은 실제 _std 컬럼들 기준으로 사용 가능한 것만 채택
    DELTA3M = [c + "_delta3m" for c in BASE_STD if (c + "_delta3m") in df_lbl.columns]
    TREND12 = [c + "_trend12m" for c in BASE_STD if (c + "_trend12m") in df_lbl.columns]

    X = df_lbl[["year_month"] + BASE_STD + DELTA3M + TREND12].copy()


    
    # 소프트 페르소나 (견고 가드: 실패 시 폴백)
    # 0) 혹시 기존에 persona_*가 이미 붙어 있으면 제거(중복 조인 방지)
    X = X.drop(columns=[c for c in X.columns if str(c).startswith("persona_")],
            errors="ignore")

    try:
        centers = load_centers(centers_path)          # persona_soft.load_centers
        P = soft_membership(df_lbl, centers, temp=1.0)  # persona_soft.soft_membership
        # (선택) 확인 로그
        pcols = [c for c in P.columns if str(c).startswith("persona_")]
        print(f"[PERSONA] added: {pcols}")
        if "persona_label" in P.columns:
            print("[PERSONA] label ratio:",
                P["persona_label"].value_counts(normalize=True).round(3).to_dict())
    except Exception as e:
        print(f"[WARN] persona centers load/apply failed → fallback to zeros ({e})")
        # 센터 실패 시 안전 폴백(3개 클러스터 가정; 필요하면 개수 바꿔도 됨)
        n = len(df_lbl)
        P = pd.DataFrame({
            "persona_p0": np.zeros(n, dtype=float),
            "persona_p1": np.zeros(n, dtype=float),
            "persona_p2": np.zeros(n, dtype=float),
            "persona_label": np.zeros(n, dtype=int),
            "persona_conf": np.zeros(n, dtype=float),
        }, index=df_lbl.index)

    # 1) 한 번만 조인
    X = X.join(P, how="left")   

    # 인구통계 원-핫
    CAT = [c for c in ["자치구", "성별", "연령대"] if c in df_lbl.columns]
    X = X.join(df_lbl[CAT])
    X = pd.get_dummies(X, columns=CAT, dummy_na=False)

    # 3) 시간 분할 & 품질월 제외(최종)
    mask_ex2 = ~X["year_month"].isin(exclude_months)
    X = X.loc[mask_ex2].copy()
    Y = df_lbl.loc[mask_ex2, ["year_month"] + lbl_cols].copy()

    mask_train = Y["year_month"] < cut_cal_from
    mask_cal = (Y["year_month"] >= cut_cal_from) & (Y["year_month"] < cut_test_from)
    mask_test = Y["year_month"] >= cut_test_from

    X_train = X.loc[mask_train].drop(columns=["year_month"]).fillna(0)
    X_cal = X.loc[mask_cal].drop(columns=["year_month"]).fillna(0)
    X_test = X.loc[mask_test].drop(columns=["year_month"]).fillna(0)

    # 상수/준상수 피처 제거
    X_train, X_cal, X_test, dropped_const = drop_low_variance_features(X_train, X_cal, X_test)
    if dropped_const:
        print(f"[WARN] Drop constant features: {len(dropped_const)}")

    # 4) 모델 학습 + 캘리브레이션 + 임계값
    try:
        import lightgbm as lgb
        def new_clf():
            return lgb.LGBMClassifier(
                n_estimators=400, learning_rate=0.05, num_leaves=127,
                min_data_in_leaf=30, min_child_samples=30,
                subsample=0.8, colsample_bytree=0.8,
                class_weight="balanced", objective="binary",
                random_state=42, n_jobs=-1, verbose=-1,
            )
    except Exception:
        from sklearn.linear_model import LogisticRegression
        def new_clf():
            return LogisticRegression(
                penalty="l2", C=1.0, max_iter=2000, class_weight="balanced", n_jobs=-1
            )

    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.metrics import average_precision_score, f1_score, recall_score, precision_score, precision_recall_curve
    from joblib import dump, load as joblib_load

    models: Dict[str, Dict] = {}
    rows = []

    all_feat_cols = list(X_train.columns)
    rules_meta = load_rules(rules_path)  # 규칙-피처 제외에 활용
    label_cost_map = label_cost_map or {}
    prec_labels = set(prec_labels or [])

    for lbl in lbl_cols:
        y_tr = Y.loc[mask_train, lbl].astype(int).to_numpy()
        y_ca = Y.loc[mask_cal, lbl].astype(int).to_numpy()
        y_te = Y.loc[mask_test, lbl].astype(int).to_numpy()

        n_tr_pos, n_tr = int(y_tr.sum()), int(len(y_tr))
        n_ca_pos, n_ca = int(y_ca.sum()), int(len(y_ca))
        n_te_pos, n_te = int(y_te.sum()), int(len(y_te))

        # 충분치 않으면 스킵
        if n_tr_pos < 100 or n_ca_pos < 20:
            rows.append({"label": lbl, "note": "skip(low positives)",
                         "train_pos": n_tr_pos, "cal_pos": n_ca_pos, "test_pos": n_te_pos})
            continue

        # 학습 세트 단일 클래스면 스킵
        if n_tr_pos == 0 or (n_tr_pos == n_tr):
            rows.append({"label": lbl, "note": "skip(single-class train)",
                         "train_pos": n_tr_pos, "cal_pos": n_ca_pos, "test_pos": n_te_pos})
            continue

        # 라벨별 규칙-피처 강제 제외(누수 방지)
        rule_drop_cols = _rule_cols_for(lbl, rules_meta, all_feat_cols, drop_ohe_from_gates=True)
        feat_cols = [c for c in all_feat_cols if c not in rule_drop_cols]
        if rule_drop_cols:
            preview = ", ".join(sorted(rule_drop_cols)[:6]) + (" ..." if len(rule_drop_cols) > 6 else "")
            print(f"[RULE] {lbl}: drop {len(rule_drop_cols)} rule cols → {preview}")

        # 라벨별 누수(완전 일치/보색) 제거
        leak_cols = _find_trivial_leak_cols(X_train[feat_cols], y_tr, max_report=50)
        feat_cols = [c for c in feat_cols if c not in leak_cols]
        if leak_cols:
            print(f"[LEAK] {lbl}: remove {len(leak_cols)} cols")

        # 학습/평가 X
        Xtr = X_train[feat_cols]; Xca = X_cal[feat_cols]; Xte = X_test[feat_cols]

        clf = new_clf()
        clf.fit(Xtr, y_tr)

        # 캘리브레이션 가능 여부
        has_two_ca = (n_ca_pos > 0) and (n_ca_pos < n_ca)
        use_cal_for_thr = has_two_ca and (n_ca_pos >= 20)

        if has_two_ca:
            try:
                cal = CalibratedClassifierCV(clf, method="isotonic", cv="prefit")
                cal.fit(Xca, y_ca)
            except Exception:
                cal = CalibratedClassifierCV(clf, method="sigmoid", cv="prefit")
                cal.fit(Xca, y_ca)
            use_est = cal
        else:
            cal = None
            use_est = clf

        # 임계값 기준세트 선택
        if use_cal_for_thr:
            base_name, y_base, p_base = "cal",   y_ca, _safe_proba(use_est, Xca)
        else:
            base_name, y_base, p_base = "train", y_tr, _safe_proba(use_est, Xtr)

        # ---- 라벨별 전략 오버라이드 여부
        # ---- 라벨별 전략 결정
        per_lbl_target = None if per_label_target_map is None else per_label_target_map.get(lbl)

        # rec_at_prec를 쓸지 여부: prec_labels에 있거나 per_label_target을 지정했을 때
        use_rec_override = (lbl in (prec_labels or set())) or (per_lbl_target is not None)

        if use_rec_override:
            tprec = per_lbl_target if per_lbl_target is not None else target_prec
            thr = pick_threshold_rec_at_prec(y_base, p_base, target_prec=tprec)
            cmsg = f"target_prec={tprec:.2f}" + (" (per-label)" if per_lbl_target is not None else " (override)")
            thr_used = "rec_at_prec"
        else:
            if thr_strategy == "f1":
                thr = pick_threshold_f1(y_base, p_base)
                cmsg = "cost_fn=-"
                thr_used = "f1"
            elif thr_strategy == "rec_at_prec":
                thr = pick_threshold_rec_at_prec(y_base, p_base, target_prec=target_prec)
                cmsg = f"target_prec={target_prec:.2f}"
                thr_used = "rec_at_prec"
            else:  # "cost"
                cf = float(label_cost_map.get(lbl, cost_fn))
                thr = pick_threshold_cost(y_base, p_base, cost_fn=cf, cost_fp=cost_fp)
                cmsg = f"cost_fn={cf}"
                thr_used = "cost"


    
    

        # 기준세트에서 프리뷰
        yhat_base = (p_base >= thr).astype(int)
        prec_base = precision_score(y_base, yhat_base, zero_division=0)
        rec_base  = recall_score(y_base, yhat_base, zero_division=0)
        print(f"[THR] {lbl}: strategy={thr_used}, base={base_name}, thr={thr:0.3f}, {cmsg} → prec_base={prec_base:0.3f}, rec_base={rec_base:0.3f}")

        # Test 확률 및 메트릭 계산
        if len(y_te) > 0:
            p_te = _safe_proba(use_est, Xte)
            if len(p_te) == len(y_te):
                yhat = (p_te >= thr).astype(int)
                pr_auc = average_precision_score(y_te, p_te) if n_te_pos > 0 else np.nan
                rec = recall_score(y_te, yhat, average='binary', zero_division=0) if n_te_pos > 0 else np.nan
                f1 = f1_score(y_te, yhat, average='binary', zero_division=0) if n_te_pos > 0 else np.nan
            else:
                pr_auc = rec = f1 = np.nan
        else:
            p_te = np.array([])
            pr_auc = rec = f1 = np.nan

        # 모델 저장
        model_path = os.path.join(out_dir, f"model_{lbl}.joblib")
        dump(use_est, model_path)

        # 중요도 덤프
        if dump_importance:
            try:
                if hasattr(clf, "feature_importances_"):
                    fi = pd.Series(clf.feature_importances_, index=feat_cols).sort_values(ascending=False)
                elif hasattr(clf, "coef_"):
                    fi = pd.Series(np.abs(clf.coef_[0]), index=feat_cols).sort_values(ascending=False)
                else:
                    fi = None
                if fi is not None:
                    fi.head(200).to_csv(os.path.join(out_dir, f"feature_importance_{lbl}.csv"),
                                        index=True, header=["importance"], encoding="utf-8-sig")
            except Exception:
                pass

        # PR 커브 덤프
        if dump_prcurve and len(np.unique(y_base)) == 2:
            try:
                prec, rec_curve, thr_arr = precision_recall_curve(y_base, p_base)
                prdf = pd.DataFrame({
                    "threshold": np.r_[np.nan, thr_arr],
                    "precision": prec,
                    "recall": rec_curve
                })
                prdf.to_csv(os.path.join(out_dir, f"prcurve_{lbl}_{base_name}.csv"),
                            index=False, encoding="utf-8-sig")
            except Exception:
                pass

        models[lbl] = {
            "model_path": model_path,
            "threshold": float(thr),
            "threshold_strategy": thr_used,
            "target_precision": target_prec if thr_strategy == "rec_at_prec" else None,
            "cost_fn_used": float(label_cost_map.get(lbl, cost_fn)) if thr_strategy == "cost" else None,
            "calibrated": bool(cal is not None),
            "features": feat_cols,
            "dropped_rule_features": rule_drop_cols,
            "dropped_leak_features": leak_cols,
        }

        rows.append({
            "label": lbl,
            "train_pos": n_tr_pos,
            "cal_pos": n_ca_pos,
            "test_pos": n_te_pos,
            "thr": float(thr),
            "PR_AUC_test": float(pr_auc) if not np.isnan(pr_auc) else np.nan,
            "Recall@thr":  float(rec)    if not np.isnan(rec)    else np.nan,
            "F1@thr":      float(f1)     if not np.isnan(f1)     else np.nan,
            "note": None if has_two_ca else "no-cal(single-class cal)",
        })

    metrics_df = pd.DataFrame(rows).sort_values("PR_AUC_test", ascending=False, na_position="last")

    # 5) 모니터링 베이스라인 저장
    baseline: Dict[str, Dict] = {"feature_hist": {}, "timestamp": datetime.now().isoformat()}
    ref = X_train
    for c in ref.columns[:200]:
        s = pd.to_numeric(ref[c], errors="coerce").astype(float)
        qs = np.quantile(s.dropna().values, np.linspace(0, 1, 21))
        baseline["feature_hist"][c] = {"q": as_pyfloat_list(qs)}

    # pred_hist
    baseline["pred_hist"] = {}
   
    for lbl, obj in models.items():
        try:
            est = joblib_load(obj["model_path"])
            feats = obj["features"]
            p_ref = _safe_proba(est, ref[feats])
            qs = np.quantile(p_ref, np.linspace(0, 1, 21))
            baseline["pred_hist"][lbl] = {"q": as_pyfloat_list(qs)}
        except Exception:
            continue

    # 6) 월별 라벨율 저장
    try:
        label_rate = Y.groupby("year_month")[lbl_cols].mean().reset_index().sort_values("year_month")
        label_rate.to_csv(os.path.join(out_dir, "label_rate_by_month.csv"),
                          index=False, encoding="utf-8-sig")
        # quick preview
        for c in ["LBL_HEALTH_MENTAL_DELTA", "LBL_DAILY_LONGTERM"]:
            if c in label_rate.columns:
                mpos = (label_rate[c] > 0).sum()
                print(f"[CHECK] {c}: 양성 월 수 = {mpos}, 최근 6개월 평균율 = {label_rate.tail(6)[c].mean():.4f}")
    except Exception:
        pass

    # 7) 아티팩트 저장
    with open(os.path.join(out_dir, "thresholds.json"), "w", encoding="utf-8") as f:
        json.dump({k: v["threshold"] for k, v in models.items()}, f, ensure_ascii=False, indent=2)

    rules_meta_for_meta = load_rules(rules_path)
    meta = {
        "created_at": datetime.now().isoformat(),
        "rules_version": rules_version(rules_meta_for_meta),
        "exclude_months": [str(x.date()) for x in exclude_months],
        "cut_cal_from": str(cut_cal_from.date()),
        "cut_test_from": str(cut_test_from.date()),
        "cost_fn_default": cost_fn,
        "cost_fp": cost_fp,
        "threshold_strategy": thr_strategy,
        "target_precision": target_prec,
        "label_cost_map": label_cost_map,
        "all_features": list(X_train.columns),
        "labels": [c for c in Y.columns if c.startswith("LBL_")],
        "ohe_categories": [c for c in X_train.columns if any(k in c for k in ["자치구_", "성별_", "연령대_"])],
        "dropped_constant_features": dropped_const,
        "per_label_features": {k: v["features"] for k, v in models.items()},
        "per_label_rule_drops": {k: v["dropped_rule_features"] for k, v in models.items()},
        "per_label_leak_drops": {k: v["dropped_leak_features"] for k, v in models.items()},
    }
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out_dir, "monitor_baseline.json"), "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False)

    metrics_csv = os.path.join(out_dir, "metrics.csv")
    metrics_df.to_csv(metrics_csv, index=False, encoding="utf-8-sig")

    return metrics_df, models


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv_path", default="telecom_group_monthly_all.csv")
    ap.add_argument("--rules_path", default=None)      # None → project/rules.yml
    ap.add_argument("--centers_path", default=None)    # None → project/cluster_centers.csv
    ap.add_argument("--out_dir", default="artifacts")
    ap.add_argument("--cut_cal_from", default="2024-07-01")
    ap.add_argument("--cut_test_from", default="2025-01-01")
    ap.add_argument("--cost_fn", type=float, default=20.0)
    ap.add_argument("--cost_fp", type=float, default=1.0)
    ap.add_argument("--thr_strategy", choices=["cost", "f1", "rec_at_prec"], default="cost")
    ap.add_argument("--target", type=float, default=0.6, help="rec_at_prec 목표 precision")
    ap.add_argument("--label_cost_map", default="", help='예: "LBL_CARE:6,LBL_LIVELIHOOD:25"')
    ap.add_argument("--dump_importance", action="store_true")
    ap.add_argument("--dump_prcurve", action="store_true")
    ap.add_argument("--id_col", default=None, help="개인 기준 Δ/Trend 계산용 ID 컬럼명")
    ap.add_argument("--no_tuner", action="store_true", help="컷 튜너 비활성화")
    ap.add_argument(
        "--prec_labels",
        default="",
        help='rec_at_prec을 적용할 라벨 콤마리스트 (예: "LBL_HOUSING,LBL_EMPLOYMENT,LBL_LIVELIHOOD,LBL_DEBT_LAW")'
    )
    ap.add_argument(
        "--per_label_target",
        default="",
        help='라벨별 precision 타겟. 예: "LBL_LIVELIHOOD:0.70,LBL_HOUSING:0.75"'
    )
        
    args = ap.parse_args()
    prec_labels = set([s.strip() for s in args.prec_labels.split(",") if s.strip()])

    # per_label_target 파싱
    per_label_target_map: Dict[str, float] = {}
    if args.per_label_target:
        for token in args.per_label_target.split(","):
            token = token.strip()
            if not token: 
                continue
            k, v = token.split(":")
            per_label_target_map[k.strip()] = float(v)



    # label_cost_map 파싱
    lmap: Dict[str, float] = {}
    if args.label_cost_map:
        for token in args.label_cost_map.split(","):
            token = token.strip()
            if not token: continue
            k, v = token.split(":")
            lmap[k.strip()] = float(v)

    m, _ = train_multilabel_with_calibration(
        csv_path=args.csv_path,
        rules_path=args.rules_path,
        centers_path=args.centers_path,
        out_dir=args.out_dir,
        cut_cal_from=pd.Timestamp(args.cut_cal_from),
        cut_test_from=pd.Timestamp(args.cut_test_from),
        cost_fn=args.cost_fn, cost_fp=args.cost_fp,
        thr_strategy=args.thr_strategy, target_prec=args.target,
        label_cost_map=lmap,
        dump_importance=args.dump_importance,
        dump_prcurve=args.dump_prcurve,
        id_col=args.id_col,
        use_target_rate_tuner=not args.no_tuner,
        prec_labels=prec_labels,
        per_label_target_map=per_label_target_map,
    )
    print(m.head(20))







