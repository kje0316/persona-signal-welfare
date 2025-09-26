#!/usr/bin/env python3
"""
복지 서비스 데이터를 위한 FastAPI 엔드포인트
"""

from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
# import psycopg2
# from psycopg2.extras import RealDictCursor
import json
import uuid
import asyncio
import os
from datetime import datetime
import pandas as pd

# 챗봇 서비스 임포트 (일시적으로 비활성화)
# try:
#     from .chatbot_service import welfare_chatbot, ChatMessage, UserProfile
# except ImportError:
#     from chatbot_service import welfare_chatbot, ChatMessage, UserProfile

# 임시 모델 정의
from pydantic import BaseModel as PydanticBaseModel

class ChatMessage(PydanticBaseModel):
    role: str
    content: str

class UserProfile(PydanticBaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    income: Optional[str] = None
    household_size: Optional[int] = None
    needs: Optional[List[str]] = None

# 시연용 Mock 복지 서비스 데이터
MOCK_WELFARE_SERVICES = [
    {
        "service_id": "DEMO_001",
        "service_name": "청년 월세 지원",
        "service_type": "local",
        "service_summary": "만 19~39세 무주택 청년에게 월 최대 20만원까지 월세를 지원합니다. 보증금 대출도 가능합니다.",
        "detailed_link": "https://www.seoul.go.kr",
        "managing_agency": "서울시 주택정책과",
        "region_sido": "서울특별시",
        "region_sigungu": "전체",
        "department": "주택정책과",
        "contact_phone": "02-120",
        "contact_email": "housing@seoul.go.kr",
        "address": "서울시 중구 태평로 1가",
        "support_target": "만 19~39세 청년, 무주택자, 월세 거주자",
        "selection_criteria": "중위소득 150% 이하",
        "support_content": "월세 최대 20만원 지원, 보증금 대출 연계",
        "support_cycle": "월 1회",
        "payment_method": "계좌이체",
        "application_method": "온라인 신청",
        "required_documents": "주민등록등본, 임대차계약서, 소득증명서",
        "category": "주거지원",
        "life_cycle": "청년",
        "target_characteristics": "청년, 1인가구, 2인가구",
        "interest_topics": "주거, 월세, 청년",
        "service_status": "active",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "view_count": 1250,
        "last_updated": "2024-09-01",
        "created_at": "2024-01-01",
        "updated_at": "2024-09-01"
    },
    {
        "service_id": "DEMO_002",
        "service_name": "임신·출산 진료비 지원(국민행복카드)",
        "service_type": "government",
        "service_summary": "임신·출산과 관련된 진료비, 약제비 등을 지원하여 경제적 부담을 덜어드립니다.",
        "detailed_link": "https://www.bokjiro.go.kr",
        "managing_agency": "보건복지부",
        "region_sido": "전국",
        "region_sigungu": "전체",
        "department": "출산정책과",
        "contact_phone": "129",
        "contact_email": "pregnancy@mohw.go.kr",
        "address": "세종특별자치시 도움4로 13",
        "support_target": "임산부, 출산가정, 임신 중인 여성",
        "selection_criteria": "임신 확인서 제출자",
        "support_content": "임신·출산 진료비 100만원 지원(다태아 140만원)",
        "support_cycle": "임신 기간 중 사용",
        "payment_method": "국민행복카드",
        "application_method": "온라인 신청, 보건소 방문",
        "required_documents": "임신확인서, 신분증, 통장사본",
        "category": "출산육아",
        "life_cycle": "출산-임신",
        "target_characteristics": "임산부, 1인가구, 다자녀가정",
        "interest_topics": "임신, 출산, 진료비",
        "service_status": "active",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "view_count": 2150,
        "last_updated": "2024-09-01",
        "created_at": "2024-01-01",
        "updated_at": "2024-09-01"
    },
    {
        "service_id": "DEMO_007",
        "service_name": "첫만남이용권",
        "service_type": "government",
        "service_summary": "2024년 출생아에게 200만원의 첫만남이용권을 지급하여 육아 경제적 부담을 경감합니다.",
        "detailed_link": "https://www.bokjiro.go.kr",
        "managing_agency": "보건복지부",
        "region_sido": "전국",
        "region_sigungu": "전체",
        "department": "출산정책과",
        "contact_phone": "129",
        "contact_email": "childcare@mohw.go.kr",
        "address": "세종특별자치시 도움4로 13",
        "support_target": "2024년 출생아 가구, 신생아 부모",
        "selection_criteria": "2024년 1월 1일 이후 출생아",
        "support_content": "아동 1인당 200만원 바우처 지급",
        "support_cycle": "출생 후 1회",
        "payment_method": "국민행복카드 바우처",
        "application_method": "온라인 신청, 주민센터 방문",
        "required_documents": "출생신고서, 통장사본, 신분증",
        "category": "출산육아",
        "life_cycle": "출산-임신, 영유아",
        "target_characteristics": "신생아 부모, 출산가정",
        "interest_topics": "출산, 육아, 바우처",
        "service_status": "active",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "view_count": 1890,
        "last_updated": "2024-09-01",
        "created_at": "2024-01-01",
        "updated_at": "2024-09-01"
    },
    {
        "service_id": "DEMO_003",
        "service_name": "기초생활보장 생계급여",
        "service_type": "government",
        "service_summary": "소득이 기준 중위소득 30% 이하인 가구에게 생계급여를 지원합니다.",
        "detailed_link": "https://www.bokjiro.go.kr",
        "managing_agency": "보건복지부",
        "region_sido": "전국",
        "region_sigungu": "전체",
        "department": "기초생활보장과",
        "contact_phone": "129",
        "contact_email": "welfare@mohw.go.kr",
        "address": "세종특별자치시 도움4로 13",
        "support_target": "기초생활수급자, 저소득층, 1인가구, 다인가구",
        "selection_criteria": "소득인정액이 기준 중위소득 30% 이하",
        "support_content": "생계급여 지원 (1인 가구 기준 월 623,368원)",
        "support_cycle": "월 1회",
        "payment_method": "계좌이체",
        "application_method": "주민센터 방문신청",
        "required_documents": "신청서, 소득재산신고서, 금융정보제공동의서",
        "category": "생활지원",
        "life_cycle": "전체",
        "target_characteristics": "저소득층, 기초생활수급자, 1인가구, 장애인",
        "interest_topics": "생계급여, 기초생활보장, 저소득",
        "service_status": "active",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "view_count": 2150,
        "last_updated": "2024-09-10",
        "created_at": "2024-01-01",
        "updated_at": "2024-09-10"
    },
    {
        "service_id": "DEMO_004",
        "service_name": "한부모가족 아동양육비",
        "service_type": "government",
        "service_summary": "한부모가족의 아동양육비를 지원하여 안정적인 양육환경을 조성합니다.",
        "detailed_link": "https://www.mogef.go.kr",
        "managing_agency": "여성가족부",
        "region_sido": "전국",
        "region_sigungu": "전체",
        "department": "가족정책과",
        "contact_phone": "02-2100-6000",
        "contact_email": "family@mogef.go.kr",
        "address": "서울특별시 중구 장교동 1-32",
        "support_target": "한부모가족, 조손가족, 미혼모, 미혼부",
        "selection_criteria": "기준 중위소득 63% 이하",
        "support_content": "아동양육비 월 21만원, 추가아동양육비 월 5만원",
        "support_cycle": "월 1회",
        "payment_method": "계좌이체",
        "application_method": "주민센터 방문신청",
        "required_documents": "한부모가족증명서, 소득증명서, 통장사본",
        "category": "육아지원",
        "life_cycle": "아동, 청소년",
        "target_characteristics": "한부모가족, 조손가족, 저소득층, 아동",
        "interest_topics": "한부모, 양육비, 아동지원",
        "service_status": "active",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "view_count": 750,
        "last_updated": "2024-08-20",
        "created_at": "2024-01-01",
        "updated_at": "2024-08-20"
    },
    {
        "service_id": "DEMO_005",
        "service_name": "장애인연금",
        "service_type": "government",
        "service_summary": "중증장애인의 근로능력 상실에 따른 소득보장을 위해 매월 일정액의 연금을 지급합니다.",
        "detailed_link": "https://www.bokjiro.go.kr/disability",
        "managing_agency": "보건복지부",
        "region_sido": "전국",
        "region_sigungu": "전체",
        "department": "장애인정책과",
        "contact_phone": "129",
        "contact_email": "disability@mohw.go.kr",
        "address": "세종특별자치시 도움4로 13",
        "support_target": "중증장애인, 장애인",
        "selection_criteria": "만 18세 이상 중증장애인, 소득하위 70% 이하",
        "support_content": "기초급여 최대 334,810원, 부가급여 최대 80,000원",
        "support_cycle": "월 1회",
        "payment_method": "계좌이체",
        "application_method": "주민센터 방문신청",
        "required_documents": "신청서, 소득재산신고서, 장애인등록증",
        "category": "장애인지원",
        "life_cycle": "전체",
        "target_characteristics": "장애인, 중증장애인, 저소득층",
        "interest_topics": "장애인연금, 중증장애인, 소득보장",
        "service_status": "active",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "view_count": 920,
        "last_updated": "2024-09-05",
        "created_at": "2024-01-01",
        "updated_at": "2024-09-05"
    },
    {
        "service_id": "DEMO_006",
        "service_name": "노인 돌봄 종합서비스",
        "service_type": "local",
        "service_summary": "독거노인 및 노인부부 가구에 전문요양보호사가 방문하여 신체활동 및 가사활동을 지원합니다.",
        "detailed_link": "https://www.seoul.go.kr/senior",
        "managing_agency": "서울시 어르신복지과",
        "region_sido": "서울특별시",
        "region_sigungu": "전체",
        "department": "어르신복지과",
        "contact_phone": "02-120",
        "contact_email": "senior@seoul.go.kr",
        "address": "서울시 중구 태평로 1가",
        "support_target": "만 65세 이상 노인, 독거노인, 노인부부",
        "selection_criteria": "기준 중위소득 160% 이하",
        "support_content": "신체활동지원, 가사활동지원, 개인활동지원",
        "support_cycle": "월 최대 27시간",
        "payment_method": "바우처 지급",
        "application_method": "국민건강보험공단 신청",
        "required_documents": "신청서, 소득증명서, 의사소견서",
        "category": "돌봄서비스",
        "life_cycle": "노년",
        "target_characteristics": "노인, 독거노인, 고령자, 1인가구",
        "interest_topics": "노인돌봄, 독거노인, 요양서비스",
        "service_status": "active",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "view_count": 680,
        "last_updated": "2024-08-25",
        "created_at": "2024-01-01",
        "updated_at": "2024-08-25"
    }
]

# Mock 데이터
MOCK_PERSONAS = [
    {
        "persona_id": 1,
        "name": "김영희 (20대 직장인)",
        "demographics": {"age": 25, "gender": "여성", "occupation": "사무직", "income": "2800만원", "region": "서울"},
        "characteristics": ["업무 스트레스 관리", "자기계발 관심", "주거비 부담", "1인 가구"],
        "needs": ["청년 주거지원", "직장인 상담 서비스", "교육비 지원", "의료비 지원"],
        "priority_services": ["청년 월세 지원", "심리상담 서비스", "직업능력개발 교육"]
    },
    {
        "persona_id": 2,
        "name": "박민수 (30대 신혼부부)",
        "demographics": {"age": 32, "gender": "남성", "occupation": "기술직", "income": "4200만원", "region": "경기도"},
        "characteristics": ["신혼생활 적응", "내집마련 계획", "육아 준비", "맞벌이 희망"],
        "needs": ["신혼부부 주거지원", "육아용품 지원", "부부상담 서비스", "출산장려금"],
        "priority_services": ["신혼부부 전세자금 대출", "임신·출산 지원", "육아휴직 급여"]
    },
    {
        "persona_id": 3,
        "name": "이순자 (60대 노인)",
        "demographics": {"age": 67, "gender": "여성", "occupation": "무직", "income": "120만원", "region": "부산"},
        "characteristics": ["건강 관리 필요", "독거 생활", "경제적 어려움", "디지털 소외"],
        "needs": ["의료비 지원", "생활비 지원", "돌봄 서비스", "문화활동 참여"],
        "priority_services": ["기초연금", "노인 돌봄 서비스", "의료급여"]
    },
    {
        "persona_id": 4,
        "name": "최지민 (대학생)",
        "demographics": {"age": 22, "gender": "남성", "occupation": "학생", "income": "0원", "region": "대전"},
        "characteristics": ["학업 집중", "아르바이트 병행", "취업 준비", "경제적 독립 준비"],
        "needs": ["학자금 지원", "생활비 지원", "취업 지원", "주거 지원"],
        "priority_services": ["국가장학금", "청년 구직활동 지원금", "대학생 생활관"]
    }
]

MOCK_EVALUATION_REPORT = {
    "summary": {
        "original_samples": 1000,
        "augmented_samples": 2500,
        "improvement_rate": "250%",
        "quality_score": 0.87,
        "processing_time": "5.2초",
        "personas_generated": 4
    },
    "performance_comparison": {
        "before_augmentation": {
            "accuracy": 0.72,
            "precision": 0.68,
            "recall": 0.71,
            "f1_score": 0.69,
            "coverage": 0.65
        },
        "after_augmentation": {
            "accuracy": 0.87,
            "precision": 0.84,
            "recall": 0.89,
            "f1_score": 0.86,
            "coverage": 0.91
        },
        "improvement": {
            "accuracy": "+20.8%",
            "precision": "+23.5%",
            "recall": "+25.4%",
            "f1_score": "+24.6%",
            "coverage": "+40.0%"
        }
    },
    "metrics": {
        "diversity_score": 0.92,
        "validity_score": 0.85,
        "consistency_score": 0.89,
        "novelty_score": 0.78
    },
    "insights": [
        "생성된 페르소나의 다양성이 92%로 우수함",
        "실제 사용자 패턴과 89% 일치율 달성",
        "데이터 커버리지 40% 향상으로 더 포괄적인 분석 가능",
        "4개의 구별되는 페르소나로 세분화된 사용자 그룹 분석 가능"
    ],
    "recommendations": [
        "생성된 페르소나를 활용한 개인화 서비스 개발 권장",
        "추가 도메인 지식으로 더 정교한 페르소나 생성 가능",
        "A/B 테스트를 통한 페르소나별 최적화 전략 수립"
    ]
}

# 데이터베이스 연결 정보
DB_CONFIG = {
    'host': 'seoul-ht-11.cpk0oamsu0g6.us-west-1.rds.amazonaws.com',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'yeardream11!!'
}

app = FastAPI(title="Welfare Service API", description="복지 서비스 데이터 API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic 모델들
class WelfareServiceBase(BaseModel):
    service_name: str
    service_type: str
    service_summary: Optional[str] = None
    detailed_link: Optional[str] = None
    managing_agency: Optional[str] = None
    support_target: Optional[str] = None
    selection_criteria: Optional[str] = None
    support_content: Optional[str] = None
    category: Optional[str] = None
    target_characteristics: Optional[str] = None

class WelfareService(WelfareServiceBase):
    service_id: str
    region_sido: Optional[str] = None
    region_sigungu: Optional[str] = None
    department: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None
    support_cycle: Optional[str] = None
    payment_method: Optional[str] = None
    application_method: Optional[str] = None
    required_documents: Optional[str] = None
    life_cycle: Optional[str] = None
    interest_topics: Optional[str] = None
    service_status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    view_count: Optional[int] = 0
    last_updated: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class FilterRequest(BaseModel):
    gender: Optional[str] = None
    lifeStage: Optional[str] = None
    income: Optional[str] = None
    householdSize: Optional[str] = None
    householdSituation: Optional[str] = None
    category: Optional[str] = None
    service_type: Optional[str] = None
    limit: Optional[int] = 50
    offset: Optional[int] = 0

class ServiceResponse(BaseModel):
    total: int
    services: List[WelfareService]
    filters_applied: Dict[str, Any]

# 챗봇 관련 모델
class ChatRequest(BaseModel):
    message: str
    user_profile: UserProfile
    conversation_history: List[ChatMessage]

class ChatResponse(BaseModel):
    response: str
    timestamp: datetime

# 데이터베이스 연결 헬퍼 (현재는 비활성화)
def get_db_connection():
    raise HTTPException(status_code=500, detail="Database connection disabled for demo mode")

# 복지 서비스 필터링 로직 - 새로운 필드 구조
def build_filter_query(filters: FilterRequest):
    """새로운 필드 구조에 따른 SQL 쿼리 생성"""
    conditions = []
    params = []

    # 성별 필터링
    if filters.gender and filters.gender in ['male', 'female']:
        gender_keywords = {
            'male': ['남성', '남자', '남근로자'],
            'female': ['여성', '여자', '여근로자', '여성가장']
        }
        keywords = gender_keywords[filters.gender]
        gender_condition = ' OR '.join(['support_target ILIKE %s'] * len(keywords))
        conditions.append(f'({gender_condition})')
        params.extend([f'%{keyword}%' for keyword in keywords])

    # 생애주기 필터링
    if filters.lifeStage:
        lifestage_keywords = {
            'pregnancy': ['출산', '임신', '임산부', '예비부모'],
            'infant': ['영유아', '영아', '유아', '0세', '1세', '2세', '3세', '4세', '5세'],
            'child': ['아동', '초등', '6세', '7세', '8세', '9세', '10세', '11세', '12세'],
            'adolescent': ['청소년', '중학', '고등', '13세', '14세', '15세', '16세', '17세', '18세'],
            'youth': ['청년', '19세', '20세', '30대', '대학', '취업', '신혼'],
            'middle': ['중장년', '40대', '50대', '60대'],
            'senior': ['노인', '노년', '65세', '70세', '80세', '고령']
        }
        if filters.lifeStage in lifestage_keywords:
            keywords = lifestage_keywords[filters.lifeStage]
            lifestage_condition = ' OR '.join(['(support_target ILIKE %s OR life_cycle ILIKE %s)'] * len(keywords))
            conditions.append(f'({lifestage_condition})')
            for keyword in keywords:
                params.extend([f'%{keyword}%', f'%{keyword}%'])

    # 소득 필터링 (직접 금액 대비)
    if filters.income and filters.income.isdigit():
        income_amount = int(filters.income)
        # 소득 구간에 따른 키워드 매핑
        if income_amount <= 200:
            income_keywords = ['기초생활', '수급자', '차상위', '저소득']
        elif income_amount <= 400:
            income_keywords = ['중위소득', '일반', '근로자']
        else:
            income_keywords = ['일반', '근로자']

        income_condition = ' OR '.join(['(support_target ILIKE %s OR selection_criteria ILIKE %s)'] * len(income_keywords))
        conditions.append(f'({income_condition})')
        for keyword in income_keywords:
            params.extend([f'%{keyword}%', f'%{keyword}%'])

    # 가구형태 필터링
    if filters.householdSize:
        household_keywords = {
            '1': ['1인가구', '독거', '1인', '혼자'],
            '2': ['2인가구', '부부', '2인'],
            '3': ['3인가구', '3인'],
            '4+': ['4인가구', '4인', '5인', '다자녀', '대가족']
        }
        if filters.householdSize in household_keywords:
            keywords = household_keywords[filters.householdSize]
            household_condition = ' OR '.join(['support_target ILIKE %s'] * len(keywords))
            conditions.append(f'({household_condition})')
            params.extend([f'%{keyword}%' for keyword in keywords])

    # 가구상황 필터링
    if filters.householdSituation and filters.householdSituation != 'general':
        situation_keywords = {
            'single_parent': ['한부모', '조손', '미혼모', '미혼부'],
            'disability': ['장애', '장애인', '장애아동'],
            'veteran': ['국가유공자', '보훈대상자', '보훈'],
            'multi_child': ['다자녀', '3자녀', '4자녀', '5자녀'],
            'multicultural': ['다문화', '탈북', '새터민', '외국인'],
            'low_income': ['저소득', '기초생활', '수급자', '차상위']
        }
        if filters.householdSituation in situation_keywords:
            keywords = situation_keywords[filters.householdSituation]
            situation_condition = ' OR '.join(['(support_target ILIKE %s OR target_characteristics ILIKE %s)'] * len(keywords))
            conditions.append(f'({situation_condition})')
            for keyword in keywords:
                params.extend([f'%{keyword}%', f'%{keyword}%'])

    # 카테고리 필터링
    if filters.category:
        conditions.append('category ILIKE %s')
        params.append(f'%{filters.category}%')

    # 서비스 유형 필터링
    if filters.service_type:
        conditions.append('service_type = %s')
        params.append(filters.service_type)

    # 활성 서비스만 조회
    conditions.append("(service_status IS NULL OR service_status = 'active')")

    where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ''

    return where_clause, params

@app.get("/", tags=["Health"])
async def health_check():
    """API 상태 확인"""
    return {"status": "healthy", "message": "Welfare Service API is running"}

@app.get("/download-pdf/{filename}", tags=["Files"])
async def download_pdf(filename: str):
    """PDF 파일 다운로드"""
    try:
        # 안전한 파일 경로 생성
        base_path = '/Users/kje/coding/project/persona-signal-welfare'
        file_path = os.path.join(base_path, filename)

        # 파일 존재 여부 확인
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

        # PDF 파일인지 확인
        if not filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="PDF 파일만 다운로드 가능합니다.")

        # 보안을 위해 파일 경로가 프로젝트 디렉토리 내에 있는지 확인
        if not os.path.abspath(file_path).startswith(os.path.abspath(base_path)):
            raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/pdf'
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 다운로드 오류: {str(e)}")

@app.get("/welfare-services", response_model=ServiceResponse, tags=["Welfare Services"])
async def get_welfare_services(
    gender: Optional[str] = Query(None, description="성별"),
    lifeStage: Optional[str] = Query(None, description="생애주기"),
    income: Optional[str] = Query(None, description="연소득(만원)"),
    householdSize: Optional[str] = Query(None, description="가구형태"),
    householdSituation: Optional[str] = Query(None, description="가구상황"),
    category: Optional[str] = Query(None, description="카테고리"),
    service_type: Optional[str] = Query(None, description="서비스유형"),
    limit: int = Query(50, description="결과 수 제한"),
    offset: int = Query(0, description="오프셋")
):
    """복지 서비스 목록 조회 (필터링 지원)"""

    filters = FilterRequest(
        gender=gender,
        lifeStage=lifeStage,
        income=income,
        householdSize=householdSize,
        householdSituation=householdSituation,
        category=category,
        service_type=service_type,
        limit=limit,
        offset=offset
    )

    # BOKJIDB.xlsx Sheet2 데이터 사용
    try:
        # EC2 호환을 위한 상대 경로 사용
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        excel_path = os.path.join(project_root, 'src', 'data', 'processed', 'BOKJIDB.xlsx')

        print(f"Excel file path: {excel_path}")

        if not os.path.exists(excel_path):
            print(f"Excel file not found at: {excel_path}")
            raise FileNotFoundError(f"Excel file not found: {excel_path}")

        df = pd.read_excel(excel_path, sheet_name='Sheet2')
        print(f"Excel file loaded successfully. Total rows: {len(df)}")

        # DataFrame을 서비스 형태로 변환
        excel_services = []
        for idx, row in df.iterrows():
            service = {
                "service_id": f"EXCEL_{idx:03d}",
                "service_name": row['복지명'],
                "service_type": "government",
                "service_summary": row['복지명'],
                "detailed_link": row['링크'],
                "managing_agency": "복지로",
                "support_target": f"성별: {row['성별']}, 생애주기: {row['생애주기']}, 가구형태: {row['가구형태']}, 가구상황: {row['가구상황']}",
                "selection_criteria": row['소득-금액'],
                "support_content": row['복지명'],
                "category": "복지서비스",
                "life_cycle": row['생애주기'],
                "target_characteristics": row['가구상황'],
                "service_status": "active",
                "view_count": 0,
                "metadata": {
                    "gender": row['성별'],
                    "life_stage": row['생애주기'],
                    "income_criteria": row['소득-금액'],
                    "household_type": row['가구형태'],
                    "household_situation": row['가구상황']
                }
            }
            excel_services.append(service)

    except Exception as e:
        # Excel 파일 읽기 실패 시 Mock 데이터 사용
        print(f"Excel file reading failed, using mock data: {str(e)}")
        excel_services = MOCK_WELFARE_SERVICES

    # BOKJIDB.xlsx 기반 필터링
    filtered_services = []

    # 시나리오 1: 여성, 출산, 4000, 1인, 일반
    if (filters.gender == 'female' and filters.lifeStage == 'pregnancy' and
        filters.income == '4000' and filters.householdSize == '1' and
        filters.householdSituation == 'general'):

        print(f"시나리오 1 조건 만족. 총 {len(excel_services)}개 서비스 검토 중...")

        for service in excel_services:
            metadata = service.get('metadata', {})
            gender = metadata.get('gender', 'ALL')
            life_stage = metadata.get('life_stage', '')
            household_type = metadata.get('household_type', '')

            # 성별 매칭 (여성 또는 ALL)
            if gender in ['여성', 'ALL']:
                # 생애주기에 임신, 출산, 청년, 영유아, 아동 포함되거나 포괄적인 경우
                life_keywords = ['임신', '출산', '청년', '영유아', '아동']
                has_matching_lifecycle = any(keyword in life_stage for keyword in life_keywords) or len(life_stage.split(',')) >= 5
                if has_matching_lifecycle:
                    # 1인 가구 지원하는 서비스
                    if household_type in ['1인', '4인이하', '-']:
                        filtered_services.append(service)

    # 시나리오 2: 남성, 고령, 1200, 1인, 저소득
    elif (filters.gender == 'male' and filters.lifeStage == 'senior' and
          filters.income == '1200' and filters.householdSize == '1' and
          filters.householdSituation == 'low_income'):

        for service in excel_services:
            metadata = service.get('metadata', {})
            gender = metadata.get('gender', 'ALL')
            life_stage = metadata.get('life_stage', '')
            household_situation = metadata.get('household_situation', '')
            household_type = metadata.get('household_type', '')

            # 성별 매칭 (남성 또는 ALL)
            if gender in ['남성', 'ALL']:
                # 생애주기에 노년, 중장년 포함
                if any(keyword in life_stage for keyword in ['노년', '중장년']) or 'ALL' in life_stage:
                    # 저소득 지원하는 서비스
                    if '저소득' in household_situation:
                        # 1인 가구 지원하는 서비스
                        if household_type in ['1인', '4인이하', '-']:
                            filtered_services.append(service)

    else:
        # 일반적인 필터링
        for service in excel_services:
            match = True
            metadata = service.get('metadata', {})
            gender = metadata.get('gender', 'ALL')
            life_stage = metadata.get('life_stage', '')
            household_situation = metadata.get('household_situation', '')
            household_type = metadata.get('household_type', '')

            # 성별 필터링
            if filters.gender:
                gender_map = {'male': ['남성', 'ALL'], 'female': ['여성', 'ALL']}
                if filters.gender in gender_map:
                    if gender not in gender_map[filters.gender]:
                        match = False

            # 생애주기 필터링
            if filters.lifeStage and match:
                lifestage_map = {
                    'pregnancy': ['임신', '출산', '청년'],
                    'youth': ['청년'],
                    'middle': ['중장년'],
                    'senior': ['노년', '중장년']
                }
                if filters.lifeStage in lifestage_map:
                    keywords = lifestage_map[filters.lifeStage]
                    if not any(keyword in life_stage for keyword in keywords) and 'ALL' not in life_stage:
                        match = False

            # 가구상황 필터링
            if filters.householdSituation and match:
                if filters.householdSituation == 'low_income':
                    if '저소득' not in household_situation:
                        match = False
                elif filters.householdSituation != 'general':
                    situation_map = {
                        'single_parent': ['한부모', '조손'],
                        'disability': ['장애인'],
                        'multi_child': ['다자녀'],
                        'multicultural': ['다문화', '탈북민']
                    }
                    if filters.householdSituation in situation_map:
                        keywords = situation_map[filters.householdSituation]
                        if not any(keyword in household_situation for keyword in keywords):
                            match = False

            # 가구형태 필터링
            if filters.householdSize and match:
                if filters.householdSize == '1' and household_type not in ['1인', '4인이하', '-']:
                    match = False
                elif filters.householdSize in ['2', '3', '4+'] and household_type not in ['4인이하', '-']:
                    match = False

            if match:
                filtered_services.append(service)

        # 최소 10개 서비스 보장
        if len(filtered_services) < 10:
            # 추가 서비스를 위해 더 넓은 기준으로 필터링
            additional_services = []
            for service in excel_services:
                if service not in filtered_services:
                    metadata = service.get('metadata', {})

                    # 시나리오 1을 위한 추가 서비스
                    if (filters.gender == 'female' and filters.lifeStage == 'pregnancy'):
                        if metadata.get('gender') in ['여성', 'ALL'] or '청년' in metadata.get('life_stage', ''):
                            additional_services.append(service)

                    # 시나리오 2를 위한 추가 서비스
                    elif (filters.gender == 'male' and filters.lifeStage == 'senior'):
                        if metadata.get('gender') in ['남성', 'ALL'] or '노년' in metadata.get('life_stage', ''):
                            additional_services.append(service)

                    # 일반적인 추가 서비스
                    else:
                        additional_services.append(service)

            # 부족한 만큼 추가
            needed = 10 - len(filtered_services)
            filtered_services.extend(additional_services[:needed])

    # 페이징 처리
    total = len(filtered_services)
    paginated_services = filtered_services[offset:offset+limit]

    return ServiceResponse(
        total=total,
        services=paginated_services,
        filters_applied=filters.dict(exclude_none=True)
    )

@app.get("/welfare-services/{service_id}", response_model=WelfareService, tags=["Welfare Services"])
async def get_welfare_service(service_id: str):
    """특정 복지 서비스 상세 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT
                service_id, service_name, service_type, service_summary, detailed_link,
                managing_agency, region_sido, region_sigungu, department,
                contact_phone, contact_email, address,
                support_target, selection_criteria, support_content,
                support_cycle, payment_method, application_method, required_documents,
                category, life_cycle, target_characteristics, interest_topics,
                service_status, start_date, end_date, view_count, last_updated,
                created_at, updated_at
            FROM welfare_services
            WHERE service_id = %s
        """

        cursor.execute(query, (service_id,))
        service = cursor.fetchone()

        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        # 조회수 증가
        cursor.execute(
            "UPDATE welfare_services SET view_count = COALESCE(view_count, 0) + 1 WHERE service_id = %s",
            (service_id,)
        )
        conn.commit()

        # 날짜 필드 문자열 변환
        service_dict = dict(service)
        for date_field in ['start_date', 'end_date', 'last_updated', 'created_at', 'updated_at']:
            if service_dict.get(date_field):
                service_dict[date_field] = str(service_dict[date_field])

        cursor.close()
        conn.close()

        return service_dict

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/welfare-categories", tags=["Statistics"])
async def get_welfare_categories():
    """복지 서비스 카테고리 통계"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT category, COUNT(*) as count
            FROM welfare_services
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category
            ORDER BY count DESC
        """

        cursor.execute(query)
        categories = cursor.fetchall()

        cursor.close()
        conn.close()

        return {"categories": [dict(cat) for cat in categories]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/welfare-statistics", tags=["Statistics"])
async def get_welfare_statistics():
    """복지 서비스 통계 정보"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 전체 통계
        stats_query = """
            SELECT
                COUNT(*) as total_services,
                COUNT(CASE WHEN service_type = 'government' THEN 1 END) as government_services,
                COUNT(CASE WHEN service_type = 'local' THEN 1 END) as local_services,
                COUNT(CASE WHEN service_type = 'private' THEN 1 END) as private_services
            FROM welfare_services
            WHERE service_status IS NULL OR service_status = 'active'
        """

        cursor.execute(stats_query)
        stats = cursor.fetchone()

        # 카테고리별 통계 (상위 10개)
        category_query = """
            SELECT category, COUNT(*) as count
            FROM welfare_services
            WHERE category IS NOT NULL AND category != ''
                AND (service_status IS NULL OR service_status = 'active')
            GROUP BY category
            ORDER BY count DESC
            LIMIT 10
        """

        cursor.execute(category_query)
        categories = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "statistics": dict(stats),
            "top_categories": [dict(cat) for cat in categories]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# 챗봇 관련 엔드포인트 임시 비활성화
# @app.post("/api/v1/chat", response_model=ChatResponse, tags=["Chatbot"])
# async def chat_with_ai(request: ChatRequest):
#     """AWS Bedrock Claude를 사용한 복지 상담 챗봇"""
#     pass

# @app.post("/api/v1/chat/recommend", tags=["Chatbot"])
# async def get_personalized_recommendations(user_profile: UserProfile, keywords: Optional[List[str]] = None):
#     """사용자 맞춤형 복지 서비스 추천"""
#     pass

# Mock API 엔드포인트들
@app.post("/api/v1/upload/structured-data", tags=["Data Augmentation"])
async def upload_structured_data(file: UploadFile = File(...)):
    """정형 데이터 파일 업로드 (Mock)"""
    try:
        # 간단한 파일 유효성 검사
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            return {"success": False, "message": "지원하지 않는 파일 형식입니다."}

        # Mock 응답
        mock_file_id = str(uuid.uuid4())
        return {
            "success": True,
            "file_id": mock_file_id,
            "filename": file.filename,
            "file_path": f"/uploads/{mock_file_id}/{file.filename}",
            "message": "파일 업로드가 완료되었습니다."
        }
    except Exception as e:
        return {"success": False, "message": f"업로드 오류: {str(e)}"}

@app.post("/api/v1/upload/knowledge-files", tags=["Data Augmentation"])
async def upload_knowledge_files(files: List[UploadFile] = File(...)):
    """지식 파일들 업로드 (Mock)"""
    try:
        uploaded_files = []
        for file in files:
            if not file.filename.endswith(('.txt', '.md', '.pdf', '.docx')):
                continue

            mock_file_id = str(uuid.uuid4())
            uploaded_files.append({
                "filename": file.filename,
                "file_path": f"/uploads/knowledge/{mock_file_id}/{file.filename}"
            })

        return {
            "success": True,
            "files": uploaded_files,
            "message": f"{len(uploaded_files)}개 파일 업로드가 완료되었습니다."
        }
    except Exception as e:
        return {"success": False, "message": f"업로드 오류: {str(e)}"}

async def simulate_data_augmentation(task_id: str):
    """데이터 증강 시뮬레이션 함수"""
    stages = [
        {"stage": "데이터 전처리", "progress": 20, "message": "데이터 형식을 분석하고 있습니다..."},
        {"stage": "페르소나 생성", "progress": 40, "message": "AI 페르소나를 생성하고 있습니다..."},
        {"stage": "데이터 증강", "progress": 60, "message": "데이터를 증강하고 있습니다..."},
        {"stage": "품질 평가", "progress": 80, "message": "결과를 평가하고 있습니다..."},
        {"stage": "완료", "progress": 100, "message": "모든 작업이 완료되었습니다."}
    ]

    for stage_info in stages:
        await manager.send_progress(task_id, {
            "type": "progress",
            "progress": stage_info["progress"],
            "stage": stage_info["stage"],
            "message": stage_info["message"]
        })
        await asyncio.sleep(1)  # 1초 대기

    # 완료 메시지
    await manager.send_progress(task_id, {
        "type": "completed",
        "progress": 100,
        "stage": "완료",
        "message": "모든 작업이 완료되었습니다.",
        "results": {
            "personas_count": len(MOCK_PERSONAS),
            "augmented_samples": 2500,
            "quality_score": 0.87
        }
    })

@app.post("/api/v1/augmentation/start", tags=["Data Augmentation"])
async def start_augmentation(request: Dict[str, Any]):
    """데이터 증강 시작 (Mock)"""
    try:
        # Mock task ID 생성
        task_id = str(uuid.uuid4())

        return {
            "success": True,
            "task_id": task_id,
            "status": "started",
            "message": "데이터 증강 작업이 시작되었습니다."
        }
    except Exception as e:
        return {"success": False, "message": f"작업 시작 오류: {str(e)}"}

@app.get("/api/v1/augmentation/download/{task_id}/{file_type}", tags=["Data Augmentation"])
async def download_results(task_id: str, file_type: str):
    """결과 다운로드 (Mock)"""
    from fastapi.responses import JSONResponse

    if file_type == "personas":
        return JSONResponse(content={"personas": MOCK_PERSONAS})
    elif file_type == "evaluation_report":
        return JSONResponse(content=MOCK_EVALUATION_REPORT)
    elif file_type == "augmented_data":
        # Mock CSV 데이터
        mock_csv = "id,name,age,income,needs\\n1,김영희,25,2800,주거지원\\n2,박민수,32,4200,육아지원"
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=mock_csv, media_type="text/csv")
    else:
        return JSONResponse(content={"evaluation_results": {"accuracy": 0.87, "precision": 0.92}})

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: str):
        if task_id in self.active_connections:
            del self.active_connections[task_id]

    async def send_progress(self, task_id: str, data: dict):
        if task_id in self.active_connections:
            try:
                await self.active_connections[task_id].send_text(json.dumps(data))
            except:
                self.disconnect(task_id)

manager = ConnectionManager()

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket 진행 상황 업데이트 및 시뮬레이션 실행"""
    await manager.connect(websocket, task_id)

    try:
        # 연결 확인 메시지
        await manager.send_progress(task_id, {
            "type": "connected",
            "message": "WebSocket 연결됨"
        })

        # 시뮬레이션 즉시 시작
        await simulate_data_augmentation(task_id)

        # 시뮬레이션 완료 후 연결 유지
        while True:
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        manager.disconnect(task_id)
    except Exception as e:
        await manager.send_progress(task_id, {
            "type": "error",
            "error": str(e)
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)