"""
통합 페르소나 생성 엔진 - RDS/RAG 시스템 통합
클러스터링된 데이터와 도메인 지식을 활용한 현실적인 페르소나 생성
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..common.database import db_manager
from ..data_analysis.enhanced_clustering import EnhancedClusteringEngine
from .rag_engine import RAGEngine

logger = logging.getLogger(__name__)


class PersonaGenerator:
    """RDS/RAG 통합 페르소나 생성 엔진"""

    def __init__(self):
        self.clustering_engine = EnhancedClusteringEngine()
        self.rag_engine = RAGEngine()
        self.knowledge_uploaded = False

    def upload_knowledge_base(self, task_id: str, knowledge_file_paths: List[str]) -> Dict[str, Any]:
        """도메인 지식 파일을 S3에 업로드하고 Knowledge Base 준비"""
        try:
            logger.info(f"지식 기반 업로드 시작: {task_id}")

            upload_result = self.rag_engine.upload_knowledge_base(task_id, knowledge_file_paths)

            if upload_result["success_count"] > 0:
                self.knowledge_uploaded = True
                logger.info("지식 기반 업로드 및 활성화 완료")

            return upload_result

        except Exception as e:
            logger.error(f"지식 기반 업로드 실패: {e}")
            raise

    def perform_clustering_analysis(
        self,
        task_id: str,
        table_name: str,
        dataset_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """RDS 데이터를 사용한 클러스터링 분석"""
        try:
            logger.info(f"클러스터링 분석 시작: {task_id}")

            clustering_results = self.clustering_engine.perform_clustering(
                task_id, table_name, dataset_metadata
            )

            logger.info(f"클러스터링 완료: {clustering_results['optimal_k']}개 클러스터")
            return clustering_results

        except Exception as e:
            logger.error(f"클러스터링 분석 실패: {e}")
            raise

    def generate_personas_from_clusters(
        self,
        clustering_results: Dict[str, Any],
        scenario: str,
        domain: str,
        knowledge_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """클러스터링 결과를 기반으로 페르소나 생성"""
        try:
            logger.info("페르소나 생성 시작")
            personas = []

            cluster_analysis = clustering_results.get("cluster_analysis", {})

            for cluster_key, cluster_info in cluster_analysis.items():
                logger.info(f"클러스터 {cluster_info['cluster_id']} 페르소나 생성 중...")

                # RAG를 활용한 페르소나 생성
                persona_result = self.rag_engine.generate_persona_with_context(
                    cluster_info, scenario, domain, knowledge_summary
                )

                # 클러스터 정보 추가
                persona_data = persona_result["persona_data"]
                persona_data.update({
                    "cluster_info": {
                        "cluster_id": cluster_info["cluster_id"],
                        "cluster_size": cluster_info["size"],
                        "cluster_percentage": cluster_info["percentage"]
                    },
                    "generation_metadata": {
                        "confidence_score": persona_result["confidence_score"],
                        "has_domain_knowledge": persona_result["has_domain_knowledge"],
                        "rag_context_length": len(persona_result["rag_context"]),
                        "source_documents_count": len(persona_result["source_documents"]),
                        "scenario": scenario,
                        "domain": domain,
                        "generated_at": datetime.now().isoformat()
                    }
                })

                personas.append(persona_data)
                logger.info(f"페르소나 '{persona_data['name']}' 생성 완료")

            logger.info(f"총 {len(personas)}개 페르소나 생성 완료")
            return personas

        except Exception as e:
            logger.error(f"페르소나 생성 실패: {e}")
            raise

    def generate_complete_personas(
        self,
        task_id: str,
        table_name: str,
        dataset_metadata: Dict[str, Any],
        knowledge_file_paths: List[str],
        scenario: str = "normal",
        domain: str = "general"
    ) -> Dict[str, Any]:
        """전체 페르소나 생성 파이프라인"""
        try:
            logger.info(f"통합 페르소나 생성 파이프라인 시작: {task_id}")

            # 1. 도메인 지식 업로드
            knowledge_result = self.upload_knowledge_base(task_id, knowledge_file_paths)

            # 2. 클러스터링 수행
            clustering_results = self.perform_clustering_analysis(
                task_id, table_name, dataset_metadata
            )

            # 3. 페르소나 생성
            personas = self.generate_personas_from_clusters(
                clustering_results,
                scenario,
                domain,
                knowledge_result["knowledge_summary"]
            )

            # 4. 결과 통합
            complete_result = {
                "task_id": task_id,
                "status": "completed",
                "generated_at": datetime.now().isoformat(),

                "clustering_info": {
                    "optimal_clusters": clustering_results["optimal_k"],
                    "total_samples": clustering_results["total_samples"],
                    "feature_count": clustering_results["feature_info"]["feature_count"]
                },

                "knowledge_base_info": {
                    "files_processed": knowledge_result["knowledge_summary"].get("files_processed", 0),
                    "total_content_length": knowledge_result["knowledge_summary"].get("total_content_length", 0),
                    "upload_success_count": knowledge_result["success_count"]
                },

                "personas": personas,
                "personas_count": len(personas),

                "generation_config": {
                    "scenario": scenario,
                    "domain": domain
                }
            }

            logger.info(f"통합 페르소나 생성 완료: {len(personas)}개 페르소나")
            return complete_result

        except Exception as e:
            logger.error(f"통합 페르소나 생성 실패: {e}")
            raise

    def save_personas_to_json(self, personas_result: Dict[str, Any], output_path: str):
        """생성된 페르소나를 JSON 파일로 저장"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(personas_result, f, ensure_ascii=False, indent=2)

            logger.info(f"페르소나 결과 저장 완료: {output_path}")

        except Exception as e:
            logger.error(f"페르소나 저장 실패: {e}")
            raise

    def get_persona_summary(self, personas_result: Dict[str, Any]) -> str:
        """페르소나 생성 결과 요약"""
        try:
            summary_lines = [
                f"📊 페르소나 생성 결과 요약 - {personas_result['task_id']}",
                f"생성 시각: {personas_result['generated_at']}",
                "",
                f"🔍 클러스터링 정보:",
                f"  - 최적 클러스터 수: {personas_result['clustering_info']['optimal_clusters']}개",
                f"  - 분석 샘플 수: {personas_result['clustering_info']['total_samples']}개",
                f"  - 사용 특성 수: {personas_result['clustering_info']['feature_count']}개",
                "",
                f"📚 지식 기반 정보:",
                f"  - 처리된 파일 수: {personas_result['knowledge_base_info']['files_processed']}개",
                f"  - 총 콘텐츠 길이: {personas_result['knowledge_base_info']['total_content_length']:,} 문자",
                "",
                f"👥 생성된 페르소나 ({personas_result['personas_count']}개):"
            ]

            for i, persona in enumerate(personas_result['personas'], 1):
                cluster_info = persona['cluster_info']
                generation_meta = persona['generation_metadata']

                summary_lines.extend([
                    f"  {i}. {persona['name']} ({persona['age']}세, {persona['gender']})",
                    f"     직업: {persona['occupation']}, 거주지: {persona['location']}",
                    f"     클러스터: {cluster_info['cluster_id']} (크기: {cluster_info['cluster_size']}명, {cluster_info['cluster_percentage']:.1f}%)",
                    f"     신뢰도: {generation_meta['confidence_score']:.2f}",
                    f"     주요 니즈: {', '.join(persona['needs'][:3])}",
                    ""
                ])

            return "\n".join(summary_lines)

        except Exception as e:
            logger.error(f"페르소나 요약 생성 실패: {e}")
            return f"요약 생성 실패: {str(e)}"


# 편의를 위한 전역 인스턴스
persona_generator = PersonaGenerator()