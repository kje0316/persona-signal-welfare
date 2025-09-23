# -*- coding: utf-8 -*-
"""
eda.py — 1인가구 통합 생활데이터 EDA/시각화 러너

기능
- 안전한 year_month 생성 (month | year+month_num)
- 대표수치 선택(4분위수 50%만 유지)
- per-capita 파생(1인가구수 기준)
- 품질 모니터링(미추정 합계 z-flag, PSI/KS 드리프트 표)
- 요약 그래프(트렌드/상관/박스) 옵션 출력
"""

from __future__ import annotations

import os
from typing import List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager, rcParams

from preprocess import (
    ensure_year_month,
    pick_median_quartile_columns,
    make_per_capita,
    drift_table,
    quality_miss_flags,
)

# ---------------------------------------------------------------------
# 한글 폰트 설정 (mac 기본 폰트만 명시해서 경고 방지)
# ---------------------------------------------------------------------
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
    # fallback
    rcParams["font.family"] = "DejaVu Sans"
    rcParams["axes.unicode_minus"] = False

use_korean_font()

plt.rcParams["axes.unicode_minus"] = False
pd.set_option("display.max_columns", 200)

# ---------------------------------------------------------------------
# 시각화 유틸
# ---------------------------------------------------------------------
def plot_monthly_trend(df_month: pd.DataFrame, cols: List[str], title: str):
    if not cols:
        return
    long_df = df_month.melt(
        id_vars="year_month", value_vars=cols,
        var_name="metric", value_name="value"
    )
    plt.figure(figsize=(12, 5))
    sns.lineplot(data=long_df, x="year_month", y="value", hue="metric")
    plt.title(title)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def plot_corr_heatmap(df: pd.DataFrame, cols: List[str], title: str = "상관관계(대표)"):
    corr = df[cols].corr(numeric_only=True)
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr, cmap="coolwarm", center=0, annot=False)
    plt.title(title)
    plt.tight_layout()
    plt.show()


def plot_monthly_box(df: pd.DataFrame, col: str, month_col: str = "year_month"):
    plt.figure(figsize=(12, 4))
    sns.boxplot(data=df, x=month_col, y=col, showfliers=False)
    plt.title(f"월별 분포: {col}")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EDA runner")
    parser.add_argument("--csv", default="telecom_group_monthly_all.csv")
    parser.add_argument("--plot", action="store_true", help="대표 그래프 출력")
    args = parser.parse_args()

    # 데이터 로드 & 기본 전처리
    df = pd.read_csv(args.csv)
    df = ensure_year_month(df)
    print("year_month:", df["year_month"].min(), "→", df["year_month"].max())

    # 대표 컬럼/파생
    num_cols_all = df.select_dtypes(include=[np.number]).columns.tolist()
    num_cols_rep = pick_median_quartile_columns(num_cols_all)
    df = make_per_capita(df, num_cols_rep, one_col="1인가구수")

    # 품질/드리프트 리포트
    qtbl = quality_miss_flags(df)
    if not qtbl.empty:
        print("\n[품질 플래그 최근 24개월]")
        print(qtbl.sort_index().tail(24))

    pc_cols = [c for c in df.columns if c.endswith("_pc")]
    if pc_cols:
        cols_for_psi = pc_cols[:20] if len(pc_cols) > 20 else pc_cols
        _, psi_rank = drift_table(df, cols_for_psi, by="year_month", topn=10)
        if not psi_rank.empty:
            print("\n[월별 드리프트 TOP(PSI)]")
            print(psi_rank.head(20))

    # 옵션: 그래프
    if args.plot:
        rep = [
            c for c in [
                "평일 총 이동 거리 합계_pc",
                "배달 서비스 사용일수_pc",
                "동영상/방송 서비스 사용일수_pc",
                "평균 통화대상자 수_pc",
            ]
            if c in df.columns
        ]
        monthly_mean = df.groupby("year_month")[rep].mean().reset_index()
        plot_monthly_trend(monthly_mean, rep, "월별 지표 트렌드(mean)")
        plot_corr_heatmap(df, (pc_cols or num_cols_rep)[:30])
        for c in rep[:4]:
            plot_monthly_box(df, c)
