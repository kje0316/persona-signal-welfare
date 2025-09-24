"""
데이터 증강 통합 파이프라인
전체 증강 프로세스를 관리하는 메인 파이프라인
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from ..common.database import db_manager
from ..data_analysis.data_ingestion import DataIngestionService
from ..persona_engine.persona_generator import PersonaGenerator
from .augmenter import PersonaBasedAugmenter
from .evaluator import AugmentationEvaluator

logger = logging.getLogger(__name__)


class DataAugmentationPipeline:
    """데이터 증강 통합 파이프라인"""

    def __init__(self):
        self.data_ingestion = DataIngestionService()
        self.persona_generator = PersonaGenerator()
        self.augmenter = PersonaBasedAugmenter()
        self.evaluator = AugmentationEvaluator()

        self.pipeline_results = {}
        self.task_id = None

    def run_complete_pipeline(
        self,
        structured_data_path: str,
        knowledge_file_paths: List[str],
        output_dir: str,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """전체 데이터 증강 파이프라인 실행"""
        try:
            # 기본 설정
            if config is None:
                config = {}

            self.task_id = config.get('task_id', f"augmentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"데이터 증강 파이프라인 시작: {self.task_id}")

            pipeline_results = {
                "task_id": self.task_id,
                "started_at": datetime.now().isoformat(),
                "config": config,
                "input_files": {
                    "structured_data": structured_data_path,
                    "knowledge_files": knowledge_file_paths
                },
                "output_directory": str(output_dir),
                "pipeline_stages": {}
            }

            # 1. 정형 데이터 처리 및 RDS 저장
            logger.info("1단계: 정형 데이터 처리 및 저장")
            ingestion_result = self._process_structured_data(structured_data_path)
            pipeline_results["pipeline_stages"]["data_ingestion"] = ingestion_result

            # 2. 페르소나 생성 (클러스터링 + RAG)
            logger.info("2단계: 페르소나 생성")
            personas_result = self._generate_personas(
                ingestion_result, knowledge_file_paths, config
            )
            pipeline_results["pipeline_stages"]["persona_generation"] = {
                "success": True,
                "personas_count": personas_result["personas_count"],
                "clustering_info": personas_result["clustering_info"]
            }

            # 3. 데이터 증강
            logger.info("3단계: 데이터 증강")
            augmentation_result = self._perform_augmentation(
                ingestion_result["table_name"],
                personas_result["personas"],
                config
            )
            pipeline_results["pipeline_stages"]["data_augmentation"] = augmentation_result

            # 4. 품질 평가
            logger.info("4단계: 품질 평가")
            evaluation_result = self._evaluate_augmentation(
                ingestion_result["table_name"],
                augmentation_result["augmented_table_name"],
                config
            )
            pipeline_results["pipeline_stages"]["evaluation"] = evaluation_result

            # 5. 결과 파일 생성
            logger.info("5단계: 결과 파일 생성")
            output_files = self._generate_output_files(
                output_dir, personas_result, augmentation_result, evaluation_result
            )
            pipeline_results["output_files"] = output_files

            # 파이프라인 완료
            pipeline_results["completed_at"] = datetime.now().isoformat()
            pipeline_results["status"] = "completed"
            pipeline_results["success"] = True

            # 전체 결과 요약
            pipeline_results["summary"] = self._generate_pipeline_summary(pipeline_results)

            self.pipeline_results = pipeline_results
            logger.info(f"데이터 증강 파이프라인 완료: {self.task_id}")

            return pipeline_results

        except Exception as e:
            logger.error(f"데이터 증강 파이프라인 실패: {e}")
            error_result = {
                "task_id": self.task_id,
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            }
            self.pipeline_results = error_result
            raise

    def _process_structured_data(self, file_path: str) -> Dict[str, Any]:
        """정형 데이터 처리"""
        try:
            logger.info(f"정형 데이터 처리: {file_path}")
            result = self.data_ingestion.process_structured_data(self.task_id, file_path)
            logger.info(f"데이터 처리 완료: {result['table_name']}")
            return result
        except Exception as e:
            logger.error(f"정형 데이터 처리 실패: {e}")
            raise

    def _generate_personas(
        self,
        ingestion_result: Dict[str, Any],
        knowledge_file_paths: List[str],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """페르소나 생성"""
        try:
            table_name = ingestion_result["table_name"]
            metadata = ingestion_result["metadata"]

            scenario = config.get("scenario", "normal")
            domain = metadata.get("estimated_domain", "general")

            logger.info(f"페르소나 생성: 시나리오={scenario}, 도메인={domain}")

            personas_result = self.persona_generator.generate_complete_personas(
                task_id=self.task_id,
                table_name=table_name,
                dataset_metadata=metadata,
                knowledge_file_paths=knowledge_file_paths,
                scenario=scenario,
                domain=domain
            )

            logger.info(f"페르소나 생성 완료: {len(personas_result['personas'])}개")
            return personas_result

        except Exception as e:
            logger.error(f"페르소나 생성 실패: {e}")
            raise

    def _perform_augmentation(
        self,
        original_table_name: str,
        personas: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """데이터 증강 수행"""
        try:
            # 원본 데이터 로드 (클러스터링된 버전)
            clustered_table_name = f"{original_table_name}_clustered"
            original_data = db_manager.load_dataframe_from_table(clustered_table_name)

            if original_data.empty:
                raise Exception(f"클러스터링된 데이터를 찾을 수 없습니다: {clustered_table_name}")

            # 증강 설정
            target_samples = config.get("target_samples", len(original_data) * 2)
            strategies = config.get("augmentation_strategies", ["interpolation", "noise_addition", "pattern_variation"])

            logger.info(f"데이터 증강: {target_samples}개 샘플 생성 목표")

            # 증강 수행
            augmented_data = self.augmenter.augment_data_from_personas(
                original_data, personas, target_samples, strategies
            )

            # 증강된 데이터를 RDS에 저장
            augmented_table_name = f"{original_table_name}_augmented"
            success = db_manager.save_dataframe_to_table(augmented_data, augmented_table_name)

            if not success:
                raise Exception("증강된 데이터 저장 실패")

            result = {
                "success": True,
                "augmented_samples": len(augmented_data),
                "augmented_table_name": augmented_table_name,
                "strategies_used": strategies,
                "target_samples": target_samples
            }

            logger.info(f"데이터 증강 완료: {len(augmented_data)}개 샘플")
            return result

        except Exception as e:
            logger.error(f"데이터 증강 실패: {e}")
            raise

    def _evaluate_augmentation(
        self,
        original_table_name: str,
        augmented_table_name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """증강 품질 평가"""
        try:
            # 데이터 로드
            original_data = db_manager.load_dataframe_from_table(f"{original_table_name}_clustered")
            augmented_data = db_manager.load_dataframe_from_table(augmented_table_name)

            # 타겟 컬럼 설정
            target_columns = config.get("target_columns", [])

            logger.info(f"품질 평가: 원본 {len(original_data)}개, 증강 {len(augmented_data)}개")

            # 평가 수행
            evaluation_result = self.evaluator.evaluate_augmentation_quality(
                original_data, augmented_data, target_columns
            )

            result = {
                "success": True,
                "overall_quality_score": evaluation_result["overall_quality_score"],
                "statistical_comparison_count": len(evaluation_result["statistical_comparison"]),
                "distribution_analysis_count": len(evaluation_result["distribution_analysis"]),
                "has_model_performance": len(evaluation_result["model_performance"]) > 0
            }

            logger.info(f"품질 평가 완료: 전체 점수 {evaluation_result['overall_quality_score']:.3f}")
            return result

        except Exception as e:
            logger.error(f"품질 평가 실패: {e}")
            raise

    def _generate_output_files(
        self,
        output_dir: Path,
        personas_result: Dict[str, Any],
        augmentation_result: Dict[str, Any],
        evaluation_result: Dict[str, Any]
    ) -> Dict[str, str]:
        """출력 파일들 생성"""
        try:
            output_files = {}

            # 1. 페르소나 JSON 저장
            personas_file = output_dir / f"{self.task_id}_personas.json"
            self.persona_generator.save_personas_to_json(personas_result, str(personas_file))
            output_files["personas"] = str(personas_file)

            # 2. 증강된 데이터 CSV 저장
            augmented_table = augmentation_result["augmented_table_name"]
            augmented_data = db_manager.load_dataframe_from_table(augmented_table)
            augmented_file = output_dir / f"{self.task_id}_augmented_data.csv"
            augmented_data.to_csv(augmented_file, index=False, encoding='utf-8')
            output_files["augmented_data"] = str(augmented_file)

            # 3. 평가 리포트 생성
            report_file = output_dir / f"{self.task_id}_evaluation_report.txt"
            evaluation_report = self.evaluator.generate_evaluation_report(str(report_file))
            output_files["evaluation_report"] = str(report_file)

            # 4. 평가 결과 JSON 저장
            evaluation_json_file = output_dir / f"{self.task_id}_evaluation_results.json"
            self.evaluator.save_evaluation_results(str(evaluation_json_file))
            output_files["evaluation_results"] = str(evaluation_json_file)

            # 5. 페르소나 요약 텍스트 저장
            summary_file = output_dir / f"{self.task_id}_personas_summary.txt"
            personas_summary = self.persona_generator.get_persona_summary(personas_result)
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(personas_summary)
            output_files["personas_summary"] = str(summary_file)

            logger.info(f"출력 파일 생성 완료: {len(output_files)}개 파일")
            return output_files

        except Exception as e:
            logger.error(f"출력 파일 생성 실패: {e}")
            raise

    def _generate_pipeline_summary(self, pipeline_results: Dict[str, Any]) -> Dict[str, Any]:
        """파이프라인 실행 요약 생성"""
        try:
            stages = pipeline_results.get("pipeline_stages", {})

            summary = {
                "execution_time": self._calculate_execution_time(
                    pipeline_results.get("started_at"),
                    pipeline_results.get("completed_at")
                ),
                "data_processing": {
                    "original_samples": stages.get("data_ingestion", {}).get("processed_shape", [0, 0])[0],
                    "augmented_samples": stages.get("data_augmentation", {}).get("augmented_samples", 0)
                },
                "persona_generation": {
                    "personas_created": stages.get("persona_generation", {}).get("personas_count", 0),
                    "clusters_identified": stages.get("persona_generation", {}).get("clustering_info", {}).get("optimal_clusters", 0)
                },
                "quality_assessment": {
                    "overall_quality_score": stages.get("evaluation", {}).get("overall_quality_score", 0),
                    "has_performance_improvement": stages.get("evaluation", {}).get("has_model_performance", False)
                },
                "success_rate": self._calculate_success_rate(stages)
            }

            return summary

        except Exception as e:
            logger.error(f"파이프라인 요약 생성 실패: {e}")
            return {"error": str(e)}

    def _calculate_execution_time(self, start_time: str, end_time: str) -> str:
        """실행 시간 계산"""
        try:
            if not start_time or not end_time:
                return "unknown"

            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            duration = end - start

            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            if hours > 0:
                return f"{hours}시간 {minutes}분 {seconds}초"
            elif minutes > 0:
                return f"{minutes}분 {seconds}초"
            else:
                return f"{seconds}초"

        except Exception:
            return "unknown"

    def _calculate_success_rate(self, stages: Dict[str, Any]) -> float:
        """성공률 계산"""
        try:
            total_stages = len(stages)
            successful_stages = sum(1 for stage in stages.values() if stage.get("success", False))
            return successful_stages / total_stages if total_stages > 0 else 0
        except Exception:
            return 0.0

    def save_pipeline_results(self, output_path: str):
        """파이프라인 결과를 JSON 파일로 저장"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.pipeline_results, f, ensure_ascii=False, indent=2)
            logger.info(f"파이프라인 결과 저장 완료: {output_path}")
        except Exception as e:
            logger.error(f"파이프라인 결과 저장 실패: {e}")
            raise

    def get_pipeline_status(self) -> Dict[str, Any]:
        """현재 파이프라인 상태 반환"""
        if not self.pipeline_results:
            return {"status": "not_started"}

        return {
            "task_id": self.pipeline_results.get("task_id"),
            "status": self.pipeline_results.get("status", "unknown"),
            "started_at": self.pipeline_results.get("started_at"),
            "completed_at": self.pipeline_results.get("completed_at"),
            "current_stage": self._get_current_stage(),
            "success_rate": self.pipeline_results.get("summary", {}).get("success_rate", 0)
        }

    def _get_current_stage(self) -> str:
        """현재 진행 중인 단계 확인"""
        if not self.pipeline_results or "pipeline_stages" not in self.pipeline_results:
            return "not_started"

        stages = self.pipeline_results["pipeline_stages"]
        stage_order = ["data_ingestion", "persona_generation", "data_augmentation", "evaluation"]

        for stage in stage_order:
            if stage not in stages:
                return stage
            if not stages[stage].get("success", False):
                return f"{stage}_failed"

        return "completed"


# 편의를 위한 전역 인스턴스
augmentation_pipeline = DataAugmentationPipeline()