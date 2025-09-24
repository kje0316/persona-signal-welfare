"""
RAG 엔진 - S3/Bedrock Knowledge Base 연동
도메인 지식을 S3에 업로드하고 RAG 기반 생성 수행
"""

import json
import logging
from typing import Dict, Any, List, Optional

from ..common.aws_clients import s3_client, bedrock_client

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG 엔진"""

    def __init__(self):
        self.s3_client = s3_client
        self.bedrock_client = bedrock_client

    def upload_knowledge_base(self, task_id: str, knowledge_file_paths: List[str]) -> Dict[str, Any]:
        """도메인 지식을 S3에 업로드"""
        try:
            logger.info(f"지식 기반 업로드 시작: {task_id}")

            if not knowledge_file_paths:
                logger.info("업로드할 지식 파일이 없습니다")
                return {
                    "task_id": task_id,
                    "uploaded_files": [],
                    "failed_files": [],
                    "success_count": 0,
                    "fail_count": 0,
                    "knowledge_summary": {}
                }

            # S3에 업로드
            upload_result = self.s3_client.upload_knowledge_files(task_id, knowledge_file_paths)

            # 지식 요약 생성
            knowledge_summary = self._create_knowledge_summary(knowledge_file_paths)

            result = {
                **upload_result,
                "knowledge_summary": knowledge_summary
            }

            logger.info(f"지식 기반 업로드 완료: {upload_result['success_count']}개 성공")
            return result

        except Exception as e:
            logger.error(f"지식 기반 업로드 실패: {e}")
            raise

    def _create_knowledge_summary(self, file_paths: List[str]) -> Dict[str, Any]:
        """지식 파일들의 요약 생성"""
        try:
            knowledge_content = []
            total_content_length = 0

            for file_path in file_paths:
                try:
                    if file_path.endswith(('.txt', '.md')):
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            sample_content = content[:2000]  # 처음 2000자만
                            knowledge_content.append({
                                'filename': file_path.split('/')[-1],
                                'content_sample': sample_content[:500],  # 샘플은 500자
                                'content_length': len(content),
                                'type': 'text'
                            })
                            total_content_length += len(content)

                    # TODO: PDF, DOCX 등 다른 형식 지원 추가

                except Exception as e:
                    logger.warning(f"지식 파일 처리 실패: {file_path}, {e}")

            summary = {
                'files_processed': len(knowledge_content),
                'total_content_length': total_content_length,
                'content_samples': [item['content_sample'] for item in knowledge_content[:3]],
                'file_types': list(set(item['type'] for item in knowledge_content))
            }

            logger.info(f"지식 요약 생성 완료: {len(knowledge_content)}개 파일")
            return summary

        except Exception as e:
            logger.error(f"지식 요약 생성 실패: {e}")
            return {}

    def retrieve_domain_knowledge(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """도메인 지식 검색"""
        try:
            # Bedrock Knowledge Base에서 문서 검색
            documents = self.bedrock_client.retrieve_documents(query, max_results)

            if not documents:
                logger.info("검색된 도메인 지식이 없습니다")
                return []

            logger.info(f"도메인 지식 검색 완료: {len(documents)}개 문서")
            return documents

        except Exception as e:
            logger.error(f"도메인 지식 검색 실패: {e}")
            return []

    def generate_with_rag(
        self,
        prompt: str,
        domain_context: str,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """RAG 기반 텍스트 생성"""
        try:
            # 1. 도메인 관련 문서 검색
            retrieved_docs = self.retrieve_domain_knowledge(domain_context, max_results=5)

            # 2. 검색된 문서를 컨텍스트로 추가
            context_texts = []
            for doc in retrieved_docs:
                if doc['content']:
                    context_texts.append(doc['content'][:500])  # 각 문서에서 최대 500자

            context = "\n\n".join(context_texts) if context_texts else ""

            # 3. 컨텍스트와 함께 생성
            full_prompt = prompt
            if context:
                full_prompt = f"""다음 도메인 지식을 참고하여 답변하세요:

=== 도메인 지식 ===
{context}

=== 요청 ===
{prompt}
"""

            response_text = self.bedrock_client.invoke_model(full_prompt, max_tokens)

            return {
                "generated_text": response_text,
                "context_used": context,
                "source_documents": retrieved_docs,
                "context_length": len(context),
                "has_domain_knowledge": len(context) > 0
            }

        except Exception as e:
            logger.error(f"RAG 생성 실패: {e}")
            # 실패시 일반 생성으로 대체
            try:
                response_text = self.bedrock_client.invoke_model(prompt, max_tokens)
                return {
                    "generated_text": response_text,
                    "context_used": "",
                    "source_documents": [],
                    "context_length": 0,
                    "has_domain_knowledge": False
                }
            except:
                raise e

    def generate_persona_with_context(
        self,
        cluster_info: Dict[str, Any],
        scenario: str,
        domain: str,
        knowledge_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """컨텍스트를 활용한 페르소나 생성"""
        try:
            # 도메인 컨텍스트 구성
            domain_query = f"{domain} 도메인의 {scenario} 상황에서의 사용자 특성과 행동 패턴"

            # 페르소나 생성 프롬프트 구성
            cluster_id = cluster_info.get("cluster_id", 0)
            cluster_size = cluster_info.get("size", 0)
            cluster_percentage = cluster_info.get("percentage", 0)
            cluster_characteristics = cluster_info.get("characteristics", {})

            prompt = self._build_persona_prompt(
                cluster_id, cluster_size, cluster_percentage,
                cluster_characteristics, scenario, domain, knowledge_summary
            )

            # RAG 기반 생성
            rag_result = self.generate_with_rag(prompt, domain_query)

            # 생성된 텍스트에서 페르소나 데이터 추출
            persona_data = self._parse_persona_response(
                rag_result["generated_text"], cluster_id, scenario
            )

            # 신뢰도 점수 계산
            confidence_score = self._calculate_confidence_score(
                rag_result, cluster_info
            )

            return {
                "persona_data": persona_data,
                "confidence_score": confidence_score,
                "rag_context": rag_result["context_used"],
                "source_documents": rag_result["source_documents"],
                "has_domain_knowledge": rag_result["has_domain_knowledge"]
            }

        except Exception as e:
            logger.error(f"RAG 페르소나 생성 실패: {e}")
            # 실패시 기본 페르소나 생성
            return self._create_fallback_persona_result(cluster_info, scenario, domain)

    def _build_persona_prompt(
        self,
        cluster_id: int,
        cluster_size: int,
        cluster_percentage: float,
        characteristics: Dict[str, Any],
        scenario: str,
        domain: str,
        knowledge_summary: Dict[str, Any]
    ) -> str:
        """페르소나 생성 프롬프트 구성"""

        # 시나리오별 설명
        scenario_descriptions = {
            "normal": "평상시의 일반적인 생활 패턴을 보이는",
            "stress": "업무나 개인적 문제로 스트레스를 받고 있는",
            "economic_difficulty": "경제적 어려움을 겪고 있는",
            "health_issue": "건강 문제나 컨디션 난조를 겪고 있는",
            "social_isolation": "외로움이나 사회적 고립을 경험하고 있는"
        }

        scenario_desc = scenario_descriptions.get(scenario, "일반적인")

        # 클러스터 특성 설명
        feature_descriptions = []
        for feature, stats in characteristics.items():
            if isinstance(stats, dict) and "mean" in stats:
                mean_val = stats["mean"]
                feature_descriptions.append(f"- {feature}: 평균 {mean_val:.2f}")

        feature_desc = "\n".join(feature_descriptions[:5]) if feature_descriptions else "특성 정보 없음"

        prompt = f"""다음 데이터 분석 결과를 바탕으로 현실적이고 구체적인 페르소나를 생성해주세요.

## 클러스터 정보
- 클러스터 ID: {cluster_id}
- 클러스터 크기: {cluster_size}명 (전체의 {cluster_percentage:.1f}%)
- 도메인: {domain}

## 주요 특성
{feature_desc}

## 생성할 페르소나 유형
{scenario_desc} 상황의 페르소나를 생성해주세요.

## 지식 기반 정보
- 처리된 파일 수: {knowledge_summary.get('files_processed', 0)}개
- 총 콘텐츠 길이: {knowledge_summary.get('total_content_length', 0)} 문자

## 요구사항
다음 JSON 형식으로 한국적 맥락에 맞는 현실적인 페르소나를 생성해주세요:

```json
{{
  "name": "한국식 이름",
  "age": 나이,
  "gender": "male 또는 female",
  "occupation": "직업",
  "location": "거주 지역",
  "family_status": "가족 상황",
  "living_situation": "생활 상황 (2-3문장)",
  "characteristics": ["특성1", "특성2", "특성3", "특성4", "특성5"],
  "needs": ["필요사항1", "필요사항2", "필요사항3"],
  "behavioral_patterns": {{
    "생활패턴": "구체적인 설명",
    "소비패턴": "구체적인 설명",
    "디지털이용": "구체적인 설명"
  }},
  "domain_insights": ["도메인별 인사이트1", "인사이트2", "인사이트3"],
  "challenges": ["{scenario} 상황에서의 구체적 어려움들"],
  "goals": ["이 페르소나의 목표나 바램들"]
}}
```

페르소나는 반드시 데이터 분석 결과와 일치하는 특성을 가져야 하며, {scenario_desc} 상황의 현실적인 어려움과 니즈를 반영해야 합니다."""

        return prompt

    def _parse_persona_response(self, response_text: str, cluster_id: int, scenario: str) -> Dict[str, Any]:
        """생성된 페르소나 응답 파싱"""
        try:
            # JSON 추출 시도
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                persona_data = json.loads(json_text)

                # 필수 필드 검증 및 기본값 설정
                required_fields = {
                    "name": f"페르소나_{cluster_id}_{scenario}",
                    "age": 30,
                    "gender": "male",
                    "occupation": "일반직",
                    "location": "서울",
                    "family_status": "1인 가구",
                    "living_situation": "일반적인 생활 패턴",
                    "characteristics": ["데이터 기반 특성"],
                    "needs": ["기본적인 니즈"],
                    "behavioral_patterns": {"생활패턴": "일반적"},
                    "domain_insights": ["데이터 분석 기반"],
                    "challenges": [f"{scenario} 관련 어려움"],
                    "goals": ["개선된 생활"]
                }

                for field, default_value in required_fields.items():
                    if field not in persona_data or not persona_data[field]:
                        persona_data[field] = default_value

                return persona_data

            else:
                logger.warning("JSON 형식을 찾을 수 없습니다")
                return self._create_basic_persona_data(cluster_id, scenario)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON 파싱 실패: {e}")
            return self._create_basic_persona_data(cluster_id, scenario)

    def _create_basic_persona_data(self, cluster_id: int, scenario: str) -> Dict[str, Any]:
        """기본 페르소나 데이터 생성"""
        names = ["김민수", "이지영", "박준호", "최수진", "정다은", "오성민", "한예림", "윤서연"]
        occupations = ["직장인", "프리랜서", "학생", "자영업자", "전문직", "서비스직"]

        return {
            "name": names[cluster_id % len(names)],
            "age": 25 + (cluster_id * 7) % 35,
            "gender": "female" if cluster_id % 2 == 0 else "male",
            "occupation": occupations[cluster_id % len(occupations)],
            "location": "서울",
            "family_status": "1인 가구",
            "living_situation": f"클러스터 {cluster_id}의 {scenario} 상황 대표 프로필",
            "characteristics": [
                f"클러스터 {cluster_id} 특성",
                f"{scenario} 상황 경험",
                "데이터 기반 프로필",
                "통계적 패턴 반영"
            ],
            "needs": [
                f"{scenario} 상황 개선",
                "맞춤형 서비스",
                "효과적인 솔루션"
            ],
            "behavioral_patterns": {
                "생활패턴": f"클러스터 {cluster_id}의 일반적 패턴",
                "소비패턴": "데이터 기반 소비 성향",
                "디지털이용": "평균적 디지털 활용"
            },
            "domain_insights": [
                f"클러스터 {cluster_id} 도메인 특성",
                "데이터 분석 기반 인사이트"
            ],
            "challenges": [f"{scenario} 상황의 구체적 어려움"],
            "goals": ["상황 개선", "더 나은 생활"]
        }

    def _calculate_confidence_score(
        self,
        rag_result: Dict[str, Any],
        cluster_info: Dict[str, Any]
    ) -> float:
        """페르소나 신뢰도 점수 계산"""
        try:
            score = 0.5  # 기본 점수

            # 도메인 지식 사용 여부
            if rag_result.get("has_domain_knowledge", False):
                score += 0.2

            # 컨텍스트 길이
            context_length = rag_result.get("context_length", 0)
            if context_length > 100:
                score += 0.2

            # 소스 문서 개수
            source_docs = len(rag_result.get("source_documents", []))
            if source_docs > 0:
                score += min(0.2, source_docs * 0.05)

            # 클러스터 크기 (더 큰 클러스터일수록 신뢰도 높음)
            cluster_size = cluster_info.get("size", 0)
            if cluster_size > 100:
                score += 0.1

            return min(1.0, score)

        except:
            return 0.5

    def _create_fallback_persona_result(
        self,
        cluster_info: Dict[str, Any],
        scenario: str,
        domain: str
    ) -> Dict[str, Any]:
        """페르소나 생성 실패시 대체 결과"""
        cluster_id = cluster_info.get("cluster_id", 0)
        basic_data = self._create_basic_persona_data(cluster_id, scenario)

        return {
            "persona_data": basic_data,
            "confidence_score": 0.3,  # 낮은 신뢰도
            "rag_context": "",
            "source_documents": [],
            "has_domain_knowledge": False
        }


# 편의를 위한 전역 인스턴스
rag_engine = RAGEngine()