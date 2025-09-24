# -*- coding: utf-8 -*-
"""
persona_api.py
AWS Bedrock 기반 페르소나 생성 FastAPI 서버 (EC2용)
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

# FastAPI 및 관련 패키지
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# AWS 및 환경 설정
import boto3
from botocore.exceptions import ClientError

# 페르소나 생성기
import sys
sys.path.append(str(Path(__file__).parent.parent))

try:
    from modules.persona_engine.bedrock_generator import BedrockPersonaGenerator
except ImportError as e:
    logging.error(f"페르소나 생성기 임포트 실패: {e}")
    BedrockPersonaGenerator = None

# 데이터 증강 엔진
try:
    from data_augmentation import data_aug_engine
except ImportError as e:
    logging.error(f"데이터 증강 엔진 임포트 실패: {e}")
    data_aug_engine = None

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/persona_api.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="PersonaGen API",
    description="AWS Bedrock 기반 1인가구 페르소나 생성 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정 (프론트엔드 연동을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용, 운영시에는 구체적 도메인 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수
persona_generator: Optional[BedrockPersonaGenerator] = None
generation_cache: Dict[str, Any] = {}
generation_tasks: Dict[str, Any] = {}

# Pydantic 모델들
class PersonaGenerationRequest(BaseModel):
    n_personas: int = Field(default=5, ge=1, le=20, description="생성할 페르소나 수 (1-20)")
    force_regenerate: bool = Field(default=False, description="캐시 무시하고 강제 재생성")
    use_clustering: bool = Field(default=True, description="클러스터링 기반 생성 여부")

class PersonaResponse(BaseModel):
    success: bool
    message: str
    data: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class SystemStatus(BaseModel):
    service_name: str = "PersonaGen API"
    status: str
    aws_region: str
    bedrock_available: bool
    cached_personas: int
    last_generation: Optional[str]
    uptime: str

# 데이터 증강 관련 모델들
class DataAugmentationTaskRequest(BaseModel):
    description: Optional[str] = Field(default="", description="분석 설명")

class DataAugmentationTaskResponse(BaseModel):
    success: bool
    task_id: str
    message: str
    status: str = "created"

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    message: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# 서버 시작 시간
SERVER_START_TIME = datetime.now()

@app.on_event("startup")
async def startup_event():
    """서버 시작시 초기화"""
    global persona_generator

    logger.info("🚀 PersonaGen API 서버 시작...")

    try:
        # AWS 리전 확인
        region = os.getenv('AWS_REGION', 'us-east-1')
        logger.info(f"AWS 리전: {region}")

        # AWS 크리덴셜 확인
        try:
            sts = boto3.client('sts', region_name=region)
            identity = sts.get_caller_identity()
            logger.info(f"AWS 계정 ID: {identity.get('Account', 'Unknown')}")
        except Exception as e:
            logger.warning(f"AWS 크리덴셜 확인 실패: {e}")

        # 페르소나 생성기 초기화
        if BedrockPersonaGenerator:
            persona_generator = BedrockPersonaGenerator(region_name=region)
            logger.info("✅ BedrockPersonaGenerator 초기화 완료")
        else:
            logger.error("❌ BedrockPersonaGenerator를 사용할 수 없음")

        # 헬스체크를 위한 더미 호출
        await health_check_internal()

        logger.info("✅ PersonaGen API 서버 시작 완료")

    except Exception as e:
        logger.error(f"❌ 서버 초기화 실패: {e}")
        # 서버는 계속 실행하되 오류 상태로 표시

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료시 정리"""
    logger.info("🔄 PersonaGen API 서버 종료 중...")
    # 진행 중인 작업들 정리
    for task_id in list(generation_tasks.keys()):
        task = generation_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
    logger.info("✅ 서버 종료 완료")

async def health_check_internal() -> Dict[str, Any]:
    """내부 헬스 체크"""
    try:
        # Bedrock 연결 테스트
        bedrock_ok = False
        if persona_generator:
            try:
                # 간단한 테스트 호출
                test_response = await persona_generator.call_bedrock_async(
                    "Hello, can you respond with just 'OK'?",
                    max_tokens=10
                )
                bedrock_ok = "OK" in test_response or len(test_response.strip()) > 0
            except Exception as e:
                logger.warning(f"Bedrock 헬스체크 실패: {e}")

        return {
            "persona_generator_available": persona_generator is not None,
            "bedrock_connection": bedrock_ok,
            "cache_size": len(generation_cache),
            "active_tasks": len([t for t in generation_tasks.values() if not t.done()]),
            "server_uptime": str(datetime.now() - SERVER_START_TIME)
        }
    except Exception as e:
        logger.error(f"헬스체크 오류: {e}")
        return {"error": str(e)}

# API 엔드포인트들

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "PersonaGen API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        health_data = await health_check_internal()

        region = os.getenv('AWS_REGION', 'us-east-1')

        return {
            "service_name": "PersonaGen API",
            "status": "healthy" if health_data.get("persona_generator_available") else "degraded",
            "aws_region": region,
            "bedrock_available": health_data.get("bedrock_connection", False),
            "cached_personas": len(generation_cache),
            "last_generation": max([v.get("generated_at", "") for v in generation_cache.values()]) if generation_cache else None,
            "uptime": health_data.get("server_uptime", "unknown"),
            "details": health_data
        }
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )

@app.post("/api/v1/personas/generate", response_model=PersonaResponse)
async def generate_personas(request: PersonaGenerationRequest, background_tasks: BackgroundTasks):
    """페르소나 생성 API"""

    if not persona_generator:
        raise HTTPException(
            status_code=503,
            detail="페르소나 생성기를 사용할 수 없습니다. 서버 설정을 확인해주세요."
        )

    try:
        # 캐시 키 생성
        cache_key = f"personas_{request.n_personas}_{request.use_clustering}"

        # 캐시 확인 (강제 재생성이 아닌 경우)
        if not request.force_regenerate and cache_key in generation_cache:
            cached_data = generation_cache[cache_key]
            cache_age = datetime.now() - datetime.fromisoformat(cached_data["generated_at"].replace('Z', '+00:00').replace('+00:00', ''))

            # 캐시가 1시간 이내인 경우 반환
            if cache_age.total_seconds() < 3600:
                logger.info(f"📦 캐시된 페르소나 반환: {request.n_personas}개")
                return PersonaResponse(
                    success=True,
                    message=f"캐시된 {request.n_personas}개 페르소나 반환",
                    data=cached_data["personas"],
                    metadata={
                        "cached": True,
                        "cache_age_minutes": int(cache_age.total_seconds() / 60),
                        "generation_method": cached_data.get("generation_method", "unknown")
                    }
                )

        # 새로운 페르소나 생성
        logger.info(f"🎭 새로운 페르소나 생성 요청: {request.n_personas}개")

        # 백그라운드에서 생성할 작업 ID
        task_id = f"generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 비동기 생성 시작
        generation_task = asyncio.create_task(
            generate_personas_async(request.n_personas, cache_key, task_id)
        )
        generation_tasks[task_id] = generation_task

        # 생성 완료 대기 (최대 60초)
        try:
            personas = await asyncio.wait_for(generation_task, timeout=60.0)

            # 성공시 캐시 저장
            generation_cache[cache_key] = {
                "personas": personas,
                "generated_at": datetime.now().isoformat(),
                "generation_method": "bedrock_async",
                "task_id": task_id
            }

            return PersonaResponse(
                success=True,
                message=f"{len(personas)}개 페르소나 생성 완료",
                data=personas,
                metadata={
                    "cached": False,
                    "generation_time": "< 60 seconds",
                    "task_id": task_id,
                    "bedrock_count": sum(1 for p in personas if p.get('generation_method') == 'bedrock_claude')
                }
            )

        except asyncio.TimeoutError:
            # 타임아웃시 백그라운드 계속 실행
            background_tasks.add_task(monitor_background_task, task_id, cache_key)

            return PersonaResponse(
                success=True,
                message="페르소나 생성이 백그라운드에서 진행중입니다",
                data=None,
                metadata={
                    "background_generation": True,
                    "task_id": task_id,
                    "check_endpoint": f"/api/v1/personas/status/{task_id}"
                }
            )

    except Exception as e:
        logger.error(f"❌ 페르소나 생성 실패: {e}")
        return PersonaResponse(
            success=False,
            message="페르소나 생성 중 오류 발생",
            error=str(e)
        )

async def generate_personas_async(n_personas: int, cache_key: str, task_id: str) -> List[Dict[str, Any]]:
    """비동기 페르소나 생성 작업"""
    try:
        personas = await persona_generator.generate_personas(n_personas)
        logger.info(f"✅ 백그라운드 페르소나 생성 완료: {len(personas)}개 (Task: {task_id})")
        return personas
    except Exception as e:
        logger.error(f"❌ 백그라운드 페르소나 생성 실패: {e}")
        raise

async def monitor_background_task(task_id: str, cache_key: str):
    """백그라운드 작업 모니터링"""
    try:
        task = generation_tasks.get(task_id)
        if task:
            personas = await task
            generation_cache[cache_key] = {
                "personas": personas,
                "generated_at": datetime.now().isoformat(),
                "generation_method": "bedrock_background",
                "task_id": task_id
            }
            logger.info(f"✅ 백그라운드 작업 완료: {task_id}")
    except Exception as e:
        logger.error(f"❌ 백그라운드 작업 실패: {task_id} - {e}")
    finally:
        # 작업 정리
        if task_id in generation_tasks:
            del generation_tasks[task_id]

@app.get("/api/v1/personas/status/{task_id}")
async def get_generation_status(task_id: str):
    """페르소나 생성 상태 확인"""
    try:
        # 완료된 작업인지 캐시에서 확인
        for cache_data in generation_cache.values():
            if cache_data.get("task_id") == task_id:
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "personas": cache_data["personas"],
                    "generated_at": cache_data["generated_at"]
                }

        # 진행중인 작업인지 확인
        if task_id in generation_tasks:
            task = generation_tasks[task_id]
            if task.done():
                if task.exception():
                    return {
                        "task_id": task_id,
                        "status": "failed",
                        "error": str(task.exception())
                    }
                else:
                    return {
                        "task_id": task_id,
                        "status": "completed_not_cached",
                        "message": "작업은 완료되었으나 결과를 찾을 수 없습니다"
                    }
            else:
                return {
                    "task_id": task_id,
                    "status": "running",
                    "message": "페르소나 생성이 진행 중입니다"
                }

        return {
            "task_id": task_id,
            "status": "not_found",
            "message": "해당 작업을 찾을 수 없습니다"
        }

    except Exception as e:
        logger.error(f"상태 확인 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/personas")
async def list_personas(use_cache: bool = Query(True, description="캐시된 페르소나 사용 여부")):
    """페르소나 목록 조회"""
    try:
        if use_cache and generation_cache:
            # 가장 최근 캐시 반환
            latest_cache = max(generation_cache.values(), key=lambda x: x["generated_at"])
            return PersonaResponse(
                success=True,
                message=f"캐시된 {len(latest_cache['personas'])}개 페르소나 반환",
                data=latest_cache["personas"],
                metadata={
                    "cached": True,
                    "generated_at": latest_cache["generated_at"]
                }
            )
        else:
            # 캐시가 없거나 사용하지 않는 경우
            return PersonaResponse(
                success=False,
                message="캐시된 페르소나가 없습니다. /api/v1/personas/generate를 사용해주세요",
                data=None
            )

    except Exception as e:
        logger.error(f"페르소나 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/personas/cache")
async def clear_cache():
    """캐시 초기화"""
    try:
        cache_size = len(generation_cache)
        generation_cache.clear()

        # 진행중인 작업들도 정리
        for task_id in list(generation_tasks.keys()):
            task = generation_tasks[task_id]
            if not task.done():
                task.cancel()
            del generation_tasks[task_id]

        return {
            "success": True,
            "message": f"{cache_size}개 캐시 항목과 진행중인 작업들을 정리했습니다"
        }
    except Exception as e:
        logger.error(f"캐시 정리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/system/metrics")
async def get_system_metrics():
    """시스템 메트릭"""
    try:
        health = await health_check_internal()

        # 캐시 통계
        cache_stats = {
            "total_cached_items": len(generation_cache),
            "cache_keys": list(generation_cache.keys()),
            "oldest_cache": min([v["generated_at"] for v in generation_cache.values()]) if generation_cache else None,
            "newest_cache": max([v["generated_at"] for v in generation_cache.values()]) if generation_cache else None
        }

        # 작업 통계
        task_stats = {
            "active_tasks": len([t for t in generation_tasks.values() if not t.done()]),
            "completed_tasks": len([t for t in generation_tasks.values() if t.done()]),
            "total_task_ids": list(generation_tasks.keys())
        }

        return {
            "system_health": health,
            "cache_statistics": cache_stats,
            "task_statistics": task_stats,
            "server_info": {
                "start_time": SERVER_START_TIME.isoformat(),
                "uptime": str(datetime.now() - SERVER_START_TIME),
                "aws_region": os.getenv('AWS_REGION', 'us-east-1')
            }
        }

    except Exception as e:
        logger.error(f"시스템 메트릭 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 데이터 증강 스튜디오 API들

@app.post("/api/v1/data-aug/upload-structured", response_model=Dict[str, Any])
async def upload_structured_data(file: UploadFile = File(...)):
    """정형 데이터 파일 업로드"""
    if not data_aug_engine:
        raise HTTPException(
            status_code=503,
            detail="데이터 증강 엔진을 사용할 수 없습니다"
        )

    try:
        # 파일 유효성 검사
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="지원되지 않는 파일 형식입니다. CSV 또는 Excel 파일을 업로드해주세요."
            )

        # 임시 파일로 저장
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"structured_{timestamp}_{file.filename}"
        file_path = upload_dir / filename

        # 파일 저장
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        logger.info(f"정형 데이터 업로드 완료: {filename}")

        return {
            "success": True,
            "message": "정형 데이터 업로드 완료",
            "filename": filename,
            "file_path": str(file_path),
            "size": len(content)
        }

    except Exception as e:
        logger.error(f"정형 데이터 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/data-aug/upload-knowledge", response_model=Dict[str, Any])
async def upload_knowledge_files(files: List[UploadFile] = File(...)):
    """도메인 지식 파일들 업로드"""
    if not data_aug_engine:
        raise HTTPException(
            status_code=503,
            detail="데이터 증강 엔진을 사용할 수 없습니다"
        )

    try:
        uploaded_files = []
        upload_dir = Path("uploads/knowledge")
        upload_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for file in files:
            if not file.filename.endswith(('.pdf', '.txt', '.md')):
                continue  # 지원되지 않는 파일은 스킵

            filename = f"knowledge_{timestamp}_{file.filename}"
            file_path = upload_dir / filename

            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            uploaded_files.append({
                "filename": filename,
                "file_path": str(file_path),
                "size": len(content)
            })

        logger.info(f"도메인 지식 파일 업로드 완료: {len(uploaded_files)}개")

        return {
            "success": True,
            "message": f"{len(uploaded_files)}개 도메인 지식 파일 업로드 완료",
            "files": uploaded_files
        }

    except Exception as e:
        logger.error(f"지식 파일 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/data-aug/start-analysis", response_model=DataAugmentationTaskResponse)
async def start_data_augmentation_analysis(
    structured_file_path: str,
    knowledge_files: List[str],
    background_tasks: BackgroundTasks
):
    """데이터 증강 분석 시작"""
    if not data_aug_engine:
        raise HTTPException(
            status_code=503,
            detail="데이터 증강 엔진을 사용할 수 없습니다"
        )

    try:
        # 파일 존재 확인
        if not Path(structured_file_path).exists():
            raise HTTPException(
                status_code=400,
                detail="정형 데이터 파일을 찾을 수 없습니다"
            )

        for kf in knowledge_files:
            if not Path(kf).exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"지식 파일을 찾을 수 없습니다: {kf}"
                )

        # 새 작업 생성
        task_id = await data_aug_engine.create_task(structured_file_path, knowledge_files)

        # 백그라운드에서 분석 시작
        background_tasks.add_task(run_full_analysis, task_id)

        logger.info(f"데이터 증강 분석 시작: {task_id}")

        return DataAugmentationTaskResponse(
            success=True,
            task_id=task_id,
            message="데이터 증강 분석이 시작되었습니다",
            status="analyzing"
        )

    except Exception as e:
        logger.error(f"분석 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/data-aug/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """작업 상태 조회"""
    if not data_aug_engine:
        raise HTTPException(
            status_code=503,
            detail="데이터 증강 엔진을 사용할 수 없습니다"
        )

    try:
        task_data = data_aug_engine.get_task_status(task_id)

        if not task_data:
            raise HTTPException(
                status_code=404,
                detail="작업을 찾을 수 없습니다"
            )

        # 결과 요약
        results = None
        if task_data['status'] == 'completed' and task_data.get('augmentation_results'):
            aug_results = task_data['augmentation_results']
            personas = task_data.get('generated_personas', [])

            results = {
                "clusters_found": task_data.get('data_analysis', {}).get('clustering', {}).get('clusters_found', 0),
                "personas_generated": len(personas),
                "data_augmented": aug_results.get('augmented_data_size', 0),
                "performance_improvement": aug_results.get('performance_improvement', 0.0)
            }

        return TaskStatusResponse(
            task_id=task_id,
            status=task_data['status'],
            progress=task_data['progress'],
            message=f"작업 상태: {task_data['status']}",
            results=results,
            error=task_data.get('error')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"작업 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/data-aug/results/{task_id}")
async def get_task_results(task_id: str):
    """작업 결과 상세 조회"""
    if not data_aug_engine:
        raise HTTPException(
            status_code=503,
            detail="데이터 증강 엔진을 사용할 수 없습니다"
        )

    try:
        task_data = data_aug_engine.get_task_status(task_id)

        if not task_data:
            raise HTTPException(
                status_code=404,
                detail="작업을 찾을 수 없습니다"
            )

        if task_data['status'] != 'completed':
            raise HTTPException(
                status_code=400,
                detail="작업이 아직 완료되지 않았습니다"
            )

        return {
            "task_id": task_id,
            "status": task_data['status'],
            "data_analysis": task_data.get('data_analysis'),
            "knowledge_summary": task_data.get('knowledge_summary'),
            "generated_personas": task_data.get('generated_personas'),
            "augmentation_results": task_data.get('augmentation_results'),
            "created_at": task_data['created_at']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"작업 결과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_full_analysis(task_id: str):
    """전체 분석 파이프라인 실행"""
    try:
        # 1. 데이터 분석
        await data_aug_engine.analyze_structured_data(task_id)

        # 2. 지식베이스 처리
        await data_aug_engine.process_knowledge_base(task_id)

        # 3. 페르소나 생성
        await data_aug_engine.generate_personas(task_id)

        # 4. 데이터 증강
        await data_aug_engine.augment_data(task_id)

        logger.info(f"전체 분석 완료: {task_id}")

    except Exception as e:
        logger.error(f"분석 파이프라인 실패 {task_id}: {e}")
        task_data = data_aug_engine.get_task_status(task_id)
        if task_data:
            task_data['status'] = 'error'
            task_data['error'] = str(e)

# 에러 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"글로벌 예외 발생: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "서버 내부 오류가 발생했습니다", "detail": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn

    # 환경 변수에서 설정 읽기
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    log_level = os.getenv("LOG_LEVEL", "info")

    print(f"🚀 PersonaGen API 서버 시작...")
    print(f"   - Host: {host}")
    print(f"   - Port: {port}")
    print(f"   - AWS Region: {os.getenv('AWS_REGION', 'us-east-1')}")
    print(f"   - Docs: http://{host}:{port}/docs")

    uvicorn.run(
        "persona_api:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False,  # 운영환경에서는 False
        access_log=True
    )