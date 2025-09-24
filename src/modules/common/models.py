"""
데이터 모델 정의
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class TaskStatus(str, Enum):
    """작업 상태"""
    PENDING = "pending"
    UPLOADING = "uploading"
    ANALYZING = "analyzing"
    CLUSTERING = "clustering"
    GENERATING_PERSONAS = "generating_personas"
    AUGMENTING = "augmenting"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


class ScenarioType(str, Enum):
    """시나리오 타입"""
    NORMAL = "normal"
    STRESS = "stress"
    ECONOMIC_DIFFICULTY = "economic_difficulty"
    HEALTH_ISSUE = "health_issue"
    SOCIAL_ISOLATION = "social_isolation"


# Pydantic 모델들
class TaskCreateRequest(BaseModel):
    """작업 생성 요청"""
    task_name: str = Field(..., description="작업 이름")
    description: Optional[str] = Field(None, description="작업 설명")


class TaskStatusResponse(BaseModel):
    """작업 상태 응답"""
    task_id: str
    task_name: str
    status: TaskStatus
    progress: float = Field(0, ge=0, le=100)
    message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class ClusterInfo(BaseModel):
    """클러스터 정보"""
    cluster_id: int
    size: int
    percentage: float
    characteristics: Dict[str, Any]
    dominant_features: List[str]


class PersonaModel(BaseModel):
    """페르소나 모델"""
    persona_id: str
    name: str
    age: int
    gender: str
    cluster_id: int
    scenario: ScenarioType
    occupation: Optional[str] = None
    location: Optional[str] = None
    family_status: Optional[str] = None
    living_situation: str
    characteristics: List[str]
    needs: List[str]
    behavioral_patterns: Dict[str, str]
    domain_insights: List[str]
    challenges: List[str]
    goals: List[str]
    confidence_score: float


class AugmentationResults(BaseModel):
    """데이터 증강 결과"""
    original_rows: int
    augmented_rows: int
    total_rows: int
    personas_generated: int
    performance_improvement: float
    quality_metrics: Dict[str, float]
    augmentation_time: float


# SQLAlchemy 모델들
class AugmentationTask(Base):
    """데이터 증강 작업 테이블"""
    __tablename__ = "augmentation_tasks"

    id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default=TaskStatus.PENDING)
    progress = Column(Float, default=0.0)
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 파일 정보
    structured_data_path = Column(String(500))
    knowledge_files_paths = Column(JSON)

    # 결과 정보
    clusters_info = Column(JSON)
    personas = Column(JSON)
    results = Column(JSON)
    error_message = Column(Text)


class DatasetMetadata(Base):
    """데이터셋 메타데이터 테이블"""
    __tablename__ = "dataset_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, nullable=False)
    table_name = Column(String(255), nullable=False)

    # 데이터 정보
    total_rows = Column(Integer)
    total_columns = Column(Integer)
    column_types = Column(JSON)
    missing_values = Column(JSON)
    basic_stats = Column(JSON)
    estimated_domain = Column(String(100))

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GeneratedPersona(Base):
    """생성된 페르소나 테이블"""
    __tablename__ = "generated_personas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, nullable=False)
    persona_id = Column(String(100), nullable=False)

    # 페르소나 정보
    name = Column(String(100))
    age = Column(Integer)
    gender = Column(String(20))
    cluster_id = Column(Integer)
    scenario = Column(String(50))

    # 상세 정보
    characteristics = Column(JSON)
    needs = Column(JSON)
    behavioral_patterns = Column(JSON)
    domain_insights = Column(JSON)
    confidence_score = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())