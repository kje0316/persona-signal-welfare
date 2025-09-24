"""
향상된 클러스터링 엔진 - RDS 연동 버전
기존 clustering.py 기능을 확장하여 RDS와 연동
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from sklearn.decomposition import PCA
import warnings

from ..common.database import db_manager

# 기존 clustering 모듈에서 함수 import
try:
    from .clustering import k_sweep_score, soft_membership_from_dist
    from .eda import ensure_year_month, make_per_capita, monthwise_robust_z_log1p
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"기존 clustering 모듈 import 실패: {e}, 자체 구현 사용")

    # 기본 구현
    def k_sweep_score(X: np.ndarray, K_list: List[int]) -> pd.DataFrame:
        rows = []
        for k in K_list:
            if k <= 1 or k >= len(X):
                continue
            km = KMeans(n_clusters=k, n_init="auto", random_state=42)
            lab = km.fit_predict(X)
            counts = np.bincount(lab, minlength=k)
            min_ratio = counts.min() / counts.sum()
            sil = silhouette_score(X, lab)
            ch = calinski_harabasz_score(X, lab)
            db = davies_bouldin_score(X, lab)
            rows.append([k, sil, ch, db, float(min_ratio)])
        return pd.DataFrame(rows, columns=["K", "silhouette", "calinski_harabasz", "davies_bouldin", "min_ratio"]).sort_values("silhouette", ascending=False)

    def soft_membership_from_dist(dists: np.ndarray, temperature: float = 1.0) -> np.ndarray:
        logits = -dists / max(1e-8, temperature)
        logits -= logits.max(axis=1, keepdims=True)
        probs = np.exp(logits)
        probs /= probs.sum(axis=1, keepdims=True)
        return probs

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


class EnhancedClusteringEngine:
    """RDS 연동 클러스터링 엔진"""

    def __init__(self):
        self.scaler = None
        self.clustering_model = None
        self.feature_columns = []
        self.clustering_results = {}

    def perform_clustering(
        self,
        task_id: str,
        table_name: str,
        dataset_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """RDS에서 데이터를 로드하여 클러스터링 수행"""
        try:
            logger.info(f"클러스터링 시작: {task_id}, 테이블: {table_name}")

            # 1. RDS에서 데이터 로드
            df = db_manager.load_dataframe_from_table(table_name)
            if df.empty:
                raise Exception("데이터를 로드할 수 없습니다")

            logger.info(f"데이터 로드 완료: {df.shape}")

            # 2. 클러스터링용 특성 선택 및 전처리
            features_df, feature_info = self._prepare_features(df, dataset_metadata)

            if features_df.empty:
                raise Exception("클러스터링에 사용할 수치형 특성이 없습니다")

            # 3. 최적 클러스터 수 찾기
            optimal_k, cluster_scores = self._find_optimal_clusters(features_df)

            # 4. 최종 클러스터링 수행
            cluster_labels, cluster_centers = self._perform_final_clustering(
                features_df, optimal_k
            )

            # 5. 클러스터별 특성 분석
            cluster_analysis = self._analyze_clusters(
                df, features_df, cluster_labels, feature_info
            )

            # 6. 차원 축소 (시각화용)
            reduced_features = self._perform_dimensionality_reduction(features_df)

            # 7. 클러스터 정보를 원본 데이터에 추가하여 저장
            self._save_clustered_data(task_id, df, cluster_labels, table_name)

            # 결과 구성
            clustering_results = {
                "task_id": task_id,
                "table_name": table_name,
                "optimal_k": optimal_k,
                "cluster_labels": cluster_labels.tolist(),
                "cluster_centers": cluster_centers.tolist(),
                "cluster_scores": cluster_scores.to_dict(),
                "cluster_analysis": cluster_analysis,
                "feature_info": feature_info,
                "reduced_features": reduced_features.tolist() if reduced_features is not None else None,
                "total_samples": len(df)
            }

            self.clustering_results = clustering_results
            logger.info(f"클러스터링 완료: {optimal_k}개 클러스터")
            return clustering_results

        except Exception as e:
            logger.error(f"클러스터링 실패: {e}")
            raise

    def _prepare_features(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> tuple:
        """클러스터링용 특성 준비"""
        try:
            # 메타데이터에서 수치형 컬럼 정보 가져오기
            numeric_info = metadata.get("numeric_info", {})
            numeric_columns = list(numeric_info.keys())

            if not numeric_columns:
                # 메타데이터가 없으면 직접 탐지
                numeric_columns = []
                for col in df.columns:
                    if pd.api.types.is_numeric_dtype(df[col]) and df[col].var() > 0:
                        numeric_columns.append(col)

            if not numeric_columns:
                return pd.DataFrame(), {}

            features_df = df[numeric_columns].copy()

            # 결측치 처리
            initial_rows = len(features_df)
            features_df = features_df.dropna()
            dropped_rows = initial_rows - len(features_df)

            if dropped_rows > 0:
                logger.info(f"결측치 제거: {dropped_rows}개 행 제거")

            # 극단값 제거 (IQR 방법)
            features_df = self._remove_outliers(features_df)

            # 스케일링
            self.scaler = RobustScaler()
            features_scaled = self.scaler.fit_transform(features_df)
            features_df_scaled = pd.DataFrame(
                features_scaled,
                columns=features_df.columns,
                index=features_df.index
            )

            self.feature_columns = numeric_columns

            feature_info = {
                "selected_features": numeric_columns,
                "feature_count": len(numeric_columns),
                "samples_after_cleaning": len(features_df_scaled),
                "outliers_removed": initial_rows - dropped_rows - len(features_df_scaled),
                "scaler_type": "RobustScaler"
            }

            logger.info(f"특성 준비 완료: {len(numeric_columns)}개 특성, {len(features_df_scaled)}개 샘플")
            return features_df_scaled, feature_info

        except Exception as e:
            logger.error(f"특성 준비 실패: {e}")
            return pd.DataFrame(), {}

    def _remove_outliers(self, df: pd.DataFrame, factor: float = 1.5) -> pd.DataFrame:
        """IQR을 사용한 극단값 제거"""
        try:
            clean_df = df.copy()
            initial_rows = len(clean_df)

            for col in df.columns:
                Q1 = clean_df[col].quantile(0.25)
                Q3 = clean_df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - factor * IQR
                upper_bound = Q3 + factor * IQR

                clean_df = clean_df[
                    (clean_df[col] >= lower_bound) & (clean_df[col] <= upper_bound)
                ]

            removed_rows = initial_rows - len(clean_df)
            if removed_rows > 0:
                logger.info(f"극단값 제거: {removed_rows}개 행 제거")

            return clean_df

        except Exception as e:
            logger.warning(f"극단값 제거 실패: {e}")
            return df

    def _find_optimal_clusters(self, features_df: pd.DataFrame) -> tuple:
        """최적 클러스터 수 찾기"""
        try:
            min_k = max(2, 2)
            max_k = min(min(len(features_df) // 10, 10), 10)

            if max_k <= min_k:
                max_k = min_k + 1

            k_range = list(range(min_k, max_k + 1))

            # k_sweep_score 함수 사용
            scores_df = k_sweep_score(features_df.values, k_range)

            if scores_df.empty:
                optimal_k = 3
                scores = {"k_values": [3], "silhouette_scores": [0]}
            else:
                # 최적 K는 실루엣 점수가 가장 높은 것
                optimal_k = int(scores_df.iloc[0]["K"])
                scores = scores_df

            logger.info(f"최적 클러스터 수: {optimal_k}")
            return optimal_k, scores

        except Exception as e:
            logger.error(f"최적 클러스터 수 찾기 실패: {e}")
            return 3, pd.DataFrame()

    def _perform_final_clustering(self, features_df: pd.DataFrame, k: int) -> tuple:
        """최종 클러스터링 수행"""
        try:
            self.clustering_model = KMeans(n_clusters=k, random_state=42, n_init=10)
            cluster_labels = self.clustering_model.fit_predict(features_df)
            cluster_centers = self.clustering_model.cluster_centers_

            logger.info(f"최종 클러스터링 완료: {k}개 클러스터")
            return cluster_labels, cluster_centers

        except Exception as e:
            logger.error(f"최종 클러스터링 실패: {e}")
            # 기본 클러스터 라벨 생성
            default_labels = np.zeros(len(features_df), dtype=int)
            default_centers = np.zeros((1, features_df.shape[1]))
            return default_labels, default_centers

    def _analyze_clusters(
        self,
        original_df: pd.DataFrame,
        features_df: pd.DataFrame,
        cluster_labels: np.ndarray,
        feature_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """클러스터별 특성 분석"""
        try:
            analysis = {}
            unique_clusters = np.unique(cluster_labels)

            for cluster_id in unique_clusters:
                cluster_mask = cluster_labels == cluster_id
                cluster_data = features_df[cluster_mask]
                cluster_original = original_df.iloc[features_df.index[cluster_mask]]

                # 기본 통계
                cluster_size = cluster_mask.sum()
                cluster_percentage = cluster_size / len(cluster_labels) * 100

                # 특성별 통계 (정규화된 값)
                feature_stats = {}
                for col in features_df.columns:
                    stats = {
                        "mean": float(cluster_data[col].mean()),
                        "std": float(cluster_data[col].std()),
                        "min": float(cluster_data[col].min()),
                        "max": float(cluster_data[col].max()),
                        "median": float(cluster_data[col].median())
                    }
                    feature_stats[col] = stats

                # 원본 데이터 기준 통계 (해석하기 쉬운 값)
                original_stats = {}
                for col in feature_info["selected_features"]:
                    if col in cluster_original.columns:
                        original_col_data = cluster_original[col]
                        if len(original_col_data) > 0:
                            original_stats[col] = {
                                "mean": float(original_col_data.mean()),
                                "std": float(original_col_data.std()),
                                "min": float(original_col_data.min()),
                                "max": float(original_col_data.max()),
                                "median": float(original_col_data.median())
                            }

                # 클러스터 중심과의 거리 기준 주요 특성 찾기
                if hasattr(self.clustering_model, 'cluster_centers_'):
                    center = self.clustering_model.cluster_centers_[cluster_id]
                    feature_importance = np.abs(center)
                    top_features_idx = np.argsort(feature_importance)[-5:]  # 상위 5개
                    top_features = [features_df.columns[idx] for idx in top_features_idx]
                else:
                    top_features = list(features_df.columns[:5])

                analysis[f"cluster_{cluster_id}"] = {
                    "cluster_id": int(cluster_id),
                    "size": int(cluster_size),
                    "percentage": float(cluster_percentage),
                    "feature_stats_normalized": feature_stats,
                    "feature_stats_original": original_stats,
                    "top_distinguishing_features": top_features
                }

            logger.info(f"클러스터 분석 완료: {len(unique_clusters)}개 클러스터")
            return analysis

        except Exception as e:
            logger.error(f"클러스터 분석 실패: {e}")
            return {}

    def _perform_dimensionality_reduction(self, features_df: pd.DataFrame) -> Optional[np.ndarray]:
        """PCA를 사용한 차원 축소 (시각화용)"""
        try:
            if features_df.shape[1] <= 2:
                return features_df.values

            pca = PCA(n_components=2, random_state=42)
            reduced_features = pca.fit_transform(features_df)

            explained_variance_ratio = pca.explained_variance_ratio_
            logger.info(f"PCA 완료: 설명 분산 비율 = {explained_variance_ratio}")

            return reduced_features

        except Exception as e:
            logger.warning(f"차원 축소 실패: {e}")
            return None

    def _save_clustered_data(
        self,
        task_id: str,
        original_df: pd.DataFrame,
        cluster_labels: np.ndarray,
        original_table_name: str
    ):
        """클러스터 정보가 추가된 데이터 저장"""
        try:
            # 클러스터 정보 추가
            clustered_df = original_df.copy()

            # 클러스터 라벨을 원본 데이터프레임과 매칭
            if len(cluster_labels) == len(clustered_df):
                clustered_df['cluster_id'] = cluster_labels
            else:
                # 클러스터링에서 일부 행이 제거된 경우
                clustered_df['cluster_id'] = -1  # 기본값
                # 실제 클러스터링에 사용된 인덱스에만 라벨 할당
                if hasattr(self, 'feature_columns') and len(self.feature_columns) > 0:
                    valid_df = clustered_df[self.feature_columns].dropna()
                    if len(cluster_labels) == len(valid_df):
                        clustered_df.loc[valid_df.index, 'cluster_id'] = cluster_labels

            # 새 테이블로 저장
            clustered_table_name = f"{original_table_name}_clustered"
            success = db_manager.save_dataframe_to_table(clustered_df, clustered_table_name)

            if success:
                logger.info(f"클러스터링된 데이터 저장: {clustered_table_name}")
            else:
                logger.warning("클러스터링된 데이터 저장 실패")

        except Exception as e:
            logger.error(f"클러스터링된 데이터 저장 실패: {e}")

    def get_cluster_centers(self) -> np.ndarray:
        """클러스터 중심 반환"""
        if self.clustering_model:
            return self.clustering_model.cluster_centers_
        return np.array([])

    def predict_cluster(self, new_data: pd.DataFrame) -> np.ndarray:
        """새로운 데이터의 클러스터 예측"""
        try:
            if self.clustering_model is None or self.scaler is None:
                raise Exception("학습된 모델이 없습니다")

            # 동일한 전처리 적용
            features = new_data[self.feature_columns]
            features_scaled = self.scaler.transform(features)

            # 클러스터 예측
            cluster_labels = self.clustering_model.predict(features_scaled)

            return cluster_labels

        except Exception as e:
            logger.error(f"클러스터 예측 실패: {e}")
            return np.array([])


# 편의를 위한 함수
def perform_enhanced_clustering(
    task_id: str,
    table_name: str,
    dataset_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """향상된 클러스터링 수행 (함수형 인터페이스)"""
    engine = EnhancedClusteringEngine()
    return engine.perform_clustering(task_id, table_name, dataset_metadata)