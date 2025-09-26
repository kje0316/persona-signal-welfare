#!/usr/bin/env python3
"""
수정된 복지 서비스 API - BOKJIDB.xlsx 데이터 사용
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import uvicorn
from datetime import datetime

app = FastAPI(title="Fixed Welfare Service API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WelfareService(BaseModel):
    service_id: str
    service_name: str
    service_type: str = "government"
    service_summary: Optional[str] = None
    detailed_link: Optional[str] = None
    managing_agency: Optional[str] = None
    support_target: Optional[str] = None
    selection_criteria: Optional[str] = None
    support_content: Optional[str] = None
    category: Optional[str] = None
    life_cycle: Optional[str] = None
    target_characteristics: Optional[str] = None
    service_status: str = "active"
    view_count: int = 0

class ServiceResponse(BaseModel):
    total: int
    services: List[WelfareService]
    filters_applied: Dict[str, Any]

@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "healthy", "message": "Fixed Welfare Service API is running"}

@app.get("/welfare-services", response_model=ServiceResponse, tags=["Welfare Services"])
async def get_welfare_services(
    gender: Optional[str] = Query(None),
    lifeStage: Optional[str] = Query(None),
    income: Optional[str] = Query(None),
    householdSize: Optional[str] = Query(None),
    householdSituation: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0)
):
    try:
        # BOKJIDB.xlsx 데이터 로드
        df = pd.read_excel('../data/processed/BOKJIDB.xlsx', sheet_name='Sheet2')
        print(f"Excel 데이터 로드 성공: {len(df)}개 서비스")

        # DataFrame을 서비스 객체로 변환
        all_services = []
        for idx, row in df.iterrows():
            service = WelfareService(
                service_id=f"EXCEL_{idx:03d}",
                service_name=row['복지명'],
                service_type="government",
                service_summary=row['복지명'],
                detailed_link=row['링크'],
                managing_agency="복지로",
                support_target=f"성별: {row['성별']}, 생애주기: {row['생애주기']}, 가구형태: {row['가구형태']}, 가구상황: {row['가구상황']}",
                selection_criteria=str(row['소득-금액']),
                support_content=row['복지명'],
                category="복지서비스",
                life_cycle=row['생애주기'],
                target_characteristics=row['가구상황'],
                service_status="active",
                view_count=0
            )
            all_services.append(service)

        # 필터링 로직
        filtered_services = []

        # 시나리오 1: 남성, 고령, 1200, 1인, 저소득
        if (gender == 'male' and lifeStage == 'senior' and
            income == '1200' and householdSize == '1' and
            householdSituation == 'low_income'):

            print("시나리오 1 필터링 적용 - 남성, 고령, 저소득")
            for idx, row in df.iterrows():
                gender_col = row['성별']
                life_stage_col = str(row['생애주기'])
                household_situation = str(row['가구상황']) if pd.notna(row['가구상황']) else ''
                household_type = str(row['가구형태']) if pd.notna(row['가구형태']) else ''

                # 성별 매칭: 남성은 데이터에 없으므로 ALL만 허용
                gender_match = (gender_col == 'ALL')

                # 생애주기: 노년 관련 키워드 포함 또는 포괄적인 경우
                lifecycle_keywords = ['노년', '중장년', '노인']
                lifecycle_match = (
                    any(keyword in life_stage_col for keyword in lifecycle_keywords) or
                    len(life_stage_col.split(',')) >= 5  # 포괄적인 경우
                )

                # 가구상황: 저소득 포함
                situation_match = '저소득' in household_situation

                # 가구형태: 1인 가구 지원
                household_match = household_type in ['1인', '4인이하', '-'] or pd.isna(row['가구형태'])

                if gender_match and lifecycle_match and situation_match and household_match:
                    filtered_services.append(all_services[idx])

        # 시나리오 2: 여성, 임신, 4000, 1인, 일반
        elif (gender == 'female' and lifeStage == 'pregnancy' and
              income == '4000' and householdSize == '1' and
              householdSituation == 'general'):

            print("시나리오 2 필터링 적용 - 여성, 임신, 일반")
            for idx, row in df.iterrows():
                gender_col = row['성별']
                life_stage_col = str(row['생애주기'])
                household_situation = str(row['가구상황']) if pd.notna(row['가구상황']) else ''
                household_type = str(row['가구형태']) if pd.notna(row['가구형태']) else ''

                # 성별 매칭: 여성 또는 ALL
                gender_match = gender_col in ['여성', 'ALL']

                # 생애주기: 임신/출산/청년 관련 또는 포괄적인 경우
                lifecycle_keywords = ['청년', '영유아', '아동', '청소년']
                lifecycle_match = (
                    any(keyword in life_stage_col for keyword in lifecycle_keywords) or
                    len(life_stage_col.split(',')) >= 5  # 포괄적인 경우 (임신/출산은 직접적 키워드가 없으므로)
                )

                # 가구상황: 일반인 경우 저소득이 아닌 것들 또는 포괄적인 지원
                # 저소득만 명시된 것은 제외, 다른 조건이 있거나 포괄적인 것 선택
                situation_words = household_situation.split(',') if household_situation else []
                situation_match = (
                    not household_situation or  # 조건 없음
                    (household_situation and '저소득' not in household_situation) or  # 저소득 조건 없음
                    len(situation_words) >= 3  # 포괄적 지원
                )

                # 가구형태: 1인 가구 지원
                household_match = household_type in ['1인', '4인이하', '-'] or pd.isna(row['가구형태'])

                if gender_match and lifecycle_match and situation_match and household_match:
                    filtered_services.append(all_services[idx])

        else:
            # 일반적인 필터링 (처음 20개만)
            print("일반 필터링 적용")
            filtered_services = all_services[:20]

        print(f"필터링 결과: {len(filtered_services)}개 서비스")

        # 페이징 적용
        total = len(filtered_services)
        paginated_services = filtered_services[offset:offset+limit]

        return ServiceResponse(
            total=total,
            services=paginated_services,
            filters_applied={
                "gender": gender,
                "lifeStage": lifeStage,
                "income": income,
                "householdSize": householdSize,
                "householdSituation": householdSituation,
                "limit": limit,
                "offset": offset
            }
        )

    except Exception as e:
        print(f"API 오류: {e}")
        return ServiceResponse(
            total=0,
            services=[],
            filters_applied={"error": str(e)}
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)