"""
데이터 증강 성능 평가기
원본 데이터와 증강된 데이터의 품질 비교 및 성능 지표 계산
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, roc_auc_score,
    mean_squared_error, r2_score,
    classification_report, confusion_matrix
)
from sklearn.preprocessing import StandardScaler
from scipy import stats

logger = logging.getLogger(__name__)


class AugmentationEvaluator:
    """데이터 증강 품질 평가 엔진"""

    def __init__(self):
        self.evaluation_results = {}
        self.comparison_plots = {}

    def evaluate_augmentation_quality(
        self,
        original_data: pd.DataFrame,
        augmented_data: pd.DataFrame,
        target_columns: List[str] = None,
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """원본 데이터와 증강 데이터의 전체적인 품질 평가"""
        try:
            logger.info("데이터 증강 품질 평가 시작")

            evaluation_results = {
                "evaluation_timestamp": datetime.now().isoformat(),
                "data_info": {
                    "original_samples": len(original_data),
                    "augmented_samples": len(augmented_data),
                    "augmentation_ratio": len(augmented_data) / len(original_data)
                },
                "statistical_comparison": {},
                "distribution_analysis": {},
                "model_performance": {},
                "quality_metrics": {}
            }

            # 1. 기본 통계 비교
            evaluation_results["statistical_comparison"] = self._compare_basic_statistics(
                original_data, augmented_data
            )

            # 2. 분포 유사성 분석
            evaluation_results["distribution_analysis"] = self._analyze_distribution_similarity(
                original_data, augmented_data
            )

            # 3. 모델 성능 비교 (타겟이 있는 경우)
            if target_columns:
                evaluation_results["model_performance"] = self._evaluate_model_performance(
                    original_data, augmented_data, target_columns, test_size
                )

            # 4. 품질 지표 계산
            evaluation_results["quality_metrics"] = self._calculate_quality_metrics(
                original_data, augmented_data
            )

            # 5. 전체 품질 점수
            evaluation_results["overall_quality_score"] = self._calculate_overall_quality_score(
                evaluation_results
            )

            self.evaluation_results = evaluation_results
            logger.info("데이터 증강 품질 평가 완료")
            return evaluation_results

        except Exception as e:
            logger.error(f"품질 평가 실패: {e}")
            raise

    def _compare_basic_statistics(
        self,
        original: pd.DataFrame,
        augmented: pd.DataFrame
    ) -> Dict[str, Any]:
        """기본 통계 비교"""
        stats_comparison = {}

        # 수치형 컬럼만 선택
        numeric_columns = original.select_dtypes(include=[np.number]).columns
        common_columns = [col for col in numeric_columns if col in augmented.columns]

        for column in common_columns:
            orig_stats = original[column].describe()
            aug_stats = augmented[column].describe()

            # 통계 차이 계산
            stats_diff = {
                "mean_difference": abs(orig_stats['mean'] - aug_stats['mean']) / orig_stats['std'] if orig_stats['std'] > 0 else 0,
                "std_ratio": aug_stats['std'] / orig_stats['std'] if orig_stats['std'] > 0 else 0,
                "range_similarity": min(aug_stats['max'] - aug_stats['min'], orig_stats['max'] - orig_stats['min']) / max(aug_stats['max'] - aug_stats['min'], orig_stats['max'] - orig_stats['min']) if max(aug_stats['max'] - aug_stats['min'], orig_stats['max'] - orig_stats['min']) > 0 else 1
            }

            stats_comparison[column] = {
                "original_stats": orig_stats.to_dict(),
                "augmented_stats": aug_stats.to_dict(),
                "differences": stats_diff,
                "quality_score": (
                    (1 - min(stats_diff["mean_difference"], 1)) * 0.4 +
                    (1 - abs(1 - stats_diff["std_ratio"])) * 0.3 +
                    stats_diff["range_similarity"] * 0.3
                )
            }

        return stats_comparison

    def _analyze_distribution_similarity(
        self,
        original: pd.DataFrame,
        augmented: pd.DataFrame
    ) -> Dict[str, Any]:
        """분포 유사성 분석"""
        distribution_analysis = {}

        numeric_columns = original.select_dtypes(include=[np.number]).columns
        common_columns = [col for col in numeric_columns if col in augmented.columns]

        for column in common_columns:
            try:
                orig_data = original[column].dropna()
                aug_data = augmented[column].dropna()

                if len(orig_data) == 0 or len(aug_data) == 0:
                    continue

                # Kolmogorov-Smirnov 테스트
                ks_statistic, ks_pvalue = stats.ks_2samp(orig_data, aug_data)

                # Mann-Whitney U 테스트
                mannwhitney_statistic, mannwhitney_pvalue = stats.mannwhitneyu(
                    orig_data, aug_data, alternative='two-sided'
                )

                # 분포 유사성 점수 (KS 통계량이 낮을수록 유사)
                similarity_score = max(0, 1 - ks_statistic)

                distribution_analysis[column] = {
                    "ks_statistic": float(ks_statistic),
                    "ks_pvalue": float(ks_pvalue),
                    "mannwhitney_pvalue": float(mannwhitney_pvalue),
                    "similarity_score": similarity_score,
                    "distribution_match": ks_pvalue > 0.05  # 같은 분포에서 왔다고 볼 수 있는지
                }

            except Exception as e:
                logger.warning(f"컬럼 {column} 분포 분석 실패: {e}")
                continue

        return distribution_analysis

    def _evaluate_model_performance(
        self,
        original: pd.DataFrame,
        augmented: pd.DataFrame,
        target_columns: List[str],
        test_size: float
    ) -> Dict[str, Any]:
        """모델 성능 비교 평가"""
        model_performance = {}

        for target_col in target_columns:
            if target_col not in original.columns or target_col not in augmented.columns:
                continue

            try:
                # 특성 컬럼 선택 (타겟 제외)
                feature_columns = [col for col in original.columns
                                 if col != target_col and col in augmented.columns
                                 and original[col].dtype in ['int64', 'float64']]

                if len(feature_columns) == 0:
                    continue

                # 데이터 준비
                X_orig = original[feature_columns].fillna(0)
                y_orig = original[target_col].fillna(0)

                X_aug = augmented[feature_columns].fillna(0)
                y_aug = augmented[target_col].fillna(0)

                # 결합된 데이터
                X_combined = pd.concat([X_orig, X_aug], ignore_index=True)
                y_combined = pd.concat([y_orig, y_aug], ignore_index=True)

                # 훈련/테스트 분할
                X_orig_train, X_orig_test, y_orig_train, y_orig_test = train_test_split(
                    X_orig, y_orig, test_size=test_size, random_state=42
                )

                X_comb_train, X_comb_test, y_comb_train, y_comb_test = train_test_split(
                    X_combined, y_combined, test_size=test_size, random_state=42
                )

                # 스케일링
                scaler = StandardScaler()
                X_orig_train_scaled = scaler.fit_transform(X_orig_train)
                X_orig_test_scaled = scaler.transform(X_orig_test)

                scaler_comb = StandardScaler()
                X_comb_train_scaled = scaler_comb.fit_transform(X_comb_train)
                X_comb_test_scaled = scaler_comb.transform(X_comb_test)

                # 모델 학습 및 평가
                performance_results = {}

                # 회귀 또는 분류 결정
                if len(np.unique(y_orig)) <= 10:  # 분류
                    models = {
                        'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42),
                        'LogisticRegression': LogisticRegression(random_state=42, max_iter=1000)
                    }
                    performance_results['task_type'] = 'classification'
                else:  # 회귀
                    models = {
                        'RandomForest': RandomForestRegressor(n_estimators=100, random_state=42),
                        'LinearRegression': LinearRegression()
                    }
                    performance_results['task_type'] = 'regression'

                for model_name, model in models.items():
                    # 원본 데이터만 사용
                    model_orig = model.__class__(**model.get_params())
                    model_orig.fit(X_orig_train_scaled, y_orig_train)
                    pred_orig = model_orig.predict(X_orig_test_scaled)

                    # 결합된 데이터 사용
                    model_comb = model.__class__(**model.get_params())
                    model_comb.fit(X_comb_train_scaled, y_comb_train)
                    pred_comb = model_comb.predict(X_comb_test_scaled)

                    if performance_results['task_type'] == 'classification':
                        # 분류 메트릭
                        orig_acc = accuracy_score(y_orig_test, pred_orig)
                        comb_acc = accuracy_score(y_comb_test, pred_comb)

                        performance_results[model_name] = {
                            'original_accuracy': float(orig_acc),
                            'combined_accuracy': float(comb_acc),
                            'improvement': float(comb_acc - orig_acc)
                        }
                    else:
                        # 회귀 메트릭
                        orig_mse = mean_squared_error(y_orig_test, pred_orig)
                        orig_r2 = r2_score(y_orig_test, pred_orig)

                        comb_mse = mean_squared_error(y_comb_test, pred_comb)
                        comb_r2 = r2_score(y_comb_test, pred_comb)

                        performance_results[model_name] = {
                            'original_mse': float(orig_mse),
                            'original_r2': float(orig_r2),
                            'combined_mse': float(comb_mse),
                            'combined_r2': float(comb_r2),
                            'mse_improvement': float(orig_mse - comb_mse),
                            'r2_improvement': float(comb_r2 - orig_r2)
                        }

                model_performance[target_col] = performance_results

            except Exception as e:
                logger.warning(f"타겟 {target_col} 모델 성능 평가 실패: {e}")
                continue

        return model_performance

    def _calculate_quality_metrics(
        self,
        original: pd.DataFrame,
        augmented: pd.DataFrame
    ) -> Dict[str, Any]:
        """품질 지표 계산"""
        quality_metrics = {}

        # 기본 품질 지표
        quality_metrics['data_completeness'] = {
            'original_completeness': (1 - original.isnull().sum().sum() / (len(original) * len(original.columns))),
            'augmented_completeness': (1 - augmented.isnull().sum().sum() / (len(augmented) * len(augmented.columns)))
        }

        # 다양성 지표
        numeric_columns = original.select_dtypes(include=[np.number]).columns
        common_columns = [col for col in numeric_columns if col in augmented.columns]

        diversity_scores = []
        for column in common_columns:
            orig_std = original[column].std()
            aug_std = augmented[column].std()
            if orig_std > 0:
                diversity_ratio = aug_std / orig_std
                diversity_scores.append(min(diversity_ratio, 2.0))  # Cap at 2.0

        quality_metrics['diversity_score'] = np.mean(diversity_scores) if diversity_scores else 0

        # 현실성 지표 (이상값 비율)
        realism_scores = []
        for column in common_columns:
            orig_q1, orig_q3 = original[column].quantile([0.25, 0.75])
            orig_iqr = orig_q3 - orig_q1

            if orig_iqr > 0:
                orig_lower = orig_q1 - 1.5 * orig_iqr
                orig_upper = orig_q3 + 1.5 * orig_iqr

                aug_outliers = augmented[
                    (augmented[column] < orig_lower) | (augmented[column] > orig_upper)
                ]
                outlier_ratio = len(aug_outliers) / len(augmented)
                realism_score = max(0, 1 - outlier_ratio * 2)  # 이상값이 적을수록 높은 점수
                realism_scores.append(realism_score)

        quality_metrics['realism_score'] = np.mean(realism_scores) if realism_scores else 0

        return quality_metrics

    def _calculate_overall_quality_score(self, evaluation_results: Dict[str, Any]) -> float:
        """전체 품질 점수 계산"""
        try:
            scores = []

            # 통계적 유사성 점수
            stat_scores = [
                result['quality_score']
                for result in evaluation_results['statistical_comparison'].values()
            ]
            if stat_scores:
                scores.append(np.mean(stat_scores))

            # 분포 유사성 점수
            dist_scores = [
                result['similarity_score']
                for result in evaluation_results['distribution_analysis'].values()
            ]
            if dist_scores:
                scores.append(np.mean(dist_scores))

            # 품질 지표 점수
            quality_metrics = evaluation_results['quality_metrics']
            if 'diversity_score' in quality_metrics:
                # 다양성 점수 정규화 (1.0이 이상적)
                diversity_normalized = 1 - abs(1 - quality_metrics['diversity_score'])
                scores.append(diversity_normalized)

            if 'realism_score' in quality_metrics:
                scores.append(quality_metrics['realism_score'])

            # 전체 점수 (0-1 범위)
            overall_score = np.mean(scores) if scores else 0.5
            return float(np.clip(overall_score, 0, 1))

        except Exception as e:
            logger.error(f"전체 품질 점수 계산 실패: {e}")
            return 0.5

    def generate_evaluation_report(self, output_path: str = None) -> str:
        """평가 리포트 생성"""
        if not self.evaluation_results:
            return "평가 결과가 없습니다. 먼저 evaluate_augmentation_quality()를 실행하세요."

        results = self.evaluation_results

        report_lines = [
            "=" * 60,
            "📊 데이터 증강 품질 평가 리포트",
            "=" * 60,
            f"평가 시각: {results['evaluation_timestamp']}",
            "",
            "📈 데이터 정보:",
            f"  원본 샘플 수: {results['data_info']['original_samples']:,}개",
            f"  증강 샘플 수: {results['data_info']['augmented_samples']:,}개",
            f"  증강 비율: {results['data_info']['augmentation_ratio']:.2f}배",
            "",
            f"🎯 전체 품질 점수: {results['overall_quality_score']:.3f}/1.000",
            ""
        ]

        # 통계 비교 요약
        if results['statistical_comparison']:
            report_lines.extend([
                "📊 통계적 유사성:",
                "  컬럼별 품질 점수:"
            ])
            for col, stats in results['statistical_comparison'].items():
                score = stats['quality_score']
                report_lines.append(f"    {col}: {score:.3f}")

        # 분포 유사성 요약
        if results['distribution_analysis']:
            report_lines.extend([
                "",
                "📈 분포 유사성:",
                "  컬럼별 유사성 점수:"
            ])
            for col, dist in results['distribution_analysis'].items():
                score = dist['similarity_score']
                match = "✓" if dist['distribution_match'] else "✗"
                report_lines.append(f"    {col}: {score:.3f} {match}")

        # 품질 지표
        if results['quality_metrics']:
            quality = results['quality_metrics']
            report_lines.extend([
                "",
                "🔍 품질 지표:",
                f"  데이터 완성도: {quality.get('diversity_score', 0):.3f}",
                f"  다양성 점수: {quality.get('diversity_score', 0):.3f}",
                f"  현실성 점수: {quality.get('realism_score', 0):.3f}"
            ])

        # 모델 성능 (있는 경우)
        if results['model_performance']:
            report_lines.extend([
                "",
                "🤖 모델 성능 비교:"
            ])
            for target, perf in results['model_performance'].items():
                task_type = perf.get('task_type', 'unknown')
                report_lines.append(f"  타겟: {target} ({task_type})")

                for model, metrics in perf.items():
                    if model == 'task_type':
                        continue

                    if task_type == 'classification':
                        improvement = metrics.get('improvement', 0)
                        symbol = "📈" if improvement > 0 else "📉" if improvement < 0 else "➡️"
                        report_lines.append(f"    {model}: {improvement:+.3f} {symbol}")
                    else:
                        r2_improvement = metrics.get('r2_improvement', 0)
                        symbol = "📈" if r2_improvement > 0 else "📉" if r2_improvement < 0 else "➡️"
                        report_lines.append(f"    {model} R²: {r2_improvement:+.3f} {symbol}")

        report_lines.extend([
            "",
            "=" * 60
        ])

        report_text = "\n".join(report_lines)

        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(report_text)
                logger.info(f"평가 리포트 저장 완료: {output_path}")
            except Exception as e:
                logger.error(f"평가 리포트 저장 실패: {e}")

        return report_text

    def save_evaluation_results(self, output_path: str):
        """평가 결과를 JSON 파일로 저장"""
        try:
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.evaluation_results, f, ensure_ascii=False, indent=2)
            logger.info(f"평가 결과 저장 완료: {output_path}")
        except Exception as e:
            logger.error(f"평가 결과 저장 실패: {e}")
            raise