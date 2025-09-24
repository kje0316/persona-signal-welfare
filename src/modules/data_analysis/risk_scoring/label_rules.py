# project/label_rules.py
# -*- coding: utf-8 -*-
import re, numpy as np, pandas as pd

def _has(df, c): 
    return (c is not None) and (c in df.columns)

def _col(df, name):
    if not name:
        return None
    if name in df.columns:
        return name
    cand = [c for c in df.columns if isinstance(c, str) and name in c]
    return cand[0] if cand else None

def _col_sfx(df, base_name, sfx):
    base = _col(df, base_name)
    if not base:
        return None
    cand = base + sfx
    return cand if cand in df.columns else None

def _rank_mask(series, by_month, side, q):
    pct = series.groupby(by_month).rank(pct=True, na_option="keep")
    return (pct >= q) if side == "ge" else (pct <= q)

def _robust_z_by_month(s, month_col):
    x   = pd.to_numeric(s, errors="coerce")
    g   = x.groupby(month_col)
    med = g.transform("median")
    iqr = g.transform(lambda v: v.quantile(0.75) - v.quantile(0.25))
    mad = g.transform(lambda v: (v - v.median()).abs().median())
    std = g.transform("std")
    scale = iqr.mask(iqr==0, np.nan)
    scale = scale.fillna(mad.replace(0, np.nan)).fillna(std.replace(0, np.nan)).fillna(1.0)
    return (x - med) / scale.replace(0, 1.0)

def _ensure_delta3m(df, base_cols, unit_cols, month_col):
    out = df.sort_values((unit_cols or []) + [month_col]).copy()
    base_cols = [c for c in base_cols if c and c in out.columns]
    for c in base_cols:
        dcol = c + "_delta3m"
        if dcol in out.columns:
            continue
        grp = (unit_cols or [month_col])
        cur3  = out.groupby(grp)[c].transform(lambda x: x.rolling(3, min_periods=3).mean())
        prev3 = out.groupby(grp)[c].transform(lambda x: x.shift(3).rolling(3, min_periods=3).mean())
        out[dcol] = cur3 - prev3
    return out

def _age_to_num(s: pd.Series) -> pd.Series:
    if s is None:
        return pd.Series(dtype=float)
    if np.issubdtype(s.dtype, np.number):
        return s.astype(float)
    def parse_one(v):
        if pd.isna(v): return np.nan
        m = re.search(r"\d+", str(v))
        return float(m.group()) if m else np.nan
    return s.map(parse_one)

# ✅ 벡터화된 사유 추가 헬퍼
def _append_reason(reasons: pd.Series, mask: pd.Series, desc: str) -> pd.Series:
    base = reasons.fillna("").astype(str)
    m = mask.fillna(False).astype(bool)
    sep = np.where(base.ne(""), "; ", "")
    new_vals = np.where(m, base + sep + (desc or ""), base)
    return pd.Series(new_vals, index=reasons.index, dtype=object)

def apply_rule_hybrid(df: pd.DataFrame,
                      month_col: str = "year_month",
                      z_thr: float = 1.64) -> pd.DataFrame:
    out = df.copy()

    unit_cols = [c for c in ["자치구", "성별", "연령대"] if c in out.columns]
    if not unit_cols:
        unit_cols = ["행정동"] if "행정동" in out.columns else []

    out["_AGE_NUM"] = _age_to_num(out["연령대"]) if "연령대" in out.columns else pd.Series(index=out.index, dtype=float)

    # 연체 열 및 Δ 생성(필요 시)
    LATE = _col(out, "최근 3개월 내 요금 연체 비율")
    if LATE:
        out = _ensure_delta3m(out, [LATE], unit_cols, month_col)

    RULES = {
        "LBL_LIVELIHOOD": {
            "cut": 1.0, "req_frac": 0.7,
            "signals": [
                {"col": LATE, "mode": "delta_z", "side": "ge", "w": 0.60, "desc": "연체 Δ↑(유의)"},
                {"col": _col(out, "소액결재 비사용 인구수_pc_std"), "mode": "qscore", "side": "ge", "q": 0.85, "w": 0.25, "desc": "소액결제 비사용↑"},
                {"col": _col(out, "소액결재 사용금액_pc_std"),     "mode": "qscore", "side": "le", "q": 0.15, "w": 0.15, "desc": "소액결제 금액↓"},
            ],
            "gate": None
        },
        "LBL_CARE": {
            "cut": 1.0, "req_frac": 0.6,
            "signals": [
                {"col": _col(out, "평일 총 이동 거리 합계_pc_std"),         "mode": "qscore", "side": "le", "q": 0.15, "w": 0.25, "desc": "이동거리↓"},
                {"col": _col(out, "지하철이동일수 합계_pc_std"),           "mode": "qscore", "side": "le", "q": 0.15, "w": 0.20, "desc": "지하철↓"},
                {"col": _col(out, "집 추정 위치 평일 총 체류시간_pc_std"), "mode": "qscore", "side": "ge", "q": 0.85, "w": 0.15, "desc": "집체류↑"},
            ],
            "gate": {"expr": (out["_AGE_NUM"] >= 65), "desc": "연령대≥65", "w": 0.40, "hard_and": True}
        },
        "LBL_HEALTH_MENTAL_DELTA": {
            "cut": 1.0, "req_frac": 0.6,
            "signals": [
                {"col": _col_sfx(out, "평일 총 이동 거리 합계_pc_std",         "_delta3m"), "mode":"qscore","side":"le","q":0.15,"w":0.40,"desc":"이동 Δ↓"},
                {"col": _col_sfx(out, "집 추정 위치 평일 총 체류시간_pc_std", "_delta3m"), "mode":"qscore","side":"ge","q":0.85,"w":0.35,"desc":"집체류 Δ↑"},
                {"col": _col_sfx(out, "동영상/방송 서비스 사용일수_pc_std",   "_delta3m"), "mode":"qscore","side":"ge","q":0.85,"w":0.25,"desc":"동영상 Δ↑"},
            ],
            "gate": None
        },
        "LBL_DAILY_LONGTERM": {
            "cut": 1.0, "req_frac": 0.6,
            "signals": [
                {"col": _col_sfx(out, "평일 총 이동 거리 합계_pc_std", "_trend12m"), "mode":"qscore","side":"le","q":0.15,"w":0.40,"desc":"이동 장기↓"},
                {"col": _col_sfx(out, "지하철이동일수 합계_pc_std",   "_trend12m"), "mode":"qscore","side":"le","q":0.15,"w":0.35,"desc":"지하철 장기↓"},
                {"col": _col_sfx(out, "배달 서비스 사용일수_pc_std",   "_trend12m"), "mode":"qscore","side":"ge","q":0.85,"w":0.25,"desc":"배달 장기↑"},
            ],
            "gate": None
        },
        "LBL_HOUSING": {
            "cut": 1.0, "req_frac": 0.8,
            "signals": [
                {"col": _col(out, "주간상주지 변경횟수 평균_pc_std"), "mode":"qscore","side":"ge","q":0.85,"w":0.50,"desc":"주간 상주지변경↑"},
                {"col": _col(out, "야간상주지 변경횟수 평균_pc_std"), "mode":"qscore","side":"ge","q":0.85,"w":0.50,"desc":"야간 상주지변경↑"},
            ],
            "gate": None
        },
        "LBL_EMPLOYMENT": {
            "cut": 1.0, "req_frac": 0.6,
            "signals": [
                {"col": _col(out, "평균 근무시간 평균_pc_std") or _col(out, "평균 근무시간_pc_std"),
                 "mode":"qscore","side":"le","q":0.15,"w":0.45,"desc":"근무시간↓"},
                {"col": _col(out, "지하철이동일수 합계_pc_std"), "mode":"qscore","side":"le","q":0.15,"w":0.30,"desc":"지하철↓"},
                {"col": _col(out, "평일 총 이동 횟수_pc_std"),   "mode":"qscore","side":"le","q":0.15,"w":0.25,"desc":"평일 이동횟수↓"},
            ],
            "gate": None
        },
        "LBL_DEBT_LAW": {
            "cut": 1.0, "req_frac": 1.0,
            "signals": [
                {"col": LATE, "mode":"delta_z", "side":"ge", "w":1.00, "desc":"연체 Δ↑(유의)"},
            ],
            "gate": None
        },
        "LBL_ISOLATION": {
            "cut": 1.0, "req_frac": 0.6,
            "signals": [
                {"col": _col(out, "평균 통화량_pc_std"),          "mode":"qscore","side":"le","q":0.15,"w":0.25,"desc":"통화↓"},
                {"col": _col(out, "평균 문자량_pc_std"),          "mode":"qscore","side":"le","q":0.15,"w":0.25,"desc":"문자↓"},
                {"col": _col(out, "평균 통화대상자 수_pc_std"),    "mode":"qscore","side":"le","q":0.15,"w":0.25,"desc":"대상자수↓"},
                {"col": _col(out, "평일 총 이동 거리 합계_pc_std"), "mode":"qscore","side":"le","q":0.15,"w":0.15,"desc":"이동거리↓"},
                {"col": _col(out, "집 추정 위치 평일 총 체류시간_pc_std"), "mode":"qscore","side":"ge","q":0.85,"w":0.10,"desc":"집체류↑"},
            ],
            "gate": None
        },
    }

    for lbl, cfg in RULES.items():
        score   = pd.Series(0.0, index=out.index, dtype=float)
        reasons = pd.Series("",   index=out.index, dtype=object)

        gate_mask = pd.Series(True, index=out.index)
        gate_w    = 0.0
        if cfg.get("gate") is not None:
            g = cfg["gate"]
            gate_mask = g["expr"].fillna(False) if g.get("hard_and", True) else g["expr"].fillna(True)
            gate_w    = float(g.get("w", 0.0))
            score    += np.where(gate_mask, gate_w, 0.0)
            reasons   = _append_reason(reasons, gate_mask, g.get("desc",""))

        # 사용 가능한 신호 총 가중치
        avail_w = 0.0
        for s in cfg["signals"]:
            col = s["col"]
            if s["mode"] == "delta_z":
                ok = _has(out, col) and _has(out, col + "_delta3m")
            else:
                ok = _has(out, col)
            if ok:
                avail_w += float(s.get("w", 0.0))

        # 신호 적용
        for s in cfg["signals"]:
            col = s["col"]
            if s["mode"] == "qscore":
                if not _has(out, col): 
                    continue
                mask = _rank_mask(out[col], out[month_col], s["side"], s["q"])
            elif s["mode"] == "delta_z":
                if not (_has(out, col) and _has(out, col + "_delta3m")):
                    continue
                z = _robust_z_by_month(out[col + "_delta3m"], out[month_col])
                mask = (z >= z_thr) if s["side"] == "ge" else (z <= -z_thr)
            else:
                continue

            w = float(s.get("w", 0.0))
            score   += np.where(mask, w, 0.0)
            reasons  = _append_reason(reasons, mask, s.get("desc",""))

        req_frac = float(cfg.get("req_frac", 0.6))
        thr = cfg.get("cut", 1.0) * req_frac * (avail_w + gate_w * gate_mask.astype(float))
        out[lbl + "_score"]   = score
        out[lbl + "_reasons"] = reasons.replace("", np.nan)
        out[lbl]              = (gate_mask) & (score >= thr)

    return out
