# persona_soft.py (robust++)
import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# 컬럼명 정규화 유틸
def _normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return name
    s = name
    if s.endswith("_pc_std"):
        return s[:-7] + "_std"
    if s.endswith("_pc"):
        return s[:-3] + "_std"
    return s

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={c: _normalize_name(c) for c in df.columns})

# 기대 피처(정규화 기준명) — 실제 사용은 교집합
CLUST_FEATS = [
    "평일 총 이동 거리 합계_std",
    "휴일 총 이동 거리 합계_std",
    "동영상/방송 서비스 사용일수_std",
    "지하철이동일수 합계_std",
    "집 추정 위치 평일 총 체류시간_std",
    "평균 통화대상자 수_std",
    "평균 문자량_std",
    "배달 서비스 사용일수_std",
]
CLUST_FEATS_CANON = CLUST_FEATS

# ─────────────────────────────────────────────────────────────────────────────
# 센터 로더: *_std만, 숫자형 강제, 최소 4개 보장
def load_centers(path: str = "cluster_centers.csv") -> pd.DataFrame:
    C = pd.read_csv(path, index_col=0)
    C = _normalize_columns(C)

    # *_std만 추림
    std_cols = [c for c in C.columns if isinstance(c, str) and c.endswith("_std")]
    if not std_cols:
        raise ValueError("centers has no *_std columns after normalization.")

    # 우선순위: 우리가 기대하는 컬럼 순서
    used = [c for c in CLUST_FEATS_CANON if c in C.columns]
    if len(used) < 4:
        # 백업: *_std를 알파벳(한글)순 상위 8개 정도
        fallback = sorted(std_cols)[:8]
        if len(fallback) < 4:
            raise ValueError(
                f"centers insufficient usable *_std columns (found {len(fallback)}). "
                "Please provide cluster centers with standardized feature columns."
            )
        used = fallback

    C = C[used].copy()

    # 숫자형 강제(문자/공백 등 방지)
    for c in C.columns:
        C[c] = pd.to_numeric(C[c], errors="coerce")
    return C

# ─────────────────────────────────────────────────────────────────────────────
# 소프트 멤버십 계산: centers 컬럼 순서 고정, 결측/비숫자 0 대체
def soft_membership(
    df: pd.DataFrame,
    centers: pd.DataFrame,
    temp: float = 1.0,
    impute_zero: bool = True,
) -> pd.DataFrame:
    # 입력 정규화
    df_norm = _normalize_columns(df)

    # 센터 기준으로 교집합 고정(순서는 센터 컬럼 순서)
    cols = [c for c in list(centers.columns) if c in df_norm.columns]
    if len(cols) < centers.shape[1]:
        # 누락 컬럼은 필요시 0 채움
        missing = [c for c in centers.columns if c not in cols]
        cols = list(centers.columns)  # 순서 그대로
        if missing and not impute_zero:
            raise ValueError(f"input df missing columns: {missing}")
        for m in missing:
            df_norm[m] = 0.0

    # 숫자형 강제 + NaN/inf 처리
    X = pd.DataFrame({c: pd.to_numeric(df_norm[c], errors="coerce") for c in cols})
    X = X[cols].to_numpy()
    if impute_zero:
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    C = centers[cols].to_numpy()
    # 거리 계산
    d2 = np.sum((X[:, None, :] - C[None, :, :]) ** 2, axis=2)

    # RBF-softmax (temp 하한 보장)
    t = max(float(temp), 1e-6)
    logits = -d2 / (2.0 * (t ** 2) + 1e-12)
    logits -= logits.max(axis=1, keepdims=True)
    P = np.exp(logits)
    P /= (P.sum(axis=1, keepdims=True) + 1e-12)

    out = pd.DataFrame(P, columns=[f"persona_p{k}" for k in range(P.shape[1])], index=df.index)
    out["persona_label"] = out.values.argmax(axis=1).astype(int)
    out["persona_conf"]  = out.max(axis=1)
    return out
# persona_soft.py (robust++)
import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# 컬럼명 정규화 유틸
def _normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return name
    s = name
    if s.endswith("_pc_std"):
        return s[:-7] + "_std"
    if s.endswith("_pc"):
        return s[:-3] + "_std"
    return s

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={c: _normalize_name(c) for c in df.columns})

# 기대 피처(정규화 기준명) — 실제 사용은 교집합
CLUST_FEATS = [
    "평일 총 이동 거리 합계_std",
    "휴일 총 이동 거리 합계_std",
    "동영상/방송 서비스 사용일수_std",
    "지하철이동일수 합계_std",
    "집 추정 위치 평일 총 체류시간_std",
    "평균 통화대상자 수_std",
    "평균 문자량_std",
    "배달 서비스 사용일수_std",
]
CLUST_FEATS_CANON = CLUST_FEATS

# ─────────────────────────────────────────────────────────────────────────────
# 센터 로더: *_std만, 숫자형 강제, 최소 4개 보장
def load_centers(path: str = "cluster_centers.csv") -> pd.DataFrame:
    C = pd.read_csv(path, index_col=0)
    C = _normalize_columns(C)

    # *_std만 추림
    std_cols = [c for c in C.columns if isinstance(c, str) and c.endswith("_std")]
    if not std_cols:
        raise ValueError("centers has no *_std columns after normalization.")

    # 우선순위: 우리가 기대하는 컬럼 순서
    used = [c for c in CLUST_FEATS_CANON if c in C.columns]
    if len(used) < 4:
        # 백업: *_std를 알파벳(한글)순 상위 8개 정도
        fallback = sorted(std_cols)[:8]
        if len(fallback) < 4:
            raise ValueError(
                f"centers insufficient usable *_std columns (found {len(fallback)}). "
                "Please provide cluster centers with standardized feature columns."
            )
        used = fallback

    C = C[used].copy()

    # 숫자형 강제(문자/공백 등 방지)
    for c in C.columns:
        C[c] = pd.to_numeric(C[c], errors="coerce")
    return C

# ─────────────────────────────────────────────────────────────────────────────
# 소프트 멤버십 계산: centers 컬럼 순서 고정, 결측/비숫자 0 대체
def soft_membership(
    df: pd.DataFrame,
    centers: pd.DataFrame,
    temp: float = 1.0,
    impute_zero: bool = True,
) -> pd.DataFrame:
    # 입력 정규화
    df_norm = _normalize_columns(df)

    # 센터 기준으로 교집합 고정(순서는 센터 컬럼 순서)
    cols = [c for c in list(centers.columns) if c in df_norm.columns]
    if len(cols) < centers.shape[1]:
        # 누락 컬럼은 필요시 0 채움
        missing = [c for c in centers.columns if c not in cols]
        cols = list(centers.columns)  # 순서 그대로
        if missing and not impute_zero:
            raise ValueError(f"input df missing columns: {missing}")
        for m in missing:
            df_norm[m] = 0.0

    # 숫자형 강제 + NaN/inf 처리
    X = pd.DataFrame({c: pd.to_numeric(df_norm[c], errors="coerce") for c in cols})
    X = X[cols].to_numpy()
    if impute_zero:
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    C = centers[cols].to_numpy()
    # 거리 계산
    d2 = np.sum((X[:, None, :] - C[None, :, :]) ** 2, axis=2)

    # RBF-softmax (temp 하한 보장)
    t = max(float(temp), 1e-6)
    logits = -d2 / (2.0 * (t ** 2) + 1e-12)
    logits -= logits.max(axis=1, keepdims=True)
    P = np.exp(logits)
    P /= (P.sum(axis=1, keepdims=True) + 1e-12)

    out = pd.DataFrame(P, columns=[f"persona_p{k}" for k in range(P.shape[1])], index=df.index)
    out["persona_label"] = out.values.argmax(axis=1).astype(int)
    out["persona_conf"]  = out.max(axis=1)
    return out


