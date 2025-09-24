# build_rag_aug.py
# 원천 CSV에서 RAG 증강 산출물을 생성합니다.
# 산출물:
#  - feature_stats.csv, feature_mapping.csv, month_coverage.csv,
#    per_month_numeric_std.csv, kb_chunks.jsonl, README.md, rag_aug.zip

import os, json, math, zipfile, textwrap, argparse
from datetime import datetime

import numpy as np
import pandas as pd

# 선택 의존성: PyYAML
try:
    import yaml  # type: ignore
    HAS_YAML = True
except Exception:
    HAS_YAML = False

def ensure_year_month(df: pd.DataFrame) -> pd.DataFrame:
    """year_month(datetime64) 보장."""
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
            year=pd.to_numeric(out["year"], errors="coerce").astype("Int64"),
            month=pd.to_numeric(out["month_num"], errors="coerce").astype("Int64"),
            day=1
        ))
        return out
    # 느슨 탐색
    for c in out.columns:
        if not isinstance(c, str): 
            continue
        low = c.lower()
        if ("year" in low and "month" in low) or ("yyyymm" in low) or ("date" in low):
            try:
                out["year_month"] = pd.to_datetime(out[c]).dt.to_period("M").dt.to_timestamp()
                return out
            except Exception:
                pass
    raise ValueError("year_month 생성 실패: 'year_month' 또는 (year, month_num) 또는 'month' 컬럼을 제공하세요.")

def robust_month_standardize(df: pd.DataFrame, month_col: str = "year_month"):
    """
    월별 강건 표준화: 모든 숫자형 컬럼에 대해 log1p 후 median/IQR 기반 z-score → <col>_std 생성.
    반환: out_df, mapping_rows
    """
    out = df.copy()
    mapping = []
    exclude = {month_col, "year", "month_num", "행정동코드", "자치구", "성별", "연령대"}
    # 숫자형만 선택
    num_cols = [c for c in out.columns if c not in exclude and pd.api.types.is_numeric_dtype(out[c])]

    for col in num_cols:
        std_col = f"{col}_std"
        if std_col in out.columns:
            mapping.append({"original": col, "std_col": std_col, "created": False, "reason": "exists"})
            continue
        x = np.log1p(pd.to_numeric(out[col], errors="coerce").clip(lower=0))
        g = x.groupby(out[month_col])
        med = g.transform("median")
        iqr = g.transform(lambda v: v.quantile(0.75) - v.quantile(0.25))
        scale = iqr.where(iqr > 0, g.transform("std")).fillna(1.0)
        out[std_col] = ((x - med) / scale.where(scale > 0, 1.0)).fillna(0.0)
        mapping.append({"original": col, "std_col": std_col, "created": True, "reason": "robust_month_std"})
    return out, mapping

def month_agg_deltas_trends(df: pd.DataFrame, base_std_cols, month_col="year_month"):
    """
    월평균 기반 파생:
      Δ3m  := mean(cur 3m) - mean(prev 3m)
      Trend:= mean(cur 6m) - mean(prev 6m)
    반환: out_df, derived_mapping_rows
    """
    out = df.copy()
    base_std_cols = [c for c in base_std_cols if c in out.columns]
    derived_map = []

    if not base_std_cols:
        return out, derived_map

    mdf = out.groupby([month_col], as_index=False)[base_std_cols].mean().sort_values(month_col)
    for c in base_std_cols:
        cur3 = mdf[c].rolling(3, min_periods=3).mean()
        prev3 = mdf[c].shift(3).rolling(3, min_periods=3).mean()
        mdf[c + "_delta3m"] = cur3 - prev3

        cur6 = mdf[c].rolling(6, min_periods=6).mean()
        prev6 = mdf[c].shift(6).rolling(6, min_periods=6).mean()
        mdf[c + "_trend12m"] = cur6 - prev6

        derived_map.append({"base_std": c, "derived": c + "_delta3m", "created": True, "grouping": "month_mean"})
        derived_map.append({"base_std": c, "derived": c + "_trend12m", "created": True, "grouping": "month_mean"})

    out = out.merge(
        mdf[[month_col] + [c + "_delta3m" for c in base_std_cols] + [c + "_trend12m" for c in base_std_cols]],
        on=month_col, how="left"
    )
    return out, derived_map

def infer_types(df: pd.DataFrame):
    info = []
    for c in df.columns:
        dt = str(df[c].dtype)
        if pd.api.types.is_numeric_dtype(df[c]):
            kind = "numeric"
        elif np.issubdtype(df[c].dtype, np.datetime64):
            kind = "datetime"
        else:
            kind = "categorical/text"
        info.append({
            "column": c,
            "dtype": dt,
            "inferred_kind": kind,
            "nunique": int(pd.Series(df[c]).nunique(dropna=True))
        })
    return pd.DataFrame(info)

def make_feature_stats(df: pd.DataFrame, month_col="year_month"):
    rows = []
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            s = pd.to_numeric(df[c], errors="coerce").astype(float)
            has = s.notna().any()
            rows.append({
                "column": c,
                "type": "numeric",
                "count": int(s.notna().sum()),
                "missing_rate": float(1 - s.notna().mean()),
                "mean": float(np.nanmean(s)) if has else math.nan,
                "std": float(np.nanstd(s)) if has else math.nan,
                "p01": float(np.nanpercentile(s.dropna(), 1)) if has else math.nan,
                "p50": float(np.nanpercentile(s.dropna(), 50)) if has else math.nan,
                "p99": float(np.nanpercentile(s.dropna(), 99)) if has else math.nan,
            })
        else:
            s = df[c]
            rows.append({
                "column": c,
                "type": "categorical/text",
                "count": int(s.notna().sum()),
                "missing_rate": float(1 - s.notna().mean()),
                "nunique": int(pd.Series(s).nunique(dropna=True))
            })

    # 월별 행 수
    month_counts = df.groupby(month_col, dropna=False).size().rename("rows").reset_index()

    # 숫자형 컬럼의 월별 표준편차
    per_month = []
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            pm = df.groupby(month_col, dropna=False)[c].std().rename("std").reset_index()
            pm["column"] = c
            per_month.append(pm)
    per_month_df = pd.concat(per_month, ignore_index=True) if per_month else pd.DataFrame(columns=[month_col, "std", "column"])
    return pd.DataFrame(rows), month_counts, per_month_df

def fuzzy_resolve(colname, df_cols):
    """규칙 신호명을 실제 컬럼과 느슨 매칭."""
    if colname in df_cols:
        return colname
    base = colname
    for suf in ["_pc_std", "_pc", "_std"]:
        if base.endswith(suf):
            base = base[: -len(suf)]
            break
    pool = [c for c in df_cols if isinstance(c, str) and base in c]
    if not pool:
        return None
    pool_std = [c for c in pool if c.endswith("_std")]
    pool = pool_std or pool
    pool = sorted(pool, key=lambda x: (0 if "평균" in x else 1, len(x)))
    return pool[0] if pool else None

def build_kb_chunks(df, dtype_df, feature_stats, month_counts, created_map, derived_map, rules_path=None):
    chunks = []
    now = datetime.now().isoformat()

    # 개요
    if len(df) > 0:
        period_min = str(df["year_month"].min().date())
        period_max = str(df["year_month"].max().date())
    else:
        period_min = period_max = "N/A"

    overview = {
        "doc_id": "dataset_overview",
        "chunk_id": "overview#1",
        "text": textwrap.dedent(f"""
        데이터셋 개요
        - 전체 행 수: {len(df):,}
        - 기간(최소~최대): {period_min} ~ {period_max}
        - 숫자형 컬럼 수: {int((dtype_df['inferred_kind']=='numeric').sum())}
        - 범주형/텍스트 컬럼 수: {int((dtype_df['inferred_kind']!='numeric').sum())}
        - 생성된 표준화 피처 수: {len([m for m in created_map if m.get('created')])}
        - 생성된 Δ/Trend 피처 수: {len(derived_map)}
        """).strip(),
        "meta": {"type":"overview","created_at":now}
    }
    chunks.append(overview)

    # 매핑
    mapping_lines = []
    for m in created_map:
        status = "신규" if m.get("created") else "기존"
        mapping_lines.append(f"- {m['original']} -> {m['std_col']} ({status})")
    for m in derived_map[:300]:
        mapping_lines.append(f"- {m['base_std']} -> {m['derived']} (Δ/Trend)")
    chunks.append({
        "doc_id": "feature_mapping",
        "chunk_id": "feature_mapping#1",
        "text": "표준화/파생 피처 매핑\n" + "\n".join(mapping_lines[:800]),
        "meta": {"type":"feature_mapping","created_at":now}
    })

    # 월 커버리지
    mc_lines = []
    for _, r in month_counts.iterrows():
        mc_lines.append(f"- {str(pd.to_datetime(r['year_month']).date())}: {int(r['rows']):,} rows")
    chunks.append({
        "doc_id":"month_coverage",
        "chunk_id":"month_coverage#1",
        "text":"월별 커버리지(행 수)\n" + "\n".join(mc_lines),
        "meta":{"type":"coverage","created_at":now}
    })

    # 규칙-신호 매핑 미리보기
    if rules_path and os.path.exists(rules_path) and HAS_YAML:
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                rules = yaml.safe_load(f)
            targets = (rules or {}).get("targets", {}) or {}
            lines = []
            for tgt, obj in targets.items():
                sigs = (obj or {}).get("signals", []) or []
                if not isinstance(sigs, list): 
                    continue
                for sig in sigs:
                    req = (sig or {}).get("col")
                    if not req: 
                        continue
                    resolved = fuzzy_resolve(req, df.columns)
                    lines.append(f"- {tgt} : '{req}' → {resolved or '매칭 실패'}")
            chunks.append({
                "doc_id":"rule_signal_resolution",
                "chunk_id":"rule_signal_resolution#1",
                "text":"규칙 신호-컬럼 매핑 미리보기\n" + "\n".join(lines[:500]),
                "meta":{"type":"rules_map","created_at":now}
            })
        except Exception as e:
            chunks.append({
                "doc_id":"rule_signal_resolution",
                "chunk_id":"rule_signal_resolution#error",
                "text":f"rules.yml 파싱 중 오류: {repr(e)}",
                "meta":{"type":"rules_map","created_at":now}
            })
    return chunks

def build_rag_augmentation(csv_path: str, out_dir: str, rules_path: str=None, month_col: str="year_month", encoding: str="utf-8"):
    os.makedirs(out_dir, exist_ok=True)

    # 1) Load & ensure year_month
    df = pd.read_csv(csv_path, encoding=encoding, low_memory=False)
    df = ensure_year_month(df)
    if month_col != "year_month":
        df = df.rename(columns={month_col: "year_month"})

    # 2) 타입/기초 메타
    dtype_df = infer_types(df)

    # 3) *_std 생성
    df_std, created_map = robust_month_standardize(df, month_col="year_month")

    # 4) Δ/Trend 파생
    base_std_cols = [c for c in df_std.columns if c.endswith("_std")]
    df_aug, derived_map = month_agg_deltas_trends(df_std, base_std_cols, month_col="year_month")

    # 5) 통계/커버리지
    feature_stats_df, month_counts_df, per_month_std_df = make_feature_stats(df_aug, month_col="year_month")

    # 6) 저장
    feature_stats_path = os.path.join(out_dir, "feature_stats.csv")
    feature_stats_df.to_csv(feature_stats_path, index=False, encoding="utf-8-sig")

    mapping_df = pd.DataFrame(created_map)
    mapping_df2 = pd.DataFrame(derived_map)
    mapping_df["type"] = "std"
    mapping_df2["type"] = "derived"
    feature_mapping_path = os.path.join(out_dir, "feature_mapping.csv")
    pd.concat([mapping_df, mapping_df2], ignore_index=True).to_csv(feature_mapping_path, index=False, encoding="utf-8-sig")

    month_cov_path = os.path.join(out_dir, "month_coverage.csv")
    month_counts_df.to_csv(month_cov_path, index=False, encoding="utf-8-sig")

    per_month_std_path = os.path.join(out_dir, "per_month_numeric_std.csv")
    per_month_std_df.to_csv(per_month_std_path, index=False, encoding="utf-8-sig")

    # 7) KB 청크
    kb_chunks = build_kb_chunks(df_aug, dtype_df, feature_stats_df, month_counts_df, created_map, derived_map, rules_path=rules_path)
    kb_path = os.path.join(out_dir, "kb_chunks.jsonl")
    with open(kb_path, "w", encoding="utf-8") as f:
        for ch in kb_chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")

    # 8) README
    readme_path = os.path.join(out_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(f"""
        # RAG 증강 산출물
        생성 시각: {datetime.now().isoformat()}

        ## 산출물
        - feature_stats.csv : 컬럼별 기본 통계(결측률, 평균/표준편차/백분위)
        - feature_mapping.csv : 원본→표준화(*_std), 표준화→파생(delta3m/trend12m) 매핑
        - month_coverage.csv : 월별 행 수
        - per_month_numeric_std.csv : 숫자형 컬럼의 월별 표준편차
        - kb_chunks.jsonl : 벡터 인덱싱용 JSONL 청크(개요/매핑/월커버리지)
        - README.md : 사용 가이드

        ## 인덱싱 가이드
        - kb_chunks.jsonl 를 벡터 인덱스에 임베딩하세요.
        - 표 파일(CSV)들은 RAG 응답 단계에서 수치 근거로 함께 로드하세요.

        ## 옵션: 규칙 파일(rules.yml)
        - --rules_path 를 넘기면 규칙 신호명 ↔ 실제 컬럼 매핑 미리보기 청크가 추가됩니다.
        """).strip())

    # 9) Zip
    zip_path = os.path.join(out_dir, "rag_aug.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn in ["feature_stats.csv", "feature_mapping.csv", "month_coverage.csv",
                   "per_month_numeric_std.csv", "kb_chunks.jsonl", "README.md"]:
            zf.write(os.path.join(out_dir, fn), arcname=fn)

    # 요약 리턴(콘솔 출력용)
    return {
        "out_dir": out_dir,
        "files": {
            "feature_stats": feature_stats_path,
            "feature_mapping": feature_mapping_path,
            "month_coverage": month_cov_path,
            "per_month_numeric_std": per_month_std_path,
            "kb_chunks": kb_path,
            "readme": readme_path,
            "zip": zip_path
        },
        "n_rows": len(df_aug),
        "n_cols": len(df_aug.columns),
        "n_std_created": int(sum(1 for m in created_map if m.get("created"))),
        "n_derived": len(derived_map)
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv_path", required=True, help="원천 CSV 경로")
    ap.add_argument("--out_dir", default="/mnt/data/rag_aug", help="출력 폴더 (기본: /mnt/data/rag_aug)")
    ap.add_argument("--rules_path", default=None, help="선택: rules.yml 경로 (있으면 규칙-신호 매핑 미리보기 추가)")
    ap.add_argument("--month_col", default="year_month", help="월 컬럼명(없으면 자동 생성)")
    ap.add_argument("--encoding", default="utf-8", help="입력 CSV 인코딩 (예: utf-8, cp949, euc-kr)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    res = build_rag_augmentation(
        csv_path=args.csv_path,
        out_dir=args.out_dir,
        rules_path=args.rules_path,
        month_col=args.month_col,
        encoding=args.encoding
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
