#!/usr/bin/env python3
"""
AWS Bedrock을 활용한 복지 상담 챗봇 서비스
"""

import boto3
import json
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# 데이터베이스 연결 정보
DB_CONFIG = {
    'host': 'seoul-ht-11.cpk0oamsu0g6.us-west-1.rds.amazonaws.com',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'yeardream11!!'
}

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class UserProfile(BaseModel):
    gender: str
    age: str
    region: str
    income: str
    targetGroup: str
    household: str
    housing: str

class WelfareService(BaseModel):
    service_id: str
    service_name: str
    service_summary: str
    support_target: str
    support_content: str
    application_method: str
    required_documents: str
    managing_agency: str
    category: str

class WelfareChatbot:
    def __init__(self):
        # AWS Bedrock 클라이언트 초기화 (IAM Role 사용)
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name='us-east-1'  # Bedrock Claude 지원 리전
        )

        # Claude 3 모델 ID
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    def get_db_connection(self):
        """데이터베이스 연결"""
        return psycopg2.connect(**DB_CONFIG)

    def search_welfare_services(self, user_profile: UserProfile, keywords: List[str] = None) -> List[WelfareService]:
        """사용자 프로필과 키워드를 기반으로 복지 서비스 검색"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 기본 조건 생성
            conditions = ["(service_status IS NULL OR service_status = 'active')"]
            params = []

            # 연령대 조건
            if user_profile.age and user_profile.age != 'all':
                age_keywords = {
                    'child': ['아동', '청소년', '영유아', '18세 이하'],
                    'youth': ['청년', '19', '20', '30'],
                    'middle': ['중장년', '40', '50', '60'],
                    'senior': ['노인', '65세', '70', '80']
                }
                if user_profile.age in age_keywords:
                    keywords_list = age_keywords[user_profile.age]
                    age_condition = ' OR '.join(['support_target ILIKE %s'] * len(keywords_list))
                    conditions.append(f'({age_condition})')
                    params.extend([f'%{keyword}%' for keyword in keywords_list])

            # 소득 조건
            if user_profile.income and user_profile.income != 'all':
                income_keywords = {
                    'basic_recipient': ['기초생활', '수급자'],
                    'near_poor': ['차상위'],
                    'median_100': ['중위소득 100%', '중위소득100%'],
                    'median_150': ['중위소득 150%', '중위소득150%']
                }
                if user_profile.income in income_keywords:
                    income_kws = income_keywords[user_profile.income]
                    income_condition = ' OR '.join(['(support_target ILIKE %s OR selection_criteria ILIKE %s)'] * len(income_kws))
                    conditions.append(f'({income_condition})')
                    for keyword in income_kws:
                        params.extend([f'%{keyword}%', f'%{keyword}%'])

            # 추가 키워드 검색
            if keywords:
                keyword_conditions = []
                for keyword in keywords:
                    keyword_conditions.append(
                        "(service_name ILIKE %s OR service_summary ILIKE %s OR support_target ILIKE %s OR support_content ILIKE %s)"
                    )
                    params.extend([f'%{keyword}%'] * 4)

                if keyword_conditions:
                    conditions.append(f"({' OR '.join(keyword_conditions)})")

            # 쿼리 실행
            query = f"""
                SELECT
                    service_id, service_name, service_summary, support_target,
                    support_content, application_method, required_documents,
                    managing_agency, category
                FROM welfare_services
                WHERE {' AND '.join(conditions)}
                ORDER BY view_count DESC NULLS LAST
                LIMIT 10
            """

            cursor.execute(query, params)
            services = cursor.fetchall()

            cursor.close()
            conn.close()

            return [WelfareService(**dict(service)) for service in services]

        except Exception as e:
            print(f"서비스 검색 오류: {e}")
            return []

    def create_system_prompt(self, user_profile: UserProfile, services: List[WelfareService]) -> str:
        """시스템 프롬프트 생성"""

        # 사용자 정보 요약
        profile_text = f"""
사용자 기본 정보:
- 성별: {user_profile.gender}
- 연령대: {user_profile.age}
- 거주지역: {user_profile.region}
- 소득수준: {user_profile.income}
- 대상유형: {user_profile.targetGroup}
- 가구형태: {user_profile.household}
- 주거상황: {user_profile.housing}
"""

        # 검색된 서비스 정보
        services_text = ""
        if services:
            services_text = "\n\n추천 가능한 복지 서비스:\n"
            for i, service in enumerate(services, 1):
                services_text += f"""
{i}. {service.service_name} (관리기관: {service.managing_agency})
   - 지원대상: {service.support_target}
   - 지원내용: {service.support_content}
   - 신청방법: {service.application_method}
   - 제출서류: {service.required_documents}
   - 카테고리: {service.category}
"""

        system_prompt = f"""당신은 전문적이고 친근한 복지 상담사입니다. 다음 역할을 수행해주세요:

1. 역할과 목적:
   - 사용자의 상황을 자세히 파악하여 적절한 복지 서비스를 추천
   - 서류 준비나 신청 방법에 대해 구체적으로 안내
   - 따뜻하고 공감적인 상담 제공

2. 상담 방식:
   - 사용자의 어려움을 공감하고 이해하는 자세
   - 명확하고 실용적인 정보 제공
   - 단계별로 차근차근 설명

3. 주요 확인사항:
   - 현재 가장 큰 어려움이나 필요한 도움
   - 구체적인 가족 구성원이나 부양가족 상황
   - 건강상 문제나 특별한 상황
   - 이전 복지 서비스 경험
   - 경제적 상황의 구체적인 어려움

{profile_text}

{services_text}

위 정보를 바탕으로 사용자와 자연스럽고 도움이 되는 상담을 진행해주세요.
긴급상황이나 위험신호가 감지되면 즉시 관련 기관 연락처를 안내하세요.
"""

        return system_prompt

    def chat_with_bedrock(self, messages: List[ChatMessage], user_profile: UserProfile) -> str:
        """AWS Bedrock Claude와 대화"""
        try:
            # 관련 복지 서비스 검색
            # 최근 메시지에서 키워드 추출
            recent_messages = messages[-3:] if len(messages) >= 3 else messages
            user_messages = [msg.content for msg in recent_messages if msg.role == "user"]
            keywords = self.extract_keywords(" ".join(user_messages))

            services = self.search_welfare_services(user_profile, keywords)

            # 시스템 프롬프트 생성
            system_prompt = self.create_system_prompt(user_profile, services)

            # Claude API 메시지 형식으로 변환
            claude_messages = []
            for msg in messages:
                claude_messages.append({
                    "role": msg.role if msg.role in ["user", "assistant"] else "user",
                    "content": msg.content
                })

            # API 호출을 위한 body 구성
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "system": system_prompt,
                "messages": claude_messages,
                "temperature": 0.7
            }

            # Bedrock API 호출
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )

            # 응답 파싱
            response_body = json.loads(response['body'].read())

            return response_body['content'][0]['text']

        except Exception as e:
            print(f"Bedrock API 호출 오류: {e}")

            # 폴백 응답
            return """죄송합니다. 일시적으로 AI 상담 서비스에 문제가 발생했습니다.

다음 방법으로 도움을 받으실 수 있습니다:
1. 거주지 주민센터 방문 (가장 정확한 상담)
2. 다산콜센터 120번 전화 상담
3. 복지로 웹사이트(www.bokjiro.go.kr) 온라인 신청

잠시 후 다시 시도해주시거나, 위 방법으로 상담받아보시기 바랍니다."""

    def extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 복지 관련 키워드 추출"""
        welfare_keywords = [
            # 생활비 관련
            '생활비', '월세', '전세', '주거비', '의료비', '교육비',
            # 상황 관련
            '실업', '질병', '장애', '임신', '육아', '노인돌봄',
            # 지원 형태
            '현금', '바우처', '서비스', '상담', '치료', '교육',
            # 긴급 상황
            '긴급', '위기', '응급', '도움'
        ]

        found_keywords = []
        text_lower = text.lower()

        for keyword in welfare_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)

        return found_keywords[:5]  # 최대 5개까지만

# 챗봇 인스턴스 생성
welfare_chatbot = WelfareChatbot()