#!/usr/bin/env python3
"""
복지 서비스 데이터를 위한 FastAPI 엔드포인트
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

# 챗봇 서비스 임포트
try:
    from .chatbot_service import welfare_chatbot, ChatMessage, UserProfile
except ImportError:
    from chatbot_service import welfare_chatbot, ChatMessage, UserProfile

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
    age: Optional[str] = None
    region: Optional[str] = None
    income: Optional[str] = None
    targetGroup: Optional[str] = None
    household: Optional[str] = None
    housing: Optional[str] = None
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

# 데이터베이스 연결 헬퍼
def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

# 복지 서비스 필터링 로직
def build_filter_query(filters: FilterRequest):
    """필터링 조건에 따른 SQL 쿼리 생성"""
    conditions = []
    params = []

    # 연령대 필터링
    if filters.age and filters.age != 'all':
        age_keywords = {
            'child': ['아동', '청소년', '영유아', '18세 이하'],
            'youth': ['청년', '19', '20', '30'],
            'middle': ['중장년', '40', '50', '60'],
            'senior': ['노인', '65세', '70', '80']
        }
        if filters.age in age_keywords:
            keywords = age_keywords[filters.age]
            age_condition = ' OR '.join(['support_target ILIKE %s'] * len(keywords))
            conditions.append(f'({age_condition})')
            params.extend([f'%{keyword}%' for keyword in keywords])

    # 소득 수준 필터링
    if filters.income and filters.income != 'all' and filters.income != 'unknown':
        income_keywords = {
            'basic_recipient': ['기초생활', '수급자'],
            'near_poor': ['차상위'],
            'median_100': ['중위소득 100%', '중위소득100%'],
            'median_150': ['중위소득 150%', '중위소득150%']
        }
        if filters.income in income_keywords:
            keywords = income_keywords[filters.income]
            income_condition = ' OR '.join(['(support_target ILIKE %s OR selection_criteria ILIKE %s)'] * len(keywords))
            conditions.append(f'({income_condition})')
            for keyword in keywords:
                params.extend([f'%{keyword}%', f'%{keyword}%'])

    # 가구형태 필터링
    if filters.household:
        household_keywords = {
            'single': ['1인가구', '독거'],
            'couple': ['2인가구', '부부'],
            'family_3': ['3인'],
            'family_4_plus': ['4인', '5인', '다자녀']
        }
        if filters.household in household_keywords:
            keywords = household_keywords[filters.household]
            household_condition = ' OR '.join(['support_target ILIKE %s'] * len(keywords))
            conditions.append(f'({household_condition})')
            params.extend([f'%{keyword}%' for keyword in keywords])

    # 특별 대상 필터링
    if filters.targetGroup and filters.targetGroup != 'general':
        target_keywords = {
            'single_parent': ['한부모', '조손', '미혼모'],
            'disability': ['장애', '장애인'],
            'veteran': ['국가유공자', '보훈'],
            'multi_child': ['다자녀', '3자녀', '4자녀'],
            'multicultural': ['다문화', '탈북', '새터민']
        }
        if filters.targetGroup in target_keywords:
            keywords = target_keywords[filters.targetGroup]
            target_condition = ' OR '.join(['support_target ILIKE %s'] * len(keywords))
            conditions.append(f'({target_condition})')
            params.extend([f'%{keyword}%' for keyword in keywords])

    # 주거 상황 필터링
    if filters.housing and filters.housing != 'all' and filters.housing != 'unknown':
        housing_keywords = {
            'homeless': ['무주택'],
            'monthly_rent': ['월세'],
            'jeonse': ['전세'],
            'rental': ['임대'],
            'owned': ['자가']
        }
        if filters.housing in housing_keywords:
            keywords = housing_keywords[filters.housing]
            housing_condition = ' OR '.join(['support_target ILIKE %s'] * len(keywords))
            conditions.append(f'({housing_condition})')
            params.extend([f'%{keyword}%' for keyword in keywords])

    # 서비스 유형 필터링
    if filters.service_type:
        conditions.append('service_type = %s')
        params.append(filters.service_type)

    # 카테고리 필터링
    if filters.category:
        conditions.append('category = %s')
        params.append(filters.category)

    # 활성 서비스만 조회
    conditions.append("(service_status IS NULL OR service_status = 'active')")

    where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ''

    return where_clause, params

@app.get("/", tags=["Health"])
async def health_check():
    """API 상태 확인"""
    return {"status": "healthy", "message": "Welfare Service API is running"}

@app.get("/welfare-services", response_model=ServiceResponse, tags=["Welfare Services"])
async def get_welfare_services(
    gender: Optional[str] = Query(None, description="성별"),
    age: Optional[str] = Query(None, description="연령대"),
    region: Optional[str] = Query(None, description="지역"),
    income: Optional[str] = Query(None, description="소득수준"),
    targetGroup: Optional[str] = Query(None, description="대상유형"),
    household: Optional[str] = Query(None, description="가구형태"),
    housing: Optional[str] = Query(None, description="주거상황"),
    category: Optional[str] = Query(None, description="카테고리"),
    service_type: Optional[str] = Query(None, description="서비스유형"),
    limit: int = Query(50, description="결과 수 제한"),
    offset: int = Query(0, description="오프셋")
):
    """복지 서비스 목록 조회 (필터링 지원)"""

    filters = FilterRequest(
        gender=gender,
        age=age,
        region=region,
        income=income,
        targetGroup=targetGroup,
        household=household,
        housing=housing,
        category=category,
        service_type=service_type,
        limit=limit,
        offset=offset
    )

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 필터 쿼리 생성
        where_clause, params = build_filter_query(filters)

        # 총 개수 쿼리
        count_query = f"""
            SELECT COUNT(*) as total
            FROM welfare_services
            {where_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']

        # 데이터 조회 쿼리
        data_query = f"""
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
            {where_clause}
            ORDER BY
                CASE WHEN service_type = 'government' THEN 1
                     WHEN service_type = 'local' THEN 2
                     ELSE 3 END,
                view_count DESC NULLS LAST,
                service_name
            LIMIT %s OFFSET %s
        """

        cursor.execute(data_query, params + [limit, offset])
        services = cursor.fetchall()

        # 날짜 필드 문자열 변환
        formatted_services = []
        for service in services:
            service_dict = dict(service)
            for date_field in ['start_date', 'end_date', 'last_updated', 'created_at', 'updated_at']:
                if service_dict.get(date_field):
                    service_dict[date_field] = str(service_dict[date_field])
            formatted_services.append(service_dict)

        cursor.close()
        conn.close()

        return ServiceResponse(
            total=total,
            services=formatted_services,
            filters_applied=filters.dict(exclude_none=True)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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

@app.post("/api/v1/chat", response_model=ChatResponse, tags=["Chatbot"])
async def chat_with_ai(request: ChatRequest):
    """AWS Bedrock Claude를 사용한 복지 상담 챗봇"""
    try:
        # 사용자 메시지를 대화 히스토리에 추가
        all_messages = request.conversation_history + [
            ChatMessage(role="user", content=request.message)
        ]

        # AI 응답 생성
        ai_response = welfare_chatbot.chat_with_bedrock(
            messages=all_messages,
            user_profile=request.user_profile
        )

        return ChatResponse(
            response=ai_response,
            timestamp=datetime.now()
        )

    except Exception as e:
        # 오류 발생 시 폴백 응답
        print(f"챗봇 오류: {e}")
        fallback_response = """죄송합니다. 일시적으로 상담 서비스에 문제가 발생했습니다.

다음 방법으로 도움받으실 수 있습니다:
📞 다산콜센터: 120 (무료)
🏢 거주지 주민센터 방문 상담
🌐 복지로 온라인: www.bokjiro.go.kr

잠시 후 다시 시도해주세요."""

        return ChatResponse(
            response=fallback_response,
            timestamp=datetime.now()
        )

@app.post("/api/v1/chat/recommend", tags=["Chatbot"])
async def get_personalized_recommendations(user_profile: UserProfile, keywords: Optional[List[str]] = None):
    """사용자 맞춤형 복지 서비스 추천"""
    try:
        services = welfare_chatbot.search_welfare_services(user_profile, keywords or [])

        return {
            "total": len(services),
            "services": services,
            "user_profile": user_profile.dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 서비스 오류: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)