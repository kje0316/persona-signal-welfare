# -*- coding: utf-8 -*-
"""
preprocess.py — 공통 전처리/파생/정규화/품질 유틸
"""

from __future__ import annotations
from typing import List, Tuple, Dict
import re
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

# ---------------------------
# year_month & 대표수치 & per-capita
# ---------------------------
def ensure_year_month(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "year_month" in out.columns and np.issubdtype(out["year_month"].dtype, np.datetime64):
        return out
    if "month" in out.columns:
        try:
            out["year_month"] = pd.to_datetime(out["month"]).dt.to_period("M").dt.to_timestamp()
            return out
        except Exception:
            pass
    if {"year", "month_num"}.issubset(out.columns):
        out["year_month"] = pd.to_datetime(dict(
            year=out["year"].astype(int),
            month=out["month_num"].astype(int),
            day=1
        ))
        return out
    raise ValueError("year_month 생성 실패: month 또는 (year, month_num) 필요")

def pick_median_quartile_columns(cols: List[str]) -> List[str]:
    keep = set(cols)
    pattern = r": 4분위수, (25%|50%|75%)$"
    groups: Dict[str, List[str]] = {}
    for c in cols:
        m = re.search(pattern, c)
        if m:
            base = re.sub(pattern, "", c).strip()
            groups.setdefault(base, []).append(c)
    for base, grp in groups.items():
        med = [g for g in grp if g.endswith("50%")]
        if med:
            for g in grp:
                if g != med[0] and g in keep:
                    keep.remove(g)
    return [c for c in cols if c in keep]

def make_per_capita(df: pd.DataFrame, num_cols: List[str], one_col: str = "1인가구수") -> pd.DataFrame:
    if one_col not in df.columns:
        raise ValueError(f"{one_col} 컬럼이 없습니다.")
    out = df.copy()
    den = out[one_col].replace(0, np.nan)
    for c in num_cols:
        if "미추정" in c:
            continue
        out[c + "_pc"] = out[c] / den
    return out

# ---------------------------
# 드리프트/품질
# ---------------------------
def _psi(a: pd.Series, b: pd.Series, bins: int = 20, eps: float = 1e-12) -> float:
    a = pd.Series(a).dropna()
    b = pd.Series(b).dropna()
    qs = np.linspace(0, 1, bins + 1)
    br = np.unique(np.quantile(pd.concat([a, b]), qs))
    ah, _ = np.histogram(a, br)
    bh, _ = np.histogram(b, br)
    ar = ah / (ah.sum() + eps)
    brt = bh / (bh.sum() + eps)
    return np.sum((ar - brt) * np.log((ar + eps) / (brt + eps)))

def drift_table(df: pd.DataFrame, cols: List[str], by: str = "year_month", topn: int = 10) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    months = sorted(df[by].unique())
    for i in range(1, len(months)):
        m_prev, m_cur = months[i - 1], months[i]
        dfp = df[df[by] == m_prev]
        dfc = df[df[by] == m_cur]
        for col in cols:
            try:
                psi_v = _psi(dfp[col], dfc[col], bins=20)
                ks_v = ks_2samp(dfp[col].dropna(), dfc[col].dropna(), alternative="two-sided", mode="auto").statistic
                rows.append([m_prev, m_cur, col, psi_v, ks_v])
            except Exception:
                continue
    out = pd.DataFrame(rows, columns=["month_prev", "month_cur", "metric", "PSI", "KS"])
    rank = (
        out.sort_values(["month_cur", "PSI"], ascending=[True, False])
        .groupby("month_cur")
        .head(topn)
    )
    return out, rank

def quality_miss_flags(df: pd.DataFrame) -> pd.DataFrame:
    miss_cols = [c for c in df.columns if "미추정" in c]
    if not miss_cols:
        return pd.DataFrame()
    miss_month = df.groupby("year_month")[miss_cols].sum().fillna(0)
    miss_month["_total_miss"] = miss_month.sum(axis=1)
    z = (miss_month["_total_miss"] - miss_month["_total_miss"].mean()) / miss_month["_total_miss"].std(ddof=0)
    return pd.DataFrame({"miss_total": miss_month["_total_miss"], "z": z, "flag": (z.abs() >= 2.0)})

# ---------------------------
# 하이브리드 정규화
# ---------------------------
def monthwise_rank_percent(s: pd.Series, by: pd.Series) -> pd.Series:
    return s.groupby(by).rank(pct=True) * 100

def robust_z_by_month(s: pd.Series, by: pd.Series) -> pd.Series:
    g = s.groupby(by)
    med = g.transform("median")
    iqr = g.transform(lambda x: x.quantile(0.75) - x.quantile(0.25))
    return (s - med) / iqr.replace(0, np.nan)

def hybrid_normalize(
    df: pd.DataFrame,
    count_like_cols: List[str],
    ratio_like_cols: List[str],
    month_col: str = "year_month"
) -> Tuple[pd.DataFrame, List[str]]:
    out = df.copy()
    new_cols: List[str] = []
    for c in count_like_cols:
        out[c + "_lz"] = np.log1p(out[c].clip(lower=0))
        out[c + "_std"] = robust_z_by_month(out[c + "_lz"], out[month_col])
        new_cols.append(c + "_std")
    for c in ratio_like_cols:
        out[c + "_rank"] = monthwise_rank_percent(out[c], out[month_col])
        new_cols.append(c + "_rank")
    return out, new_cols

# ---------------------------
# (선택) 피처 준비 헬퍼
# ---------------------------
def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """군집에 자주 쓰는 per-capita 후보를 하이브리드 정규화까지 한 번에."""
    df = ensure_year_month(df)
    if "총인구" in df.columns:
        df = df.drop(columns=["총인구"])
    num_cols_all = df.select_dtypes(include=[np.number]).columns.tolist()
    num_cols_rep = pick_median_quartile_columns(num_cols_all)
    df = make_per_capita(df, num_cols_rep, one_col="1인가구수")

    cand = [
        "평일 총 이동 거리 합계_pc", "휴일 총 이동 거리 합계_pc", "야간상주지 변경횟수 평균_pc",
        "동영상/방송 서비스 사용일수_pc", "배달 서비스 사용일수_pc", "평균 통화대상자 수_pc",
        "평균 통화량_pc", "데이터 사용량_pc", "쇼핑 서비스 사용일수_pc",
        "금융 서비스 사용일수_pc", "게임 서비스 사용일수_pc", "SNS 사용횟수_pc"
    ]
    cand = [c for c in cand if c in df.columns]

    rank_cols = [c for c in cand if c.endswith("SNS 사용횟수_pc")]
    z_cols = [c for c in cand if c not in rank_cols]
    df_norm, norm_cols = hybrid_normalize(df, z_cols, rank_cols, month_col="year_month")
    return df_norm, norm_cols