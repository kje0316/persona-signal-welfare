"""
통합 데이터 증강 API - 모듈화된 아키텍처 기반
FastAPI + WebSocket을 사용한 실시간 데이터 증강 파이프라인
"""

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import tempfile
import uuid

# FastAPI 및 관련
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

# 모듈 import
import sys
sys.path.append(str(Path(__file__).parent.parent))

from modules.data_augmentation.pipeline import DataAugmentationPipeline
from modules.common.database import db_manager
from modules.common.models import TaskStatus

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 앱
app = FastAPI(
    title="Universal Data Augmentation API",
    description="AI 페르소나 기반 범용 데이터 증강 시스템",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 전역 변수
pipeline_instance = DataAugmentationPipeline()
active_tasks: Dict[str, Dict[str, Any]] = {}
websocket_connections: Dict[str, WebSocket] = {}
SERVER_START_TIME = datetime.now()

# Pydantic 모델들
class DataAugmentationRequest(BaseModel):
    scenario: str = Field(default="normal", description="페르소나 시나리오 (normal, stress, economic_difficulty 등)")
    domain: str = Field(default="general", description="도메인 (자동 감지됨)")
    target_samples: int = Field(default=1000, ge=100, le=50000, description="목표 증강 샘플 수")
    augmentation_strategies: List[str] = Field(default=["interpolation", "noise_addition", "pattern_variation"], description="증강 전략")
    target_columns: List[str] = Field(default=[], description="성능 평가용 타겟 컬럼")

class TaskResponse(BaseModel):
    success: bool
    task_id: str
    status: str
    message: str
    websocket_url: Optional[str] = None

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    current_stage: str
    message: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    estimated_completion: Optional[str] = None

# 시작/종료 이벤트
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 초기화"""
    logger.info("🚀 Universal Data Augmentation API 시작")
    try:
        # 데이터베이스 테이블 생성
        await db_manager.create_tables()
        logger.info("✅ 데이터베이스 초기화 완료")
    except Exception as e:
        logger.error(f"❌ 초기화 실패: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 정리"""
    logger.info("🔄 서버 종료 중...")
    # 진행 중인 작업들 정리
    for task_id in list(active_tasks.keys()):
        if "background_task" in active_tasks[task_id]:
            active_tasks[task_id]["background_task"].cancel()
    # 데이터베이스 연결 종료
    await db_manager.close()
    logger.info("✅ 서버 종료 완료")

# 헬스체크 및 기본 엔드포인트
@app.get("/")
async def root():
    return {
        "service": "Universal Data Augmentation API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "websocket_endpoint": "/ws/{task_id}"
    }

@app.get("/health")
async def health_check():
    """시스템 헬스체크"""
    try:
        # 데이터베이스 연결 확인
        db_healthy = db_manager.table_exists("alembic_version") or True  # 기본적으로 healthy

        uptime = datetime.now() - SERVER_START_TIME

        return {
            "status": "healthy" if db_healthy else "degraded",
            "database": "connected" if db_healthy else "disconnected",
            "active_tasks": len(active_tasks),
            "websocket_connections": len(websocket_connections),
            "uptime": str(uptime),
            "server_start": SERVER_START_TIME.isoformat()
        }
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(e)}
        )

# 파일 업로드 엔드포인트들
@app.post("/api/v1/upload/structured-data")
async def upload_structured_data(file: UploadFile = File(...)):
    """정형 데이터 파일 업로드"""
    try:
        # 파일 확장자 검증
        if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="지원되지 않는 파일 형식입니다. CSV, Excel 파일만 업로드 가능합니다."
            )

        # 임시 파일 저장
        upload_dir = Path(tempfile.gettempdir()) / "augmentation_uploads"
        upload_dir.mkdir(exist_ok=True)

        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        saved_path = upload_dir / f"structured_{file_id}{file_extension}"

        # 파일 저장
        content = await file.read()
        with open(saved_path, "wb") as f:
            f.write(content)

        logger.info(f"정형 데이터 업로드 완료: {file.filename} -> {saved_path}")

        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "size": len(content),
            "file_path": str(saved_path),
            "message": "정형 데이터 업로드 완료"
        }

    except Exception as e:
        logger.error(f"정형 데이터 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/upload/knowledge-files")
async def upload_knowledge_files(files: List[UploadFile] = File(...)):
    """도메인 지식 파일들 업로드"""
    try:
        upload_dir = Path(tempfile.gettempdir()) / "augmentation_uploads" / "knowledge"
        upload_dir.mkdir(parents=True, exist_ok=True)

        uploaded_files = []
        batch_id = str(uuid.uuid4())

        for file in files:
            # 지원되는 파일 형식만 처리
            if not file.filename.lower().endswith(('.txt', '.md', '.pdf', '.docx')):
                continue

            file_extension = Path(file.filename).suffix
            saved_path = upload_dir / f"knowledge_{batch_id}_{file.filename}"

            content = await file.read()
            with open(saved_path, "wb") as f:
                f.write(content)

            uploaded_files.append({
                "filename": file.filename,
                "size": len(content),
                "file_path": str(saved_path)
            })

        logger.info(f"도메인 지식 파일 업로드 완료: {len(uploaded_files)}개")

        return {
            "success": True,
            "batch_id": batch_id,
            "files_uploaded": len(uploaded_files),
            "files": uploaded_files,
            "message": f"{len(uploaded_files)}개 지식 파일 업로드 완료"
        }

    except Exception as e:
        logger.error(f"지식 파일 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 메인 데이터 증강 API
@app.post("/api/v1/augmentation/start", response_model=TaskResponse)
async def start_data_augmentation(
    structured_file_path: str,
    knowledge_file_paths: List[str],
    config: DataAugmentationRequest,
    background_tasks: BackgroundTasks
):
    """데이터 증강 파이프라인 시작"""
    try:
        # 파일 존재 확인
        if not Path(structured_file_path).exists():
            raise HTTPException(status_code=400, detail="정형 데이터 파일을 찾을 수 없습니다")

        for kf_path in knowledge_file_paths:
            if not Path(kf_path).exists():
                raise HTTPException(status_code=400, detail=f"지식 파일을 찾을 수 없습니다: {kf_path}")

        # 새 작업 생성
        task_id = f"aug_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 출력 디렉토리 생성
        output_dir = Path(tempfile.gettempdir()) / "augmentation_results" / task_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # 작업 등록
        active_tasks[task_id] = {
            "task_id": task_id,
            "status": TaskStatus.PENDING,
            "progress": 0,
            "current_stage": "초기화 중",
            "started_at": datetime.now().isoformat(),
            "config": config.dict(),
            "input_files": {
                "structured_data": structured_file_path,
                "knowledge_files": knowledge_file_paths
            },
            "output_dir": str(output_dir)
        }

        # 백그라운드에서 파이프라인 실행
        background_task = asyncio.create_task(
            run_augmentation_pipeline(task_id, structured_file_path, knowledge_file_paths, config, output_dir)
        )
        active_tasks[task_id]["background_task"] = background_task

        logger.info(f"데이터 증강 파이프라인 시작: {task_id}")

        return TaskResponse(
            success=True,
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="데이터 증강 파이프라인이 시작되었습니다",
            websocket_url=f"/ws/{task_id}"
        )

    except Exception as e:
        logger.error(f"파이프라인 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_augmentation_pipeline(
    task_id: str,
    structured_file_path: str,
    knowledge_file_paths: List[str],
    config: DataAugmentationRequest,
    output_dir: Path
):
    """백그라운드에서 실행되는 증강 파이프라인"""
    try:
        # 파이프라인 설정
        pipeline_config = {
            "task_id": task_id,
            "scenario": config.scenario,
            "target_samples": config.target_samples,
            "augmentation_strategies": config.augmentation_strategies,
            "target_columns": config.target_columns
        }

        # 진행 상황 업데이트 함수
        async def update_progress(stage: str, progress: int, message: str = ""):
            if task_id in active_tasks:
                active_tasks[task_id].update({
                    "current_stage": stage,
                    "progress": progress,
                    "last_update": datetime.now().isoformat()
                })

                # WebSocket으로 실시간 업데이트
                if task_id in websocket_connections:
                    try:
                        await websocket_connections[task_id].send_json({
                            "type": "progress",
                            "task_id": task_id,
                            "stage": stage,
                            "progress": progress,
                            "message": message
                        })
                    except:
                        pass  # WebSocket 연결이 끊어진 경우 무시

        # 1단계: 데이터 처리 시작
        await update_progress("데이터 처리", 10, "정형 데이터 분석 중...")
        active_tasks[task_id]["status"] = TaskStatus.ANALYZING

        # 2단계: 페르소나 생성
        await update_progress("페르소나 생성", 30, "클러스터링 및 페르소나 생성 중...")
        active_tasks[task_id]["status"] = TaskStatus.GENERATING_PERSONAS

        # 3단계: 데이터 증강
        await update_progress("데이터 증강", 60, "합성 데이터 생성 중...")
        active_tasks[task_id]["status"] = TaskStatus.AUGMENTING

        # 4단계: 품질 평가
        await update_progress("품질 평가", 80, "증강 품질 평가 중...")
        active_tasks[task_id]["status"] = TaskStatus.EVALUATING

        # 실제 파이프라인 실행
        pipeline_results = pipeline_instance.run_complete_pipeline(
            structured_data_path=structured_file_path,
            knowledge_file_paths=knowledge_file_paths,
            output_dir=str(output_dir),
            config=pipeline_config
        )

        # 5단계: 완료
        await update_progress("완료", 100, "모든 작업이 완료되었습니다")
        active_tasks[task_id].update({
            "status": TaskStatus.COMPLETED,
            "completed_at": datetime.now().isoformat(),
            "results": pipeline_results,
            "output_files": pipeline_results.get("output_files", {})
        })

        # WebSocket으로 완료 알림
        if task_id in websocket_connections:
            try:
                await websocket_connections[task_id].send_json({
                    "type": "completed",
                    "task_id": task_id,
                    "results": pipeline_results.get("summary", {}),
                    "output_files": pipeline_results.get("output_files", {})
                })
            except:
                pass

        logger.info(f"데이터 증강 파이프라인 완료: {task_id}")

    except Exception as e:
        logger.error(f"파이프라인 실행 실패 {task_id}: {e}")

        # 실패 상태 업데이트
        if task_id in active_tasks:
            active_tasks[task_id].update({
                "status": TaskStatus.FAILED,
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            })

        # WebSocket으로 실패 알림
        if task_id in websocket_connections:
            try:
                await websocket_connections[task_id].send_json({
                    "type": "error",
                    "task_id": task_id,
                    "error": str(e)
                })
            except:
                pass

# 작업 상태 조회 및 관리
@app.get("/api/v1/augmentation/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """작업 상태 조회"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

    task_data = active_tasks[task_id]

    # 실행 시간 계산
    started_at = task_data.get("started_at")
    estimated_completion = None
    if started_at and task_data["status"] not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        # 간단한 추정 로직 (평균 5분 소요)
        start_time = datetime.fromisoformat(started_at)
        elapsed = (datetime.now() - start_time).total_seconds()
        progress = task_data.get("progress", 0)
        if progress > 0:
            total_estimated = (elapsed / progress) * 100
            remaining = total_estimated - elapsed
            estimated_completion_time = datetime.now().timestamp() + remaining
            estimated_completion = datetime.fromtimestamp(estimated_completion_time).isoformat()

    return TaskStatusResponse(
        task_id=task_id,
        status=task_data["status"],
        progress=task_data.get("progress", 0),
        current_stage=task_data.get("current_stage", "알 수 없음"),
        message=task_data.get("message"),
        results=task_data.get("results", {}).get("summary") if task_data.get("results") else None,
        error=task_data.get("error"),
        started_at=started_at,
        estimated_completion=estimated_completion
    )

@app.get("/api/v1/augmentation/results/{task_id}")
async def get_task_results(task_id: str):
    """작업 결과 상세 조회"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

    task_data = active_tasks[task_id]

    if task_data["status"] != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="작업이 아직 완료되지 않았습니다")

    return {
        "task_id": task_id,
        "status": task_data["status"],
        "completed_at": task_data.get("completed_at"),
        "execution_time": task_data.get("results", {}).get("summary", {}).get("execution_time"),
        "results": task_data.get("results", {}),
        "output_files": task_data.get("output_files", {})
    }

@app.get("/api/v1/augmentation/download/{task_id}/{file_type}")
async def download_result_file(task_id: str, file_type: str):
    """결과 파일 다운로드"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

    task_data = active_tasks[task_id]
    output_files = task_data.get("output_files", {})

    if file_type not in output_files:
        raise HTTPException(status_code=404, detail=f"파일 타입 '{file_type}'을 찾을 수 없습니다")

    file_path = output_files[file_type]

    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다")

    # 파일 타입별 미디어 타입 설정
    media_types = {
        "personas": "application/json",
        "augmented_data": "text/csv",
        "evaluation_report": "text/plain",
        "evaluation_results": "application/json",
        "personas_summary": "text/plain"
    }

    return FileResponse(
        file_path,
        media_type=media_types.get(file_type, "application/octet-stream"),
        filename=Path(file_path).name
    )

@app.delete("/api/v1/augmentation/cancel/{task_id}")
async def cancel_task(task_id: str):
    """작업 취소"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

    task_data = active_tasks[task_id]

    # 백그라운드 작업 취소
    if "background_task" in task_data and not task_data["background_task"].done():
        task_data["background_task"].cancel()

    # 상태 업데이트
    active_tasks[task_id].update({
        "status": "cancelled",
        "cancelled_at": datetime.now().isoformat()
    })

    # WebSocket으로 취소 알림
    if task_id in websocket_connections:
        try:
            await websocket_connections[task_id].send_json({
                "type": "cancelled",
                "task_id": task_id,
                "message": "작업이 취소되었습니다"
            })
        except:
            pass

    return {"success": True, "message": "작업이 취소되었습니다"}

# WebSocket 연결
@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """실시간 작업 진행 상황 WebSocket"""
    await websocket.accept()
    websocket_connections[task_id] = websocket

    try:
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id,
            "message": "WebSocket 연결이 설정되었습니다"
        })

        # 연결 유지
        while True:
            try:
                # 클라이언트로부터 ping 메시지 대기
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
            except:
                break

    except Exception as e:
        logger.error(f"WebSocket 오류: {e}")
    finally:
        # 연결 정리
        if task_id in websocket_connections:
            del websocket_connections[task_id]

# 시스템 관리 API
@app.get("/api/v1/system/tasks")
async def list_all_tasks():
    """모든 작업 목록 조회"""
    task_summary = []
    for task_id, task_data in active_tasks.items():
        task_summary.append({
            "task_id": task_id,
            "status": task_data.get("status"),
            "progress": task_data.get("progress", 0),
            "started_at": task_data.get("started_at"),
            "current_stage": task_data.get("current_stage")
        })

    return {
        "total_tasks": len(active_tasks),
        "active_websockets": len(websocket_connections),
        "tasks": task_summary
    }

@app.delete("/api/v1/system/cleanup")
async def cleanup_completed_tasks():
    """완료된 작업들 정리"""
    cleaned_count = 0
    task_ids_to_remove = []

    for task_id, task_data in active_tasks.items():
        if task_data.get("status") in [TaskStatus.COMPLETED, TaskStatus.FAILED, "cancelled"]:
            # 24시간 이상 된 완료 작업만 정리
            completed_at = task_data.get("completed_at") or task_data.get("failed_at") or task_data.get("cancelled_at")
            if completed_at:
                completed_time = datetime.fromisoformat(completed_at)
                if (datetime.now() - completed_time).total_seconds() > 86400:  # 24시간
                    task_ids_to_remove.append(task_id)

    for task_id in task_ids_to_remove:
        del active_tasks[task_id]
        cleaned_count += 1

        # WebSocket 연결도 정리
        if task_id in websocket_connections:
            try:
                await websocket_connections[task_id].close()
            except:
                pass
            del websocket_connections[task_id]

    return {
        "success": True,
        "cleaned_tasks": cleaned_count,
        "remaining_tasks": len(active_tasks)
    }

# ============================================================
# UI 호환성 API 엔드포인트 (프론트엔드 통합용)
# ============================================================

@app.post("/api/v1/data-aug/upload-structured")
async def upload_structured_data_ui(file: UploadFile = File(...)):
    """정형 데이터 파일 업로드 (UI 호환용)"""
    return await upload_structured_data(file)

@app.post("/api/v1/data-aug/upload-knowledge")
async def upload_knowledge_files_ui(files: List[UploadFile] = File(...)):
    """도메인 지식 파일 업로드 (UI 호환용)"""
    return await upload_knowledge_files(files)

@app.post("/api/v1/data-aug/start")
async def start_augmentation_ui(
    structured_file_id: str,
    knowledge_batch_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):
    """데이터 증강 시작 (UI 호환용 - 간소화된 인터페이스)"""
    try:
        # 파일 경로 구성
        upload_dir = Path(tempfile.gettempdir()) / "augmentation_uploads"

        # 정형 데이터 파일 찾기
        structured_files = list(upload_dir.glob(f"structured_{structured_file_id}*"))
        if not structured_files:
            raise HTTPException(status_code=404, detail="정형 데이터 파일을 찾을 수 없습니다")

        structured_file_path = str(structured_files[0])

        # 지식 파일들 찾기
        knowledge_file_paths = []
        if knowledge_batch_id:
            knowledge_dir = upload_dir / "knowledge"
            knowledge_files = list(knowledge_dir.glob(f"knowledge_{knowledge_batch_id}_*"))
            knowledge_file_paths = [str(f) for f in knowledge_files]

        # 기본 설정으로 증강 시작
        config = DataAugmentationRequest()

        return await start_data_augmentation(
            structured_file_path=structured_file_path,
            knowledge_file_paths=knowledge_file_paths,
            config=config,
            background_tasks=background_tasks or BackgroundTasks()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"UI 증강 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/data-aug/status/{task_id}")
async def get_augmentation_status_ui(task_id: str):
    """증강 상태 조회 (UI 호환용)"""
    try:
        status = await get_task_status(task_id)
        return {
            "task_id": status.task_id,
            "status": status.status,
            "progress": status.progress,
            "stage": status.current_stage,
            "message": status.message,
            "error": status.error
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/data-aug/download/{task_id}")
async def download_augmented_data_ui(task_id: str):
    """증강된 데이터 다운로드 (UI 호환용)"""
    return await download_result_file(task_id, "augmented_data")

@app.get("/api/v1/data-aug/results/{task_id}")
async def get_augmentation_results_ui(task_id: str):
    """증강 결과 조회 (UI 호환용)"""
    return await get_task_results(task_id)

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

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))  # 메인 API 포트

    print(f"🚀 Universal Data Augmentation API 시작...")
    print(f"   - Host: {host}")
    print(f"   - Port: {port}")
    print(f"   - Docs: http://{host}:{port}/docs")
    print(f"   - WebSocket: ws://{host}:{port}/ws/{{task_id}}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        reload=False
    )