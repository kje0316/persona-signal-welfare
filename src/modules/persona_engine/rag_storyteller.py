# -*- coding: utf-8 -*-
"""
rag_storyteller.py
RAG 시스템을 활용한 페르소나 스토리텔링 엔진
"""

import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re

@dataclass
class PersonaStory:
    """페르소나의 구체적인 스토리"""
    persona_id: int
    character_name: str
    background_story: str
    daily_routine: str
    challenges: List[str]
    aspirations: List[str]
    welfare_journey: str
    realistic_scenarios: List[str]

class RAGKnowledgeBase:
    """RAG 지식 베이스 관리"""

    def __init__(self, kb_chunks_path: str = None, policy_docs_path: str = None):
        self.feature_knowledge = {}
        self.policy_knowledge = {}
        self.statistical_insights = {}

        if kb_chunks_path and os.path.exists(kb_chunks_path):
            self.load_kb_chunks(kb_chunks_path)

        if policy_docs_path and os.path.exists(policy_docs_path):
            self.load_policy_docs(policy_docs_path)

    def load_kb_chunks(self, path: str):
        """kb_chunks.jsonl에서 통계적 지식 로드"""
        print(f"📖 지식 베이스 로딩: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunk = json.loads(line.strip())
                    chunk_type = chunk.get('meta', {}).get('type', 'general')

                    if chunk_type == 'overview':
                        self.statistical_insights['overview'] = chunk['text']
                    elif chunk_type == 'feature_mapping':
                        self.feature_knowledge['mapping'] = chunk['text']
                    elif chunk_type == 'coverage':
                        self.statistical_insights['coverage'] = chunk['text']

    def load_policy_docs(self, docs_path: str):
        """정책 문서 디렉토리에서 복지 정보 로드"""
        docs_dir = Path(docs_path)
        if not docs_dir.exists():
            return

        for file_path in docs_dir.glob("*.txt"):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.policy_knowledge[file_path.stem] = content

    def get_feature_insights(self, feature_name: str) -> List[str]:
        """특정 피처에 대한 통계적 인사이트 추출"""
        insights = []

        # 매핑 정보에서 관련 내용 찾기
        if 'mapping' in self.feature_knowledge:
            mapping_text = self.feature_knowledge['mapping']
            if feature_name in mapping_text:
                # 해당 피처와 관련된 라인 추출
                lines = mapping_text.split('\n')
                for line in lines:
                    if feature_name in line:
                        insights.append(line.strip())

        return insights

    def get_welfare_policy_context(self, welfare_category: str) -> str:
        """복지 카테고리별 정책 컨텍스트 제공"""
        category_mapping = {
            'LIVELIHOOD': '생계지원',
            'CARE': '돌봄서비스',
            'HEALTH_MENTAL_DELTA': '정신건강',
            'DAILY_LONGTERM': '일상지원',
            'HOUSING': '주거지원',
            'EMPLOYMENT': '고용지원',
            'ISOLATION': '사회참여'
        }

        korean_category = category_mapping.get(welfare_category, welfare_category)

        # 관련 정책 문서에서 정보 찾기
        for doc_name, content in self.policy_knowledge.items():
            if korean_category in content or welfare_category.lower() in doc_name.lower():
                # 관련 문단 추출 (첫 200자)
                return content[:200] + "..."

        # 기본 컨텍스트 제공
        default_contexts = {
            'LIVELIHOOD': "기초생활보장제도를 통해 최저생계비를 지원하며, 긴급복지지원으로 위기상황에 대응합니다.",
            'CARE': "노인장기요양보험과 지역사회 돌봄서비스를 통해 케어 서비스를 제공합니다.",
            'HEALTH_MENTAL_DELTA': "정신건강증진센터와 상담 프로그램을 통해 정신건강 문제에 대응합니다.",
            'DAILY_LONGTERM': "일상생활 지원서비스와 가사도우미를 통해 독립적 생활을 돕습니다.",
            'HOUSING': "주거급여와 전세자금지원을 통해 주거 안정성을 확보합니다.",
            'EMPLOYMENT': "취업지원센터와 직업훈련을 통해 경제활동을 지원합니다.",
            'ISOLATION': "사회참여 프로그램과 커뮤니티 활동을 통해 사회적 연결을 강화합니다."
        }

        return default_contexts.get(welfare_category, "관련 복지 서비스를 제공합니다.")

class PersonaStoryTeller:
    """페르소나 스토리 생성 엔진"""

    def __init__(self, knowledge_base: RAGKnowledgeBase):
        self.kb = knowledge_base

        # 스토리 템플릿
        self.name_pools = {
            'male_young': ['김민준', '이도윤', '박시우', '최준서', '정하준'],
            'male_middle': ['김성호', '이재영', '박동현', '최민석', '정상우'],
            'male_senior': ['김병수', '이광호', '박종민', '최영수', '정덕수'],
            'female_young': ['김지우', '이서연', '박하은', '최민서', '정소율'],
            'female_middle': ['김미영', '이은정', '박선희', '최수연', '정현주'],
            'female_senior': ['김순자', '이영희', '박금순', '최말순', '정복순']
        }

        self.district_contexts = {
            '강남구': '고급 주거지역으로 인프라가 잘 발달된 지역',
            '관악구': '대학가 근처로 젊은 층이 많은 주거지역',
            '은평구': '조용한 주거환경의 서북권 지역',
            '송파구': '잠실 일대의 신도시 지역',
            '성북구': '전통적인 주거지역으로 다양한 계층이 거주'
        }

    def select_name(self, gender: str, age_group: str, persona_id: int) -> str:
        """성별과 연령대에 맞는 이름 선택"""
        if age_group == '청년층':
            age_key = 'young'
        elif age_group == '중년층':
            age_key = 'middle'
        else:
            age_key = 'senior'

        gender_key = 'male' if gender == '남성' else 'female'
        pool_key = f"{gender_key}_{age_key}"

        name_pool = self.name_pools.get(pool_key, ['김철수', '이영희'])
        return name_pool[persona_id % len(name_pool)]

    def generate_background_story(self, persona_profile: Dict[str, Any]) -> str:
        """페르소나의 배경 스토리 생성"""
        name = persona_profile['name']
        age_group = persona_profile['age_group']
        district = persona_profile['district']
        mobility = persona_profile['mobility_level']
        digital = persona_profile['digital_engagement']
        social = persona_profile['social_connectivity']

        district_desc = self.district_contexts.get(district, f"{district} 지역")

        # 연령대별 배경 설정
        if age_group == '청년층':
            base_story = f"{name}님은 20대 후반의 1인가구로 {district_desc}에 거주하고 있습니다."

            if mobility == '높음':
                base_story += " 활동적인 성격으로 자주 외출하며 다양한 활동에 참여합니다."
            elif mobility == '낮음':
                base_story += " 주로 집에서 시간을 보내며 외출은 필요한 경우에만 하는 편입니다."

        elif age_group == '중년층':
            base_story = f"{name}님은 40대의 1인가구로 {district_desc}에서 독립적인 생활을 하고 있습니다."

            if social == '낮음':
                base_story += " 혼자만의 시간을 중요하게 여기며 조용한 생활을 선호합니다."
            else:
                base_story += " 적절한 사회활동을 유지하며 균형잡힌 생활을 추구합니다."

        else:  # 노년층
            base_story = f"{name}님은 65세 이상의 고령 1인가구로 {district_desc}에서 오랫동안 거주해왔습니다."
            base_story += " 건강 관리와 안전한 생활환경 유지에 관심이 많습니다."

        # 디지털 활용도 반영
        if digital == '높음':
            base_story += " 온라인 서비스와 디지털 콘텐츠 활용에 능숙합니다."
        elif digital == '낮음':
            base_story += " 디지털 기기 사용에 어려움을 느끼는 편입니다."

        return base_story

    def generate_daily_routine(self, persona_profile: Dict[str, Any]) -> str:
        """일상 루틴 생성"""
        mobility = persona_profile['mobility_level']
        digital = persona_profile['digital_engagement']
        age_group = persona_profile['age_group']

        routine_parts = []

        # 기상 시간
        if age_group == '노년층':
            routine_parts.append("오전 6시경 기상하여 가벼운 스트레칭으로 하루를 시작합니다.")
        elif age_group == '청년층':
            routine_parts.append("오전 7-8시경 기상하여 출근 준비를 합니다.")
        else:
            routine_parts.append("오전 7시경 규칙적으로 기상합니다.")

        # 활동 패턴
        if mobility == '높음':
            routine_parts.append("평일에는 대중교통을 이용해 다양한 곳을 이동하며 활발한 외부활동을 합니다.")
            if digital == '높음':
                routine_parts.append("이동 중에는 스마트폰으로 동영상 시청이나 SNS 활용을 즐깁니다.")
        elif mobility == '낮음':
            routine_parts.append("집 근처에서 주로 생활하며 필요한 외출만 하는 편입니다.")
            if digital == '높음':
                routine_parts.append("집에서 온라인 쇼핑이나 배달 서비스를 자주 이용합니다.")
            else:
                routine_parts.append("전화나 직접 방문을 통해 필요한 업무를 처리합니다.")

        # 저녁 시간
        routine_parts.append("저녁에는 집에서 휴식을 취하며 하루를 마무리합니다.")

        return " ".join(routine_parts)

    def generate_challenges(self, persona_profile: Dict[str, Any]) -> List[str]:
        """페르소나가 직면한 도전과제 생성"""
        challenges = []
        welfare_needs = persona_profile.get('welfare_needs', {})
        risk_factors = persona_profile.get('risk_factors', [])

        # 복지 욕구별 도전과제 매핑
        high_need_categories = [k for k, v in welfare_needs.items() if v > 0.6]

        for category in high_need_categories:
            if 'LIVELIHOOD' in category:
                challenges.append("경제적 어려움으로 인한 생계비 부담")
            elif 'ISOLATION' in category:
                challenges.append("사회적 고립감과 외로움 문제")
            elif 'HEALTH' in category:
                challenges.append("정신적 스트레스와 건강 관리의 어려움")
            elif 'HOUSING' in category:
                challenges.append("주거 안정성에 대한 불안감")
            elif 'EMPLOYMENT' in category:
                challenges.append("안정적인 일자리 확보의 어려움")

        # 기본 도전과제 (1인가구 공통)
        if not challenges:
            challenges.extend([
                "1인가구로서의 외로움과 고립감",
                "응급상황 시 도움을 받을 수 있는 네트워크 부족",
                "혼자서 모든 일상생활을 처리해야 하는 부담"
            ])

        return challenges[:3]  # 최대 3개까지

    def generate_aspirations(self, persona_profile: Dict[str, Any]) -> List[str]:
        """페르소나의 희망사항 생성"""
        aspirations = []
        age_group = persona_profile['age_group']
        social = persona_profile['social_connectivity']

        if age_group == '청년층':
            aspirations.extend([
                "안정적인 직장과 경제적 독립 달성",
                "의미있는 인간관계 형성 및 유지",
                "개인적 성장과 자아실현 기회 확대"
            ])
        elif age_group == '중년층':
            aspirations.extend([
                "건강한 노후 준비와 경제적 안정",
                "사회적 기여와 의미있는 활동 참여",
                "가족이나 친구들과의 관계 강화"
            ])
        else:  # 노년층
            aspirations.extend([
                "건강 유지와 독립적인 생활 지속",
                "세대 간 소통과 지혜 전수 기회",
                "안전하고 편안한 생활환경 조성"
            ])

        if social == '낮음':
            aspirations.append("사회적 연결망 확대와 소속감 증진")

        return aspirations[:3]

    def generate_welfare_journey(self, persona_profile: Dict[str, Any]) -> str:
        """복지 서비스 이용 여정 스토리"""
        welfare_needs = persona_profile.get('welfare_needs', {})
        recommended_services = persona_profile.get('recommended_services', [])

        # 가장 높은 복지 욕구 찾기
        if welfare_needs:
            top_need = max(welfare_needs.items(), key=lambda x: x[1])
            need_category = top_need[0].replace('proba_LBL_', '')
            need_score = top_need[1]

            if need_score > 0.7:
                urgency = "긴급히"
            elif need_score > 0.5:
                urgency = "필요시"
            else:
                urgency = "예방 차원에서"

            # 복지 정책 컨텍스트 가져오기
            policy_context = self.kb.get_welfare_policy_context(need_category)

            journey = f"{urgency} {need_category.lower()} 관련 지원이 필요한 상황입니다. "
            journey += policy_context + " "

            if recommended_services:
                service_list = ", ".join(recommended_services[:2])
                journey += f"특히 {service_list} 등의 서비스가 도움이 될 것으로 예상됩니다."

            return journey

        return "현재는 특별한 복지 서비스가 필요하지 않은 안정적인 상태입니다."

    def generate_realistic_scenarios(self, persona_profile: Dict[str, Any]) -> List[str]:
        """현실적인 상황 시나리오 생성"""
        scenarios = []
        mobility = persona_profile['mobility_level']
        digital = persona_profile['digital_engagement']
        age_group = persona_profile['age_group']
        welfare_needs = persona_profile.get('welfare_needs', {})

        # 일상생활 시나리오
        if mobility == '낮음' and digital == '낮음':
            scenarios.append("마트에 직접 가서 장을 보되, 무거운 물건은 배송 서비스를 이용합니다.")
        elif digital == '높음':
            scenarios.append("온라인 쇼핑몰에서 생필품을 주문하고 배달 앱으로 식사를 해결합니다.")

        # 연령대별 시나리오
        if age_group == '노년층':
            scenarios.append("정기적으로 동네 병원을 방문하여 건강검진을 받습니다.")
            scenarios.append("복지관의 프로그램에 참여하여 다른 어르신들과 교류합니다.")
        elif age_group == '청년층':
            scenarios.append("취업 준비나 이직을 위해 온라인 강의를 수강합니다.")
            scenarios.append("가끔 친구들과 만나 외식이나 문화활동을 즐깁니다.")

        # 복지 욕구 기반 시나리오
        high_needs = [k for k, v in welfare_needs.items() if v > 0.6]
        if any('ISOLATION' in need for need in high_needs):
            scenarios.append("외로움을 느낄 때는 전화 상담이나 온라인 커뮤니티를 이용합니다.")

        return scenarios[:3]

    def create_persona_story(self, persona_profile: Dict[str, Any]) -> PersonaStory:
        """완전한 페르소나 스토리 생성"""
        persona_id = persona_profile['id']

        # 이름 재생성 (더 현실적으로)
        character_name = self.select_name(
            persona_profile['gender'],
            persona_profile['age_group'],
            persona_id
        )

        story = PersonaStory(
            persona_id=persona_id,
            character_name=character_name,
            background_story=self.generate_background_story(persona_profile),
            daily_routine=self.generate_daily_routine(persona_profile),
            challenges=self.generate_challenges(persona_profile),
            aspirations=self.generate_aspirations(persona_profile),
            welfare_journey=self.generate_welfare_journey(persona_profile),
            realistic_scenarios=self.generate_realistic_scenarios(persona_profile)
        )

        return story

def main():
    """CLI 테스트 실행"""
    import argparse

    parser = argparse.ArgumentParser(description="페르소나 RAG 스토리텔러 테스트")
    parser.add_argument("--kb_path", required=True, help="kb_chunks.jsonl 경로")
    parser.add_argument("--persona_json", required=True, help="생성된 페르소나 JSON 경로")
    parser.add_argument("--output", default="persona_stories.json", help="스토리 출력 경로")

    args = parser.parse_args()

    # 지식 베이스 로드
    print("📚 RAG 지식 베이스 초기화...")
    kb = RAGKnowledgeBase(args.kb_path)

    # 스토리텔러 초기화
    storyteller = PersonaStoryTeller(kb)

    # 페르소나 프로필 로드
    with open(args.persona_json, 'r', encoding='utf-8') as f:
        personas_data = json.load(f)

    # 각 페르소나에 대한 스토리 생성
    stories = []
    for persona_profile in personas_data['personas']:
        print(f"📝 {persona_profile['name']} 스토리 생성 중...")
        story = storyteller.create_persona_story(persona_profile)
        stories.append(story)

    # 결과 저장
    stories_dict = {
        'metadata': {
            'generated_at': pd.Timestamp.now().isoformat(),
            'total_stories': len(stories),
            'storyteller_version': '1.0'
        },
        'stories': [story.__dict__ for story in stories]
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(stories_dict, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(stories)}개 페르소나 스토리 생성 완료: {args.output}")

    # 샘플 출력
    if stories:
        sample_story = stories[0]
        print(f"\n📖 샘플 스토리 - {sample_story.character_name}:")
        print(f"배경: {sample_story.background_story}")
        print(f"도전과제: {', '.join(sample_story.challenges)}")

if __name__ == "__main__":
    main()