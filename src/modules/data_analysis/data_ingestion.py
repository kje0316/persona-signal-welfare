"""
데이터 수집 및 전처리 서비스
CSV/Excel 파일을 RDS에 저장하고 메타데이터 관리
"""

import logging
import os
from typing import Optional, List, Dict, Any
from pathlib import Path

import pandas as pd
import numpy as np

from ..common.database import db_manager
from ..common.models import DatasetMetadata

logger = logging.getLogger(__name__)


class DataIngestionService:
    """데이터 수집 및 전처리 서비스"""

    def __init__(self):
        self.supported_formats = {'.csv', '.xlsx', '.xls'}

    def process_structured_data(
        self,
        task_id: str,
        file_path: str
    ) -> Dict[str, Any]:
        """정형 데이터 처리 및 RDS 저장"""
        try:
            # 파일 읽기
            df = self._load_dataframe(file_path)
            logger.info(f"원본 데이터 로드: {df.shape}")

            # 데이터 전처리
            df_processed = self._preprocess_dataframe(df)
            logger.info(f"전처리 후 데이터: {df_processed.shape}")

            # 테이블명 생성
            table_name = f"dataset_{task_id}"

            # RDS에 저장
            success = db_manager.save_dataframe_to_table(df_processed, table_name)
            if not success:
                raise Exception("데이터베이스 저장 실패")

            # 메타데이터 생성
            metadata = self._analyze_dataframe(df_processed)

            # 메타데이터를 RDS에 저장
            self._save_dataset_metadata(task_id, table_name, metadata)

            return {
                "table_name": table_name,
                "original_shape": df.shape,
                "processed_shape": df_processed.shape,
                "metadata": metadata,
                "file_path": file_path
            }

        except Exception as e:
            logger.error(f"정형 데이터 처리 실패: {e}")
            raise

    def _load_dataframe(self, file_path: str) -> pd.DataFrame:
        """파일에서 데이터프레임 로드"""
        file_ext = Path(file_path).suffix.lower()

        if file_ext == '.csv':
            # CSV 인코딩 자동 감지
            encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr', 'iso-8859-1']
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, low_memory=False)
                    logger.info(f"CSV 로드 성공 (인코딩: {encoding})")
                    return df
                except UnicodeDecodeError:
                    continue
            raise Exception("지원되지 않는 CSV 인코딩")

        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
            logger.info("Excel 파일 로드 성공")
            return df

        else:
            raise Exception(f"지원되지 않는 파일 형식: {file_ext}")

    def _preprocess_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터프레임 전처리"""
        df_clean = df.copy()

        # 1. 컬럼명 정리 (공백 제거, 특수문자 처리)
        df_clean.columns = df_clean.columns.str.strip()

        # 2. 중복 행 제거
        df_clean = df_clean.drop_duplicates()

        # 3. 완전히 빈 행/열 제거
        df_clean = df_clean.dropna(how='all')  # 모든 값이 NaN인 행 제거
        df_clean = df_clean.loc[:, ~df_clean.isnull().all()]  # 모든 값이 NaN인 열 제거

        # 4. 수치형 데이터 타입 최적화
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                # 숫자로 변환 가능한지 확인
                try:
                    numeric_series = pd.to_numeric(df_clean[col], errors='coerce')
                    if not numeric_series.isnull().all():
                        # 정수인지 실수인지 판단
                        if numeric_series.notna().all() or (numeric_series % 1 == 0).all():
                            df_clean[col] = numeric_series.astype('Int64')
                        else:
                            df_clean[col] = numeric_series.astype('float64')
                except:
                    pass

        # 5. 날짜형 데이터 감지 및 변환
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                try:
                    # 날짜 패턴 감지
                    sample = df_clean[col].dropna().head(10)
                    if len(sample) > 0:
                        converted = pd.to_datetime(sample, errors='coerce')
                        if converted.notna().sum() > len(sample) * 0.8:  # 80% 이상이 날짜로 변환됨
                            df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')
                except:
                    pass

        logger.info(f"전처리 완료: {len(df)} -> {len(df_clean)} 행")
        return df_clean

    def _analyze_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """데이터프레임 분석"""
        analysis = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "column_types": {},
            "missing_values": {},
            "basic_stats": {},
            "categorical_info": {},
            "numeric_info": {}
        }

        # 컬럼별 분석
        for col in df.columns:
            dtype = str(df[col].dtype)
            missing_count = df[col].isnull().sum()
            missing_rate = missing_count / len(df) * 100

            analysis["column_types"][col] = dtype
            analysis["missing_values"][col] = {
                "count": int(missing_count),
                "rate": float(missing_rate)
            }

            if pd.api.types.is_numeric_dtype(df[col]):
                # 수치형 컬럼
                stats = df[col].describe()
                analysis["numeric_info"][col] = {
                    "mean": float(stats["mean"]) if not pd.isna(stats["mean"]) else None,
                    "std": float(stats["std"]) if not pd.isna(stats["std"]) else None,
                    "min": float(stats["min"]) if not pd.isna(stats["min"]) else None,
                    "max": float(stats["max"]) if not pd.isna(stats["max"]) else None,
                    "q25": float(stats["25%"]) if not pd.isna(stats["25%"]) else None,
                    "q50": float(stats["50%"]) if not pd.isna(stats["50%"]) else None,
                    "q75": float(stats["75%"]) if not pd.isna(stats["75%"]) else None
                }
            elif df[col].dtype == 'object' or df[col].dtype.name == 'category':
                # 범주형 컬럼
                value_counts = df[col].value_counts().head(10)
                analysis["categorical_info"][col] = {
                    "unique_count": int(df[col].nunique()),
                    "top_values": {str(k): int(v) for k, v in value_counts.items()}
                }

        # 도메인 추정
        analysis["estimated_domain"] = self._estimate_domain(df)

        return analysis

    def _estimate_domain(self, df: pd.DataFrame) -> str:
        """데이터 도메인 추정"""
        column_names = [col.lower() for col in df.columns]
        all_text = " ".join(column_names)

        domain_keywords = {
            "healthcare": ["patient", "diagnosis", "treatment", "hospital", "disease", "symptom", "의료", "환자", "진료"],
            "finance": ["amount", "price", "cost", "revenue", "income", "payment", "금액", "수입", "지출", "매출"],
            "education": ["student", "grade", "score", "course", "학생", "성적", "점수", "과목"],
            "retail": ["product", "customer", "order", "sales", "구매", "판매", "상품", "고객"],
            "welfare": ["benefit", "support", "assistance", "service", "복지", "지원", "혜택", "서비스"],
            "telecom": ["call", "data", "usage", "통화", "데이터", "사용량", "이동"],
            "transportation": ["distance", "travel", "trip", "이동", "거리", "교통"],
            "demographics": ["age", "gender", "population", "나이", "성별", "인구", "가구"]
        }

        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in all_text)
            if score > 0:
                domain_scores[domain] = score

        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        else:
            return "general"

    def _save_dataset_metadata(self, task_id: str, table_name: str, metadata: Dict[str, Any]):
        """메타데이터를 데이터베이스에 저장"""
        try:
            with db_manager.get_sync_session() as session:
                metadata_record = DatasetMetadata(
                    task_id=task_id,
                    table_name=table_name,
                    total_rows=metadata["total_rows"],
                    total_columns=metadata["total_columns"],
                    column_types=metadata["column_types"],
                    missing_values=metadata["missing_values"],
                    basic_stats=metadata,
                    estimated_domain=metadata["estimated_domain"]
                )
                session.add(metadata_record)
                session.commit()
                logger.info(f"메타데이터 저장 완료: {task_id}")

        except Exception as e:
            logger.error(f"메타데이터 저장 실패: {e}")
            raise

    def prepare_knowledge_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """도메인 지식 파일들 준비"""
        knowledge_info = {
            "files": [],
            "total_files": len(file_paths),
            "total_size": 0
        }

        for file_path in file_paths:
            if os.path.exists(file_path):
                file_info = {
                    "path": file_path,
                    "filename": os.path.basename(file_path),
                    "size": os.path.getsize(file_path),
                    "extension": Path(file_path).suffix.lower()
                }
                knowledge_info["files"].append(file_info)
                knowledge_info["total_size"] += file_info["size"]

        logger.info(f"지식 파일 준비 완료: {len(knowledge_info['files'])}개 파일")
        return knowledge_info