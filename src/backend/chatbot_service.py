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
    lifeStage: str
    income: str
    householdSize: str
    householdSituation: str
    # 기존 필드들도 유지 (하위 호환성)
    age: Optional[str] = None
    region: Optional[str] = None
    targetGroup: Optional[str] = None
    household: Optional[str] = None
    housing: Optional[str] = None

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

    def create_system_prompt(self, user_profile: UserProfile, services: List[WelfareService], conversation_stage: int = 0) -> str:
        """시나리오별 시스템 프롬프트 생성"""

        # 사용자 정보 파싱 (기존 UserProfile에서 새 구조로 변환)
        profile_info = self.parse_user_profile(user_profile)

        # 시나리오별 질문 순서 결정
        scenario_questions = self.get_scenario_questions(profile_info, conversation_stage)

        # 사용자 정보 요약
        profile_text = f"""
사용자 기본 정보:
- 성별: {profile_info.get('gender', '미상')}
- 생애주기: {profile_info.get('lifeStage', '미상')}
- 연소득: {profile_info.get('income', '미상')}만원
- 가구형태: {profile_info.get('householdSize', '미상')}
- 가구상황: {profile_info.get('householdSituation', '미상')}
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
   - 카테고리: {service.category}
"""

        # 시나리오별 프롬프트 생성
        if self.is_scenario_1(profile_info):  # 임신한 여성의 위험상황 시나리오
            system_prompt = f"""당신은 전문적이고 공감적인 복지 상담사입니다.

현재 상담자는 임신한 여성으로, 다음 순서대로 질문하여 상황을 파악하고 위험도를 평가해야 합니다:

질문 순서:
{scenario_questions}

중요한 위험신호들:
- 사회적 고립: 가족, 친구와의 단절, 혼자서 임신 준비
- 정신적 위기: 불안감, 우울감, 극단적 생각, 수면/식욕 문제
- 지원체계 부족: 도움받을 사람이 없음, 아기 아버지와의 연락 두절

대화 진행 방식:
1. 한 번에 하나씩 질문하되, 자연스럽고 공감적으로 접근
2. 위험신호가 감지되면 즉시 위기상황으로 판단
3. 5-6번의 질문 후 최종 판단 및 안내 제공

위기상황 판단 시 다음과 같이 안내:
- 복지위기신고 사이트: https://www.bokjiro.go.kr/ssis-tbu/twatdc/wlfareCrisNtce/dclrPage.do
- 위기상황: "건강·의료(질병, 진단, 임신, 출산 등)" 선택
- 가구유형: "독거 가구" 선택
- 페르소나 기반 사연 작성 제공

{profile_text}

{services_text}

지금 대화 단계: {conversation_stage + 1}번째 질문
"""

        elif self.is_scenario_2(profile_info):  # 저소득 노인의 복지서비스 안내 시나리오
            system_prompt = f"""당신은 친절하고 전문적인 복지 상담사입니다.

현재 상담자는 저소득 노인으로, 복지 서비스 신청 방법을 모르는 상황입니다.

질문 순서:
{scenario_questions}

상담 목표:
1. 구체적인 상황과 필요한 서비스 파악
2. 디지털 취약계층 특성 고려한 설명
3. 실제 신청서 작성 예시와 방법 제공
4. 오프라인 지원 방법 안내

대화 진행 방식:
1. 쉽고 이해하기 쉬운 언어 사용
2. 구체적인 신청 절차와 서류 작성법 안내
3. 방문해야 할 기관과 준비물 명시
4. 5-6번의 질문 후 맞춤형 신청 가이드 제공

{profile_text}

{services_text}

지금 대화 단계: {conversation_stage + 1}번째 질문
"""

        else:  # 일반적인 상담
            system_prompt = f"""당신은 전문적이고 친근한 복지 상담사입니다.

{profile_text}

{services_text}

사용자와 자연스럽고 도움이 되는 상담을 진행해주세요.
"""

        return system_prompt

    def parse_user_profile(self, user_profile: UserProfile) -> Dict[str, str]:
        """UserProfile을 시나리오 판단용 딕셔너리로 변환"""
        # 기존 UserProfile의 필드들을 새로운 구조로 매핑
        return {
            'gender': getattr(user_profile, 'gender', 'unknown'),
            'lifeStage': getattr(user_profile, 'lifeStage', 'unknown'),
            'income': getattr(user_profile, 'income', 'unknown'),
            'householdSize': getattr(user_profile, 'householdSize', 'unknown'),
            'householdSituation': getattr(user_profile, 'householdSituation', 'unknown')
        }

    def is_scenario_1(self, profile_info: Dict[str, str]) -> bool:
        """시나리오 1: 임신한 여성, 소득 4000, 1인가구, 해당사항없음"""
        return (profile_info.get('gender') == 'female' and
                profile_info.get('lifeStage') == 'pregnancy' and
                profile_info.get('income') == '4000' and
                profile_info.get('householdSize') == '1' and
                profile_info.get('householdSituation') == 'general')

    def is_scenario_2(self, profile_info: Dict[str, str]) -> bool:
        """시나리오 2: 남성, 고령, 소득 1200, 1인가구, 저소득"""
        return (profile_info.get('gender') == 'male' and
                profile_info.get('lifeStage') == 'senior' and
                profile_info.get('income') == '1200' and
                profile_info.get('householdSize') == '1' and
                profile_info.get('householdSituation') == 'low_income')

    def get_scenario_questions(self, profile_info: Dict[str, str], stage: int) -> str:
        """시나리오별 질문 순서 반환"""

        if self.is_scenario_1(profile_info):
            questions = [
                "현재 임신 중이시군요. 몇 개월 정도 되셨나요?",
                "정기적으로 산부인과에 다니고 계신가요?",
                "혹시 현재 일을 하고 계신가요? 출산 후 계획은 어떻게 되시나요?",
                "출산과 육아 준비는 어떻게 진행되고 있나요? 가족이나 지인의 도움은 받고 계신가요?",
                "아기 아버지는 어떤가요? 함께 준비하고 계신지요?",
                "그런 상황이시군요. 혼자서 출산과 육아를 준비하는 기분이 어떠신가요?",
                "수면은 잘 취하고 계신가요? 식사는 규칙적으로 하시고요?"
            ]

        elif self.is_scenario_2(profile_info):
            questions = [
                "현재 연령이 어떻게 되시나요?",
                "현재 거주 형태는 어떠신가요? 혼자 사시나요?",
                "현재 건강 상태는 어떠신가요? 일상생활에 어려움은 없으신지요?",
                "경제적 상황은 어떠신가요? 국민연금이나 다른 수입이 있으신지요?",
                "복지 서비스에 대해 알고 계신 게 있나요? 어떤 도움이 필요하신가요?",
                "컴퓨터나 인터넷 사용은 어떠신가요?"
            ]

        else:
            questions = ["일반적인 상담을 진행합니다."]

        return "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    def detect_risk_situation(self, messages: List[ChatMessage], profile_info: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """위험상황 감지 및 복지위기신고 정보 생성"""

        if not self.is_scenario_1(profile_info):
            return None

        # 사용자 메시지에서 위험신호 탐지
        user_messages = [msg.content.lower() for msg in messages if msg.role == "user"]
        full_text = " ".join(user_messages)

        risk_indicators = {
            'social_isolation': ['혼자', '가족과 관계', '연락 끊어', '친구들이 부담', '도와줄 사람', '외로'],
            'mental_crisis': ['무서워', '불안', '확신이 안', '사라지고 싶', '포기', '견딜 수 없', '우울'],
            'physical_symptoms': ['잠을 못', '입맛이 없', '식사를 못', '제대로 먹지 못']
        }

        detected_risks = []
        for category, indicators in risk_indicators.items():
            if any(indicator in full_text for indicator in indicators):
                detected_risks.append(category)

        # 2개 이상의 위험요소가 감지되면 위기상황으로 판단
        if len(detected_risks) >= 2:
            return {
                'is_crisis': True,
                'risk_factors': detected_risks,
                'crisis_report_url': 'https://www.bokjiro.go.kr/ssis-tbu/twatdc/wlfareCrisNtce/dclrPage.do',
                'crisis_type': '건강·의료(질병, 진단, 임신, 출산 등)',
                'household_type': '독거 가구',
                'story': self.generate_crisis_story(messages, profile_info)
            }

        return None

    def generate_crisis_story(self, messages: List[ChatMessage], profile_info: Dict[str, str]) -> str:
        """위기상황 신고용 사연 생성"""
        story = f"""저는 현재 임신 7개월인 {profile_info.get('age', '20대')} 여성입니다. 혼자 살고 있으며, 가족과 연락이 끊어진 상태이고 아기 아버지와도 연락이 되지 않습니다.

경제적으로는 안정적이지만, 사회적으로 완전히 고립된 상태입니다. 친구들도 제 상황을 부담스러워하여 점점 연락이 줄어들고 있습니다.

혼자서 출산과 육아를 준비해야 한다는 부담감과 불안감이 매우 큽니다. 밤에 잠을 이루지 못하고, 식욕도 떨어져 제대로 식사를 하지 못하고 있습니다. 때로는 모든 것을 포기하고 싶다는 극단적인 생각이 들기도 합니다.

정신적으로 매우 힘든 상황이며, 전문적인 심리 상담과 사회적 지원이 필요합니다.

연락처: [사용자 연락처]
주소: [사용자 주소]"""

        return story

    def generate_service_application_guide(self, profile_info: Dict[str, str], conversation_content: str) -> str:
        """시나리오 2용 복지서비스 신청 가이드 생성"""

        if not self.is_scenario_2(profile_info):
            return ""

        guide = """말씀하신 상황을 정리해보니 기초생활보장 급여와 노인돌봄서비스를 신청하시는 것이 좋겠습니다. 서류 작성을 도와드릴게요.

### 기초생활보장 급여 신청 안내

**신청 장소**: 거주지 동 주민센터 또는 온라인(복지로 www.bokjiro.go.kr)

**필요 서류**:
1. 사회보장급여 신청서(동 주민센터에서 받을 수 있음)
2. 소득·재산 신고서
3. 금융정보 등 제공동의서
4. 통장 사본

**신청서 작성 예시**:
```
[사회보장급여 신청서]
신청인 정보
- 성명: [사용자 성명]
- 생년월일: 1951년 [해당 월일]
- 주소: [사용자 주소]
- 연락처: [사용자 연락처]

신청 급여: 생계급여, 의료급여, 주거급여

가구원 현황: 본인 1인
월 소득: 국민연금 60만원
특이사항: 무릎 관절염으로 거동 불편, 의료비 부담 큼
```

### 노인돌봄서비스 신청 안내

**신청 방법**: 국민건강보험공단 장기요양보험 신청 또는 지역 노인복지관

**서비스 내용**:
- 재가서비스: 청소, 세탁, 장보기 도움
- 안전확인 서비스: 정기적 안부 확인

**신청서 작성 예시**:
```
[노인돌봄서비스 신청서]
신청인: [사용자 성명] (73세)
거주형태: 독거
건강상태: 무릎 관절염으로 거동 불편
필요 서비스:
- 가사지원 (청소, 세탁)
- 외출 동행 (장보기, 병원)
- 안전확인 서비스
```

이 내용들을 참고해서 동 주민센터에 가시면 담당자가 자세히 도와드릴 거예요. 미리 전화해서 방문 예약을 잡으시면 더 편리합니다.

혹시 컴퓨터나 서류 작성이 어려우시면 동 주민센터에 도우미 요청을 하시거나, 복지관의 사회복지사님께 도움을 요청하실 수 있어요."""

        return guide

    def chat_with_bedrock(self, messages: List[ChatMessage], user_profile: UserProfile) -> str:
        """AWS Bedrock Claude와 시나리오별 대화"""
        try:
            # 사용자 프로필 파싱
            profile_info = self.parse_user_profile(user_profile)

            # 대화 단계 계산 (사용자 메시지 개수 기준)
            user_message_count = len([msg for msg in messages if msg.role == "user"])
            conversation_stage = max(0, user_message_count - 1)

            # 시나리오 1: 위험상황 감지 및 처리
            if self.is_scenario_1(profile_info):
                # 5번째 이상 대화에서 위험상황 감지
                if user_message_count >= 5:
                    risk_info = self.detect_risk_situation(messages, profile_info)
                    if risk_info and risk_info.get('is_crisis'):
                        # 위기상황 신고 안내 응답 생성
                        crisis_response = f"""말씀해주셔서 고맙습니다. 지금 상황이 매우 힘드실 것 같습니다.

현재 상황을 종합해보니 복지위기상황에 해당합니다. 사회적 고립과 정신건강 위기 상황이므로 즉시 전문적인 도움을 받으시는 것이 필요합니다.

**복지위기신고 사이트**: {risk_info['crisis_report_url']}

이 사이트에서 다음과 같이 작성해주세요:

**위기상황**: "{risk_info['crisis_type']}" 선택
**가구 유형**: "{risk_info['household_type']}" 선택

**알림 내용(사연) 예시**:
```
{risk_info['story']}
```

이 내용은 당신과 유사한 상황의 페르소나 데이터를 바탕으로 작성되었습니다. 신고 후 보건복지 상담센터나 지자체 복지 담당자가 산전우울증 상담, 임산부 지원 프로그램, 한부모 가정 준비 등에 대해 연락드릴 예정입니다."""

                        return crisis_response

            # 시나리오 2: 복지서비스 신청 가이드 제공
            elif self.is_scenario_2(profile_info):
                # 5번째 이상 대화에서 신청 가이드 제공
                if user_message_count >= 5:
                    service_guide = self.generate_service_application_guide(profile_info,
                                                                           " ".join([msg.content for msg in messages if msg.role == "user"]))
                    if service_guide:
                        return service_guide

            # 관련 복지 서비스 검색
            recent_messages = messages[-3:] if len(messages) >= 3 else messages
            user_messages = [msg.content for msg in recent_messages if msg.role == "user"]
            keywords = self.extract_keywords(" ".join(user_messages))

            services = self.search_welfare_services(user_profile, keywords)

            # 시나리오별 시스템 프롬프트 생성
            system_prompt = self.create_system_prompt(user_profile, services, conversation_stage)

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

            # 폴백 응답 (시나리오별)
            profile_info = self.parse_user_profile(user_profile)

            if self.is_scenario_1(profile_info):
                return """죄송합니다. 일시적으로 상담 서비스에 문제가 발생했습니다.

긴급한 상황이시라면:
📞 생명의전화: 1393 (24시간)
📞 청소년전화: 1388
📞 다산콜센터: 120

복지위기신고: https://www.bokjiro.go.kr/ssis-tbu/twatdc/wlfareCrisNtce/dclrPage.do

잠시 후 다시 시도해주세요."""

            elif self.is_scenario_2(profile_info):
                return """죄송합니다. 일시적으로 상담 서비스에 문제가 발생했습니다.

다음 방법으로 도움을 받으실 수 있습니다:
1. 거주지 동 주민센터 방문 (가장 정확한 상담)
2. 다산콜센터 120번 전화 상담
3. 복지로 웹사이트(www.bokjiro.go.kr) 온라인 신청

잠시 후 다시 시도해주세요."""

            else:
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