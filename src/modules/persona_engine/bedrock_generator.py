# -*- coding: utf-8 -*-
"""
bedrock_generator.py
AWS Bedrock을 사용한 EC2 기반 페르소나 생성 엔진
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import numpy as np
import pandas as pd

# AWS SDK
import boto3
from botocore.exceptions import ClientError, BotoCoreError

# 기존 데이터 분석 모듈들
import sys
sys.path.append(str(Path(__file__).parent.parent))

try:
    from data_analysis.clustering import persona_clustering
    from data_analysis.risk_scoring.rules_loader import load_rules, apply_rules_to_dataframe
except ImportError as e:
    logging.warning(f"데이터 분석 모듈 임포트 실패: {e}")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BedrockPersonaGenerator:
    """AWS Bedrock Claude 3.5 Haiku를 사용한 페르소나 생성기"""

    def __init__(self, region_name: str = "us-east-1"):
        """
        AWS Bedrock 클라이언트 초기화

        Args:
            region_name: AWS 리전 (기본값: us-east-1)
        """
        self.region_name = region_name
        self.model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"  # Claude 3.5 Haiku

        # Bedrock 클라이언트 초기화
        try:
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=region_name
            )
            logger.info(f"✅ AWS Bedrock 클라이언트 초기화 완료 (리전: {region_name})")
        except Exception as e:
            logger.error(f"❌ AWS Bedrock 클라이언트 초기화 실패: {e}")
            raise

        # 데이터 경로 설정
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.data_path = self.project_root / "src" / "modules" / "data_analysis"

        # 캐시
        self.cluster_cache = {}
        self.knowledge_cache = {}

    def load_cluster_data(self) -> Optional[pd.DataFrame]:
        """클러스터링 결과 데이터 로드"""
        try:
            # 가능한 데이터 파일 경로들
            possible_paths = [
                self.data_path / "rag_aug_out" / "processed_data.csv",
                self.data_path / "risk_scoring" / "telecom_group_monthly_all_with_preds.csv",
                self.project_root / "data" / "processed_telecom_data.csv"
            ]

            for path in possible_paths:
                if path.exists():
                    logger.info(f"📊 데이터 로딩: {path}")
                    return pd.read_csv(path)

            logger.warning("⚠️ 클러스터 데이터 파일을 찾을 수 없음")
            return None

        except Exception as e:
            logger.error(f"❌ 클러스터 데이터 로딩 실패: {e}")
            return None

    def load_knowledge_base(self) -> Dict[str, Any]:
        """RAG 지식 베이스 로드"""
        if self.knowledge_cache:
            return self.knowledge_cache

        try:
            kb_path = self.data_path / "rag_aug_out" / "kb_chunks.jsonl"

            if not kb_path.exists():
                logger.warning("⚠️ kb_chunks.jsonl 파일을 찾을 수 없음")
                return {}

            knowledge = {}
            with open(kb_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        chunk = json.loads(line.strip())
                        chunk_type = chunk.get('meta', {}).get('type', 'general')
                        knowledge[chunk_type] = chunk.get('text', '')

            self.knowledge_cache = knowledge
            logger.info(f"📚 지식 베이스 로딩 완료: {len(knowledge)}개 청크")
            return knowledge

        except Exception as e:
            logger.error(f"❌ 지식 베이스 로딩 실패: {e}")
            return {}

    async def call_bedrock_async(self, prompt: str, max_tokens: int = 2000) -> str:
        """AWS Bedrock Claude 비동기 호출"""
        try:
            # Claude 3.5 요청 형식
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "top_p": 0.9
            }

            # 비동기 호출을 위한 executor 사용
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(request_body)
                )
            )

            # 응답 파싱
            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [{}])[0].get('text', '')

            logger.debug(f"🤖 Bedrock 응답 길이: {len(content)} 문자")
            return content

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"❌ Bedrock API 오류 ({error_code}): {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Bedrock 호출 실패: {e}")
            raise

    def generate_cluster_summary(self, cluster_data: pd.DataFrame, cluster_id: int) -> Dict[str, Any]:
        """클러스터 데이터 요약 생성"""
        try:
            # 기본 통계
            summary = {
                "cluster_id": cluster_id,
                "sample_count": len(cluster_data),
                "demographics": {},
                "behavior_patterns": {},
                "welfare_indicators": {}
            }

            # 인구통계 정보
            if '연령대' in cluster_data.columns:
                summary["demographics"]["avg_age"] = float(cluster_data['연령대'].mean())
                summary["demographics"]["age_distribution"] = cluster_data['연령대'].value_counts().to_dict()

            if '자치구' in cluster_data.columns:
                summary["demographics"]["districts"] = cluster_data['자치구'].value_counts().head(3).to_dict()

            if '성별' in cluster_data.columns:
                summary["demographics"]["gender_ratio"] = cluster_data['성별'].value_counts(normalize=True).to_dict()

            # 행동 패턴 (수치형 컬럼들의 평균)
            behavior_cols = [
                '평일 총 이동 거리 합계', '동영상/방송 서비스 사용일수',
                '배달 서비스 사용일수', '평균 통화대상자 수', 'SNS 사용횟수'
            ]

            for col in behavior_cols:
                if col in cluster_data.columns:
                    value = cluster_data[col].mean()
                    if not pd.isna(value):
                        summary["behavior_patterns"][col] = float(value)

            # 복지 지표 (확률 컬럼들)
            welfare_cols = [col for col in cluster_data.columns if col.startswith('proba_LBL_')]
            for col in welfare_cols:
                value = cluster_data[col].mean()
                if not pd.isna(value):
                    summary["welfare_indicators"][col] = float(value)

            return summary

        except Exception as e:
            logger.error(f"❌ 클러스터 요약 생성 실패: {e}")
            return {"cluster_id": cluster_id, "error": str(e)}

    def create_persona_prompt(self, cluster_summary: Dict[str, Any], knowledge_context: str) -> str:
        """페르소나 생성을 위한 프롬프트 작성"""

        cluster_id = cluster_summary.get("cluster_id", 0)
        demographics = cluster_summary.get("demographics", {})
        behaviors = cluster_summary.get("behavior_patterns", {})
        welfare = cluster_summary.get("welfare_indicators", {})

        # 주요 복지 욕구 식별
        high_welfare_needs = []
        for key, value in welfare.items():
            if value > 0.6:  # 높은 욕구
                category = key.replace('proba_LBL_', '')
                high_welfare_needs.append(category)

        prompt = f"""
서울시 1인가구 데이터 분석을 바탕으로 현실적인 페르소나를 생성해주세요.

## 데이터 분석 결과 (클러스터 {cluster_id})
- 표본 수: {cluster_summary.get('sample_count', 0)}명
- 평균 연령대: {demographics.get('avg_age', 40):.1f}세
- 주요 거주지역: {list(demographics.get('districts', {}).keys())[:2]}
- 행동 패턴 점수:
  * 이동성: {behaviors.get('평일 총 이동 거리 합계', 0):.2f}
  * 디지털 활용: {behaviors.get('동영상/방송 서비스 사용일수', 0):.2f}
  * 사회적 소통: {behaviors.get('평균 통화대상자 수', 0):.2f}
  * 배달 서비스: {behaviors.get('배달 서비스 사용일수', 0):.2f}
- 주요 복지 욕구: {high_welfare_needs[:3]}

## 컨텍스트 정보
{knowledge_context[:1000]}

## 요청사항
위 데이터를 바탕으로 다음 형식의 JSON으로 현실적인 페르소나 1명을 생성해주세요:

{{
  "name": "한국식 이름",
  "age": 구체적 나이,
  "gender": "남성" 또는 "여성",
  "district": "서울시 자치구명",
  "occupation": "직업",
  "living_situation": "거주 형태 설명",
  "personality_traits": ["성격 특성 3개"],
  "daily_routine": "하루 일과 설명 (2-3문장)",
  "digital_habits": "디지털 기기/서비스 사용 패턴",
  "social_patterns": "사회적 관계 및 소통 방식",
  "mobility_style": "이동 패턴 및 교통수단 이용",
  "consumption_habits": "소비 패턴 및 서비스 이용",
  "challenges": ["주요 어려움 3개"],
  "welfare_needs": ["필요한 복지 서비스 3개"],
  "goals": ["개인적 목표나 바람 2개"],
  "background_story": "이 사람의 배경과 현재 상황 설명 (3-4문장)"
}}

반드시 JSON 형식으로만 응답하고, 한국의 1인가구 현실을 정확히 반영해주세요.
"""

        return prompt

    async def generate_single_persona(self, cluster_summary: Dict[str, Any]) -> Dict[str, Any]:
        """단일 페르소나 생성"""
        try:
            # 지식 컨텍스트 준비
            knowledge = self.load_knowledge_base()
            context = knowledge.get('overview', '') + '\n' + knowledge.get('feature_mapping', '')[:500]

            # 프롬프트 생성
            prompt = self.create_persona_prompt(cluster_summary, context)

            # Bedrock 호출
            logger.info(f"🤖 클러스터 {cluster_summary.get('cluster_id')} 페르소나 생성 중...")
            response = await self.call_bedrock_async(prompt, max_tokens=3000)

            # JSON 응답 파싱
            try:
                # JSON 부분만 추출 (응답에 다른 텍스트가 포함될 수 있음)
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_text = response[json_start:json_end]
                    persona_data = json.loads(json_text)
                else:
                    raise ValueError("JSON 형식을 찾을 수 없음")

            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"❌ JSON 파싱 실패: {e}")
                logger.debug(f"원본 응답: {response}")

                # 폴백 페르소나 생성
                persona_data = self.create_fallback_persona(cluster_summary)

            # 메타데이터 추가
            persona_data.update({
                "cluster_id": cluster_summary.get("cluster_id"),
                "confidence_score": 0.85,
                "generated_at": datetime.now().isoformat(),
                "generation_method": "bedrock_claude",
                "data_source": "seoul_single_household_telecom"
            })

            return persona_data

        except Exception as e:
            logger.error(f"❌ 페르소나 생성 실패: {e}")
            return self.create_fallback_persona(cluster_summary)

    def create_fallback_persona(self, cluster_summary: Dict[str, Any]) -> Dict[str, Any]:
        """오류 발생시 기본 페르소나 생성"""
        cluster_id = cluster_summary.get("cluster_id", 0)
        demographics = cluster_summary.get("demographics", {})

        fallback_names = ["김민수", "이지은", "박준호", "최서연", "정태우"]
        districts = ["강남구", "관악구", "성북구", "마포구", "송파구"]

        return {
            "name": fallback_names[cluster_id % len(fallback_names)],
            "age": int(demographics.get("avg_age", 35)),
            "gender": "남성" if cluster_id % 2 == 0 else "여성",
            "district": districts[cluster_id % len(districts)],
            "occupation": "회사원",
            "living_situation": "원룸 거주",
            "personality_traits": ["독립적", "실용적", "신중함"],
            "daily_routine": "규칙적인 출퇴근과 집에서의 휴식 시간을 보냅니다.",
            "digital_habits": "스마트폰과 온라인 서비스를 적절히 활용합니다.",
            "social_patterns": "가족, 친구들과 적절한 연락을 유지합니다.",
            "mobility_style": "대중교통 주로 이용",
            "consumption_habits": "필요에 따른 합리적 소비",
            "challenges": ["경제적 부담", "사회적 고립", "건강 관리"],
            "welfare_needs": ["생계지원", "의료지원", "주거지원"],
            "goals": ["안정적인 생활", "건강한 미래"],
            "background_story": "서울에서 독립적인 1인가구 생활을 하고 있는 평범한 시민입니다.",
            "cluster_id": cluster_id,
            "confidence_score": 0.6,
            "generated_at": datetime.now().isoformat(),
            "generation_method": "fallback",
            "data_source": "cluster_summary"
        }

    async def generate_personas(self, n_personas: int = 5) -> List[Dict[str, Any]]:
        """여러 페르소나 생성"""
        logger.info(f"🎭 {n_personas}개 페르소나 생성 시작...")

        try:
            # 데이터 로드
            data = self.load_cluster_data()
            if data is None:
                logger.warning("⚠️ 데이터가 없어 기본 페르소나 생성")
                return [self.create_fallback_persona({"cluster_id": i}) for i in range(n_personas)]

            # 클러스터링 수행 (데이터가 있는 경우)
            try:
                if len(data) > 1000:  # 충분한 데이터가 있는 경우
                    # 실제 클러스터링 수행
                    unit_cols = ["자치구", "행정동", "성별", "연령대"]
                    unit_cols = [col for col in unit_cols if col in data.columns]

                    if unit_cols:
                        labels_df, model_info = persona_clustering(
                            df=data.sample(min(10000, len(data))),  # 샘플링으로 성능 최적화
                            unit_cols=unit_cols,
                            K_list=[3, 4, 5, 6, 7][:n_personas+2]
                        )

                        # 클러스터별 요약 생성
                        cluster_summaries = []
                        for i in range(min(n_personas, model_info['K'])):
                            cluster_mask = labels_df['persona_id'] == i
                            cluster_data = data[data.index.isin(labels_df[cluster_mask].index)]

                            if len(cluster_data) > 0:
                                summary = self.generate_cluster_summary(cluster_data, i)
                                cluster_summaries.append(summary)
                    else:
                        raise ValueError("적절한 단위 컬럼이 없음")

                else:
                    raise ValueError("데이터가 부족함")

            except Exception as e:
                logger.warning(f"⚠️ 클러스터링 실패, 데이터 기반 요약 생성: {e}")
                # 데이터를 균등 분할하여 요약 생성
                chunk_size = len(data) // n_personas
                cluster_summaries = []

                for i in range(n_personas):
                    start_idx = i * chunk_size
                    end_idx = (i + 1) * chunk_size if i < n_personas - 1 else len(data)
                    chunk_data = data.iloc[start_idx:end_idx]

                    summary = self.generate_cluster_summary(chunk_data, i)
                    cluster_summaries.append(summary)

            # 비동기로 페르소나 생성
            tasks = []
            for summary in cluster_summaries:
                task = self.generate_single_persona(summary)
                tasks.append(task)

            personas = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 정리 (예외 처리)
            valid_personas = []
            for i, persona in enumerate(personas):
                if isinstance(persona, Exception):
                    logger.error(f"❌ 페르소나 {i} 생성 실패: {persona}")
                    valid_personas.append(self.create_fallback_persona({"cluster_id": i}))
                else:
                    valid_personas.append(persona)

            logger.info(f"✅ {len(valid_personas)}개 페르소나 생성 완료")
            return valid_personas

        except Exception as e:
            logger.error(f"❌ 페르소나 생성 프로세스 실패: {e}")
            # 전체 실패시 기본 페르소나들 반환
            return [self.create_fallback_persona({"cluster_id": i}) for i in range(n_personas)]

    def save_personas(self, personas: List[Dict[str, Any]], output_path: str):
        """생성된 페르소나 저장"""
        try:
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            personas_data = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_personas": len(personas),
                    "generator": "bedrock_claude_3_5_haiku",
                    "region": self.region_name,
                    "version": "1.0"
                },
                "personas": personas
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(personas_data, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 페르소나 저장 완료: {output_path}")

        except Exception as e:
            logger.error(f"❌ 페르소나 저장 실패: {e}")

async def main():
    """CLI 테스트"""
    import argparse

    parser = argparse.ArgumentParser(description="AWS Bedrock 페르소나 생성기")
    parser.add_argument("--personas", type=int, default=5, help="생성할 페르소나 수")
    parser.add_argument("--region", default="us-east-1", help="AWS 리전")
    parser.add_argument("--output", default="bedrock_personas.json", help="출력 파일")

    args = parser.parse_args()

    # 생성기 초기화
    generator = BedrockPersonaGenerator(region_name=args.region)

    try:
        # 페르소나 생성
        personas = await generator.generate_personas(args.personas)

        # 결과 출력
        print(f"\n🎭 생성된 페르소나들:")
        for i, persona in enumerate(personas):
            print(f"{i+1}. {persona.get('name', '이름없음')} "
                  f"({persona.get('age', '?')}세, {persona.get('district', '지역미상')})")
            print(f"   직업: {persona.get('occupation', '미상')}")
            print(f"   주요 특성: {', '.join(persona.get('personality_traits', [])[:2])}")
            print()

        # 파일 저장
        generator.save_personas(personas, args.output)

        # 통계
        print(f"📊 생성 통계:")
        print(f"  - 총 페르소나: {len(personas)}개")
        bedrock_count = sum(1 for p in personas if p.get('generation_method') == 'bedrock_claude')
        print(f"  - Bedrock 생성: {bedrock_count}개")
        print(f"  - 폴백 생성: {len(personas) - bedrock_count}개")

    except Exception as e:
        logger.error(f"❌ 실행 실패: {e}")
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())