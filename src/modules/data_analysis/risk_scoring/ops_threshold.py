# ops_threshold.py
# -*- coding: utf-8 -*-
"""
Find score threshold that meets a target recall on a calibration/validation CSV.

Usage (repo root = AI_HACK):
  # 1) repo 루트에서
  PYTHONPATH=persona-signal-welfare/src \
  python -m project.ops_threshold \
      --csv persona-signal-welfare/src/modules/data_analysis/notebooks/project/artifacts_future/preds_cal.csv \
      --target-recall 0.65 \
      --out-json persona-signal-welfare/src/modules/data_analysis/notebooks/project/artifacts_future/threshold.json

  # 2) notebooks 폴더에서 (현재 스크린샷처럼)
  PYTHONPATH=../.. \
  python -m project.ops_threshold \
      --csv ../modules/data_analysis/notebooks/project/artifacts_future/preds_cal.csv \
      --target-recall 0.65 \
      --out-json ../modules/data_analysis/notebooks/project/artifacts_future/threshold.json
"""
from __future__ import annotations
import argparse, json, os
from typing import Tuple, Dict, Any, List, Optional
import numpy as np
import pandas as pd

Y_COL_CANDIDATES = ["y_true", "label", "y", "target", "gt", "truth"]
SCORE_COL_CANDIDATES = ["score", "proba", "prob", "pred_score", "y_pred_proba", "p", "prediction"]

def _guess_col(df: pd.DataFrame, candidates: List[str]) -> str:
    low = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in low: return low[c]
    for col in df.columns:
        if any(c in col.lower() for c in candidates): return col
    raise ValueError(f"Can't find any of columns: {candidates} in {list(df.columns)}")

def load_xy(csv_path: str, y_col: Optional[str] = None, score_col: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(csv_path)
    y_col = y_col or _guess_col(df, Y_COL_CANDIDATES)
    score_col = score_col or _guess_col(df, SCORE_COL_CANDIDATES)
    y = df[y_col].values
    s = df[score_col].values
    if y.dtype == bool: y = y.astype(int)
    mask = np.isfinite(s) & np.isfinite(y)
    y = y[mask].astype(int)
    s = s[mask].astype(float)
    if (y == 1).sum() == 0: raise ValueError("No positive samples in CSV.")
    if (y == 0).sum() == 0: raise ValueError("No negative samples in CSV.")
    return y, s

def metrics_at_threshold(y: np.ndarray, s: np.ndarray, thr: float) -> Dict[str, Any]:
    pred = (s >= thr).astype(int)
    tp = int(((y == 1) & (pred == 1)).sum())
    fp = int(((y == 0) & (pred == 1)).sum())
    fn = int(((y == 1) & (pred == 0)).sum())
    tn = int(((y == 0) & (pred == 0)).sum())
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1   = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
    return {"threshold": float(thr), "precision": float(prec), "recall": float(rec),
            "f1": float(f1), "tp": tp, "fp": fp, "fn": fn, "tn": tn}

def threshold_for_target_recall(y: np.ndarray, s: np.ndarray, target_recall: float) -> Dict[str, Any]:
    target_recall = float(np.clip(target_recall, 0.0, 1.0))
    order = np.argsort(-s)  # high -> low
    y_sorted = y[order]; s_sorted = s[order]
    cum_tp = np.cumsum(y_sorted == 1)
    total_pos = int((y_sorted == 1).sum())
    best = None; seen = set()
    for i in range(len(s_sorted)):
        sc = float(s_sorted[i])
        if sc in seen: continue
        seen.add(sc)
        rec = int(cum_tp[i]) / total_pos if total_pos > 0 else 0.0
        if rec >= target_recall:
            m = metrics_at_threshold(y, s, sc)
            if best is None or sc > best["threshold"]: best = m
    if best is None:
        sc = float(np.min(s_sorted))
        best = metrics_at_threshold(y, s, sc)
    return best

def main():
    ap = argparse.ArgumentParser(description="Find threshold for target recall.")
    ap.add_argument("--csv", required=True, help="Calibration/validation CSV with y and score columns.")
    ap.add_argument("--target-recall", type=float, required=True, help="e.g., 0.65 for 65% recall.")
    ap.add_argument("--y-col", default=None, help="Optional ground-truth column name.")
    ap.add_argument("--score-col", default=None, help="Optional score/proba column name.")
    ap.add_argument("--out-json", default=None, help="Optional path to save result JSON.")
    args = ap.parse_args()

    y, s = load_xy(args.csv, y_col=args.y_col, score_col=args.score_col)
    res = threshold_for_target_recall(y, s, args.target_recall)
    res.update({
        "n_samples": int(len(y)),
        "n_pos": int((y == 1).sum()),
        "n_neg": int((y == 0).sum()),
        "csv": os.path.abspath(args.csv),
        "target_recall": float(args.target_recall),
        "y_col": args.y_col,
        "score_col": args.score_col,
    })

    print("[RESULT]")
    print(json.dumps(res, ensure_ascii=False, indent=2))

    if args.out_json:
        os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()


