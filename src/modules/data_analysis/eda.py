# src/modules/data_analysis/eda.py
# -*- coding: utf-8 -*-
"""
EDA: Cohort Δ3개월 신호 '정확도' 점검 모듈
- 라이브러리 함수 + CLI 지원
- per-capita + 월내 log1p-RobustZ → Δ3개월 → 유의성/크기 게이트 → 지속성/플라시보 평가
"""
from __future__ import annotations
import numpy as np, pandas as pd, warnings, argparse, sys
warnings.filterwarnings("ignore")
pd.set_option("display.width", 180); pd.set_option("display.max_columns", 200)

# ===================== 기본 유틸 =====================
def ensure_year_month(df: pd.DataFrame, month_col: str="year_month") -> pd.DataFrame:
    if month_col in df and np.issubdtype(df[month_col].dtype, np.datetime64):
        return df
    if "month" in df.columns:
        try:
            df[month_col] = pd.to_datetime(df["month"]).dt.to_period("M").dt.to_timestamp(); return df
        except Exception:
            pass
    if {"year","month_num"}.issubset(df.columns):
        df[month_col] = pd.to_datetime(dict(year=df["year"].astype(int), month=df["month_num"].astype(int), day=1)); return df
    raise ValueError("[ensure_year_month] year_month 생성 실패: month / (year, month_num) 중 하나가 필요합니다.")

def make_per_capita(df: pd.DataFrame, base_cols: list[str], den_col: str) -> pd.DataFrame:
    out = df.copy()
    den = out[den_col].replace(0, np.nan)
    for c in base_cols:
        if c in out.columns:
            out[c+"_pc"] = out[c] / den
    return out

def monthwise_robust_z_log1p(df: pd.DataFrame, cols: list[str], month_col: str) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c not in out.columns: 
            continue
        s = np.log1p(out[c].clip(lower=0))
        g = s.groupby(out[month_col])
        med = g.transform("median")
        iqr = g.transform(lambda x: x.quantile(0.75) - x.quantile(0.25))
        out[c + "_std"] = (s - med) / iqr.replace(0, np.nan)
    return out

def compute_delta3m(df: pd.DataFrame, unit_cols: list[str], month_col: str, std_cols: list[str]) -> pd.DataFrame:
    out = df.sort_values(unit_cols + [month_col]).copy()
    for c in std_cols:
        cur3  = out.groupby(unit_cols)[c].transform(lambda x: x.rolling(3, min_periods=3).mean())
        prev3 = out.groupby(unit_cols)[c].transform(lambda x: x.shift(3).rolling(3, min_periods=3).mean())
        out[c+"_delta3m"] = cur3 - prev3
    return out

def add_z_and_flags(df: pd.DataFrame, month_col: str, unit_cols: list[str], std_cols: list[str],
                    z_thr: float=1.96, delta_abs_q: float=0.85) -> pd.DataFrame:
    out = df.copy()
    for c in std_cols:
        rol_std = (out.groupby(unit_cols)[c]
                     .transform(lambda x: x.rolling(12, min_periods=6).std()))
        se = np.sqrt(2*(rol_std**2)/3.0)
        dz = out[c+"_delta3m"]
        out[c+"_z"] = dz / se.replace(0, np.nan)
        # 월별 절대Δ 분위수 컷
        qcut = out.groupby(month_col)[c+"_delta3m"].transform(lambda s: s.abs().quantile(delta_abs_q))
        out[c+"_size_ok"] = dz.abs() >= qcut
        out[c+"_sig_ok"]  = out[c+"_z"].abs() >= z_thr
        out[c+"_flag"]    = out[c+"_size_ok"] & out[c+"_sig_ok"]
    return out

def sustained_hits(df: pd.DataFrame, unit_cols: list[str], month_col: str, std_cols: list[str]) -> pd.DataFrame:
    out_rows=[]
    all_months = sorted(df[month_col].unique())
    next_map = {m: all_months[i+1] if i+1<len(all_months) else pd.NaT for i,m in enumerate(all_months)}
    def get_next(m, k):
        cur=m
        for _ in range(k):
            cur = next_map.get(cur, pd.NaT)
            if pd.isna(cur): return pd.NaT
        return cur

    tmp = df.sort_values(unit_cols+[month_col]).copy()
    for c in std_cols:
        flag_col = f"{c}_flag"
        dz_col   = f"{c}_delta3m"
        rec = df[[*unit_cols, month_col, c, dz_col, flag_col]].dropna(subset=[dz_col])
        rec = rec[rec[flag_col]]
        if rec.empty:
            out_rows.append([c, 0, np.nan, np.nan]); continue

        prev3 = tmp.groupby(unit_cols)[c].transform(lambda x: x.shift(1).rolling(3, min_periods=3).mean())
        tmp["__prev3"] = prev3
        merged = rec.merge(tmp[[*unit_cols, month_col, "__prev3"]], on=[*unit_cols, month_col], how="left").dropna(subset=["__prev3"])

        # 다음달/다다음달 값 조인
        nxt = df[[*unit_cols, month_col, c]].rename(columns={c: "val"})

        for k in (1, 2, 3):
            merged[f"m_plus{k}"] = merged[month_col].apply(lambda m: get_next(m, k))
            merged = merged.merge(
                nxt,
                left_on=[*unit_cols, f"m_plus{k}"],
                right_on=[*unit_cols, month_col],
                how="left",
                suffixes=("", f"_n{k}")   # <-- 핵심: 오른쪽 month_col에 접미사 부여
            )
            # 오른쪽에서 들어온 month_col만 드롭하고 값 컬럼 이름 변경
            merged = merged.drop(columns=[f"{month_col}_n{k}"]).rename(columns={"val": f"x_n{k}"})

        merged["sign_d"] = np.sign(merged[dz_col])
        merged["hit1"] = np.sign(merged["x_n1"] - merged["__prev3"]) == merged["sign_d"]
        merged["x_n13_mean"] = merged[["x_n1","x_n2","x_n3"]].mean(axis=1)
        merged["hit3"] = np.sign(merged["x_n13_mean"] - merged["__prev3"]) == merged["sign_d"]

        n_flag = len(merged)
        h1 = merged["hit1"].mean(skipna=True) if n_flag>0 else np.nan
        h3 = merged["hit3"].mean(skipna=True) if n_flag>0 else np.nan
        out_rows.append([c, n_flag, h1, h3])

    return pd.DataFrame(out_rows, columns=["metric","n_flag","hit_rate_t+1","hit_rate_t+1..t+3"])

def placebo_flag_rate(base: pd.DataFrame, unit_cols: list[str], month_col: str, std_cols: list[str],
                      n_perm: int=30, seed: int=42, max_cohorts: int|None=None) -> pd.Series:
    rng = np.random.RandomState(seed)
    if max_cohorts:
        idx = base.groupby(unit_cols).ngroup()
        keep_ids = np.unique(idx)[:max_cohorts]
        base = base[idx.isin(keep_ids)]
    unit_groups = list(base.groupby(unit_cols))

    rates=[]
    for _ in range(n_perm):
        shuffled = []
        for (_, g) in unit_groups:
            g2 = g.sort_values(month_col).copy()
            vals = g2[month_col].values.copy()
            rng.shuffle(vals)  # 월 순서 섞기
            g2[month_col] = vals
            shuffled.append(g2)
        s_all = pd.concat(shuffled, ignore_index=True).sort_values(unit_cols+[month_col])
        s_all = compute_delta3m(s_all, unit_cols, month_col, std_cols)
        s_all = add_z_and_flags(s_all, month_col, unit_cols, std_cols)
        rates.append({c: s_all[f"{c}_flag"].mean(skipna=True) for c in std_cols})
    return pd.DataFrame(rates).mean().rename("placebo_flag_rate")

# ===================== 상위 API =====================
def delta_accuracy_report(
    df: pd.DataFrame,
    csv_path: str|None = None,
    month_col: str="year_month",
    unit_cols: list[str]|None=None,
    one_col: str="1인가구수",
    base_cols: list[str]|None=None,
    quality_exclude: list[pd.Timestamp]|None=None,
    z_thr: float=1.96,
    delta_abs_q: float=0.85,
    n_perm: int=30,
    random_state: int=42,
    max_cohorts: int|None=None,
) -> pd.DataFrame:
    """메인 리포트 생성 (데이터프레임 반환)"""
    if unit_cols is None:
        unit_cols = ["자치구","행정동","성별","연령대"]
    if base_cols is None:
        base_cols = [
            "평일 총 이동 거리 합계",
            "지하철이동일수 합계",
            "배달 서비스 사용일수",
            "동영상/방송 서비스 사용일수",
            "평균 통화량",
            "집 추정 위치 평일 총 체류시간",
        ]
    if quality_exclude is None:
        quality_exclude = [pd.Timestamp("2024-06-01"), pd.Timestamp("2024-08-01"), pd.Timestamp("2024-09-01")]

    df = ensure_year_month(df, month_col)
    df = df[~df[month_col].isin(quality_exclude)].copy()

    # unit key 축소(결측 제거)
    unit_cols = [c for c in unit_cols if c in df.columns]

    # per-capita
    if one_col not in df.columns:
        raise ValueError(f"[delta_accuracy_report] '{one_col}' 컬럼이 필요합니다.")
    df = make_per_capita(df, [c for c in base_cols if c in df.columns], one_col)

    # 월내 robust Z
    pc_cols = [c+"_pc" for c in base_cols if c in df.columns]
    df = monthwise_robust_z_log1p(df, pc_cols, month_col)
    std_cols = [c+"_pc_std" for c in base_cols if c in df.columns]

    # Δ3개월 → 유의성/크기 플래그
    df = compute_delta3m(df, unit_cols, month_col, std_cols)
    df = add_z_and_flags(df, month_col, unit_cols, std_cols, z_thr=z_thr, delta_abs_q=delta_abs_q)

    # 요약
    rows=[]
    for c in std_cols:
        sub = df[~df[c+"_delta3m"].isna()]
        rows.append([
            c, len(sub),
            sub[c+"_flag"].mean(),
            sub[c+"_sig_ok"].mean(),
            sub[c+"_size_ok"].mean(),
            sub[c+"_z"].abs().median()
        ])
    base_summary = pd.DataFrame(rows, columns=["metric","n_obs","flag_rate","sig_rate","size_rate","|z|_median"])

    # 지속성
    hit_tbl = sustained_hits(df, unit_cols, month_col, std_cols)

    # Placebo
    placebo = placebo_flag_rate(df[[*unit_cols, month_col, *std_cols]].copy(), unit_cols, month_col, std_cols,
                                n_perm=n_perm, seed=random_state, max_cohorts=max_cohorts)

    rep = (base_summary.merge(hit_tbl, on="metric", how="left")
                      .merge(placebo, left_on="metric", right_index=True, how="left")) \
            .sort_values("flag_rate", ascending=False)

    return rep

# ===================== CLI =====================
def _build_argparser():
    ap = argparse.ArgumentParser(description="Cohort Δ3개월 정확도 리포트 (EDA)")
    ap.add_argument("--csv_path", default="telecom_group_monthly_all.csv")
    ap.add_argument("--month_col", default="year_month")
    ap.add_argument("--unit_cols", default="자치구,행정동,성별,연령대")
    ap.add_argument("--one_col", default="1인가구수")
    ap.add_argument("--exclude_months", default="2024-06,2024-08,2024-09")
    ap.add_argument("--z_thr", type=float, default=1.96)
    ap.add_argument("--delta_abs_q", type=float, default=0.85)
    ap.add_argument("--n_perm", type=int, default=30)
    ap.add_argument("--max_cohorts", type=int, default=None)
    ap.add_argument("--out_csv", default=None, help="요약 CSV 저장 경로")
    return ap

def main():
    args = _build_argparser().parse_args()
    df = pd.read_csv(args.csv_path)
    unit_cols = [c for c in args.unit_cols.split(",") if c]
    exclude = []
    if args.exclude_months:
        exclude = [pd.to_datetime(m).to_period("M").to_timestamp() for m in args.exclude_months.split(",")]
    rep = delta_accuracy_report(
        df,
        csv_path=args.csv_path,
        month_col=args.month_col,
        unit_cols=unit_cols,
        one_col=args.one_col,
        quality_exclude=exclude,
        z_thr=args.z_thr,
        delta_abs_q=args.delta_abs_q,
        n_perm=args.n_perm,
        max_cohorts=args.max_cohorts,
    )
    pd.set_option("display.float_format", lambda x: f"{x:,.3f}")
    print("\n[정확도 요약 테이블]")
    print(rep)
    if args.out_csv:
        rep.to_csv(args.out_csv, index=False, encoding="utf-8-sig")
        print(f"\n✅ 저장: {args.out_csv}")

if __name__ == "__main__":
    main()

