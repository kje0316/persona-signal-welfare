"""
페르소나 기반 데이터 증강기
생성된 페르소나를 활용하여 현실적인 합성 데이터 생성
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
import random

from ..persona_engine.rag_engine import RAGEngine

logger = logging.getLogger(__name__)


class PersonaBasedAugmenter:
    """페르소나 기반 데이터 증강 엔진"""

    def __init__(self):
        self.rag_engine = RAGEngine()
        self.augmentation_strategies = {
            'interpolation': self._interpolate_features,
            'noise_addition': self._add_realistic_noise,
            'pattern_variation': self._vary_behavioral_patterns,
            'demographic_shift': self._shift_demographics
        }

    def augment_data_from_personas(
        self,
        original_data: pd.DataFrame,
        personas: List[Dict[str, Any]],
        target_samples: int,
        strategies: List[str] = None
    ) -> pd.DataFrame:
        """페르소나를 기반으로 데이터 증강"""
        try:
            logger.info(f"페르소나 기반 데이터 증강 시작: {target_samples}개 샘플 목표")

            if strategies is None:
                strategies = ['interpolation', 'noise_addition', 'pattern_variation']

            augmented_samples = []
            samples_per_persona = max(1, target_samples // len(personas))

            for persona in personas:
                logger.info(f"페르소나 '{persona['name']}' 기반 데이터 생성...")

                # 해당 페르소나 클러스터의 원본 데이터 찾기
                cluster_id = persona['cluster_info']['cluster_id']
                cluster_data = original_data[original_data['cluster_id'] == cluster_id].copy()

                if len(cluster_data) == 0:
                    logger.warning(f"클러스터 {cluster_id}에 해당하는 데이터가 없습니다")
                    continue

                # 각 전략별로 샘플 생성
                persona_samples = self._generate_samples_for_persona(
                    cluster_data, persona, samples_per_persona, strategies
                )

                augmented_samples.extend(persona_samples)

            # DataFrame 생성
            augmented_df = pd.DataFrame(augmented_samples)

            # 부족한 샘플 보완
            current_count = len(augmented_df)
            if current_count < target_samples:
                additional_needed = target_samples - current_count
                additional_samples = self._generate_additional_samples(
                    original_data, personas, additional_needed, strategies
                )
                additional_df = pd.DataFrame(additional_samples)
                augmented_df = pd.concat([augmented_df, additional_df], ignore_index=True)

            # 최종 샘플 수 조정
            if len(augmented_df) > target_samples:
                augmented_df = augmented_df.sample(n=target_samples, random_state=42).reset_index(drop=True)

            logger.info(f"데이터 증강 완료: {len(augmented_df)}개 샘플 생성")
            return augmented_df

        except Exception as e:
            logger.error(f"데이터 증강 실패: {e}")
            raise

    def _generate_samples_for_persona(
        self,
        cluster_data: pd.DataFrame,
        persona: Dict[str, Any],
        target_count: int,
        strategies: List[str]
    ) -> List[Dict[str, Any]]:
        """특정 페르소나에 대한 샘플 생성"""
        samples = []

        for i in range(target_count):
            # 기반이 될 원본 샘플 선택
            base_sample = cluster_data.sample(1, random_state=42 + i).iloc[0].to_dict()

            # 페르소나 특성을 반영한 샘플 생성
            augmented_sample = self._create_persona_influenced_sample(
                base_sample, persona, strategies
            )

            # 메타데이터 추가
            augmented_sample.update({
                'augmentation_source': 'persona_based',
                'source_persona': persona['name'],
                'source_cluster_id': persona['cluster_info']['cluster_id'],
                'generated_at': datetime.now().isoformat(),
                'is_synthetic': True
            })

            samples.append(augmented_sample)

        return samples

    def _create_persona_influenced_sample(
        self,
        base_sample: Dict[str, Any],
        persona: Dict[str, Any],
        strategies: List[str]
    ) -> Dict[str, Any]:
        """페르소나 특성을 반영한 샘플 생성"""
        augmented_sample = base_sample.copy()

        # 페르소나의 behavioral_patterns 반영
        if 'behavioral_patterns' in persona:
            behavioral_patterns = persona['behavioral_patterns']

            # 생활 패턴 반영
            if '생활패턴' in behavioral_patterns:
                pattern_desc = behavioral_patterns['생활패턴'].lower()
                if '활발' in pattern_desc or '높음' in pattern_desc:
                    self._adjust_mobility_features(augmented_sample, 1.2)
                elif '정적' in pattern_desc or '낮음' in pattern_desc:
                    self._adjust_mobility_features(augmented_sample, 0.8)

            # 디지털 사용 패턴 반영
            if '디지털이용' in behavioral_patterns:
                digital_desc = behavioral_patterns['디지털이용'].lower()
                if '높음' in digital_desc or '적극' in digital_desc:
                    self._adjust_digital_features(augmented_sample, 1.3)
                elif '낮음' in digital_desc or '제한' in digital_desc:
                    self._adjust_digital_features(augmented_sample, 0.7)

        # 나이대별 특성 반영
        age = persona.get('age', 30)
        self._adjust_age_related_features(augmented_sample, age)

        # 선택된 증강 전략 적용
        for strategy in strategies:
            if strategy in self.augmentation_strategies:
                augmented_sample = self.augmentation_strategies[strategy](augmented_sample, persona)

        return augmented_sample

    def _adjust_mobility_features(self, sample: Dict[str, Any], multiplier: float):
        """이동성 관련 특성 조정"""
        mobility_features = [
            '평일 총 이동 거리 합계', '주말 총 이동 거리 합계',
            '평일 평균 이동 거리', '주말 평균 이동 거리'
        ]

        for feature in mobility_features:
            if feature in sample and pd.notna(sample[feature]):
                sample[feature] = max(0, sample[feature] * multiplier)

    def _adjust_digital_features(self, sample: Dict[str, Any], multiplier: float):
        """디지털 사용 관련 특성 조정"""
        digital_features = [
            '동영상/방송 서비스 사용일수', '게임 서비스 사용일수',
            '음악 서비스 사용일수', '소셜네트워크 서비스 사용일수'
        ]

        for feature in digital_features:
            if feature in sample and pd.notna(sample[feature]):
                sample[feature] = max(0, sample[feature] * multiplier)

    def _adjust_age_related_features(self, sample: Dict[str, Any], age: int):
        """나이와 관련된 특성 조정"""
        if age < 30:  # 청년층
            # 더 활발한 디지털 사용
            digital_boost = 1.2
            # 더 많은 소셜 활동
            social_boost = 1.1
        elif age >= 60:  # 노년층
            # 적은 디지털 사용
            digital_boost = 0.7
            # 적은 이동성
            social_boost = 0.8
        else:  # 중년층
            digital_boost = 1.0
            social_boost = 1.0

        # 적용
        self._adjust_digital_features(sample, digital_boost)

        social_features = ['평균 통화대상자 수', '평균 문자대상자 수']
        for feature in social_features:
            if feature in sample and pd.notna(sample[feature]):
                sample[feature] = max(0, sample[feature] * social_boost)

    def _interpolate_features(self, sample: Dict[str, Any], persona: Dict[str, Any]) -> Dict[str, Any]:
        """특성 보간을 통한 변형"""
        result = sample.copy()

        # 수치형 특성들에 대해 소량의 변동 추가
        for key, value in result.items():
            if isinstance(value, (int, float)) and pd.notna(value) and key != 'cluster_id':
                # 정규분포를 따르는 노이즈 추가 (표준편차 5%)
                noise_factor = np.random.normal(1.0, 0.05)
                result[key] = max(0, value * noise_factor)

        return result

    def _add_realistic_noise(self, sample: Dict[str, Any], persona: Dict[str, Any]) -> Dict[str, Any]:
        """현실적인 노이즈 추가"""
        result = sample.copy()

        # 특성별 현실적인 변동 범위 정의
        noise_ranges = {
            '평일 총 이동 거리 합계': 0.15,  # ±15%
            '주말 총 이동 거리 합계': 0.20,  # ±20%
            '동영상/방송 서비스 사용일수': 0.10,  # ±10%
            '평균 통화대상자 수': 0.25,  # ±25%
        }

        for key, value in result.items():
            if isinstance(value, (int, float)) and pd.notna(value) and key in noise_ranges:
                noise_range = noise_ranges[key]
                noise_factor = np.random.uniform(1 - noise_range, 1 + noise_range)
                result[key] = max(0, value * noise_factor)

        return result

    def _vary_behavioral_patterns(self, sample: Dict[str, Any], persona: Dict[str, Any]) -> Dict[str, Any]:
        """행동 패턴 변형"""
        result = sample.copy()

        # 페르소나의 특성에 따른 패턴 변형
        if 'characteristics' in persona:
            characteristics = persona['characteristics']

            for char in characteristics:
                char_lower = char.lower()

                if '활발' in char_lower or '적극' in char_lower:
                    # 활동성 증가
                    self._adjust_mobility_features(result, np.random.uniform(1.1, 1.3))

                elif '소극' in char_lower or '조용' in char_lower:
                    # 활동성 감소
                    self._adjust_mobility_features(result, np.random.uniform(0.7, 0.9))

        return result

    def _shift_demographics(self, sample: Dict[str, Any], persona: Dict[str, Any]) -> Dict[str, Any]:
        """인구통계학적 특성 변형"""
        result = sample.copy()

        # 나이대별 특성 조정
        age = persona.get('age', 30)
        age_group = persona.get('age_group', '중년층')

        if age_group == '청년층':
            # 청년층 특성 강화
            self._adjust_digital_features(result, np.random.uniform(1.2, 1.4))
        elif age_group == '노년층':
            # 노년층 특성 강화
            self._adjust_digital_features(result, np.random.uniform(0.6, 0.8))
            self._adjust_mobility_features(result, np.random.uniform(0.7, 0.9))

        return result

    def _generate_additional_samples(
        self,
        original_data: pd.DataFrame,
        personas: List[Dict[str, Any]],
        needed_count: int,
        strategies: List[str]
    ) -> List[Dict[str, Any]]:
        """부족한 샘플 추가 생성"""
        additional_samples = []

        for i in range(needed_count):
            # 랜덤하게 페르소나 선택
            persona = random.choice(personas)
            cluster_id = persona['cluster_info']['cluster_id']

            # 해당 클러스터 데이터
            cluster_data = original_data[original_data['cluster_id'] == cluster_id]

            if len(cluster_data) > 0:
                base_sample = cluster_data.sample(1, random_state=42 + i).iloc[0].to_dict()

                augmented_sample = self._create_persona_influenced_sample(
                    base_sample, persona, strategies
                )

                augmented_sample.update({
                    'augmentation_source': 'persona_based_additional',
                    'source_persona': persona['name'],
                    'source_cluster_id': cluster_id,
                    'generated_at': datetime.now().isoformat(),
                    'is_synthetic': True
                })

                additional_samples.append(augmented_sample)

        return additional_samples

    def save_augmented_data(self, augmented_df: pd.DataFrame, output_path: str):
        """증강된 데이터를 파일로 저장"""
        try:
            augmented_df.to_csv(output_path, index=False, encoding='utf-8')
            logger.info(f"증강된 데이터 저장 완료: {output_path} ({len(augmented_df)} 샘플)")
        except Exception as e:
            logger.error(f"증강된 데이터 저장 실패: {e}")
            raise