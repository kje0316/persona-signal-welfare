#!/usr/bin/env python3
"""
복지 서비스 CSV 데이터의 자격 조건을 분석하여 필터링 기준을 추출하는 스크립트
"""

import pandas as pd
import re
from collections import Counter, defaultdict
import json
from pathlib import Path

# CSV 파일 경로
CSV_FILES = {
    'government': 'src/modules/welfare_recommender/crawlers/datapotal/goverment_final_welfare_list_categorized.csv',
    'local': 'src/modules/welfare_recommender/crawlers/datapotal/local_final_welfare_list_categorized.csv',
    'private': 'src/modules/welfare_recommender/crawlers/datapotal/private_final_welfare_list_with_category.csv'
}

def extract_age_conditions(text):
    """나이/연령 조건 추출"""
    if not isinstance(text, str):
        return []

    age_patterns = [
        r'(\d+)세\s*이상',
        r'(\d+)세\s*미만',
        r'(\d+)세\s*～\s*(\d+)세',
        r'(\d+)세\s*-\s*(\d+)세',
        r'만\s*(\d+)세',
        r'청년',
        r'노인',
        r'중장년',
        r'아동',
        r'청소년',
        r'영유아',
        r'신생아'
    ]

    age_conditions = []
    for pattern in age_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        age_conditions.extend(matches)

    return age_conditions

def extract_income_conditions(text):
    """소득 조건 추출"""
    if not isinstance(text, str):
        return []

    income_patterns = [
        r'기준\s*중위소득\s*(\d+)%',
        r'중위소득\s*(\d+)%',
        r'기초생활',
        r'차상위',
        r'저소득',
        r'수급자',
        r'건강보험료',
        r'(\d+)만원\s*이하',
        r'소득\s*(\d+)백만원',
        r'연소득\s*(\d+)천만원'
    ]

    income_conditions = []
    for pattern in income_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            income_conditions.extend(matches)

    # 특수 키워드
    special_keywords = ['기초생활', '차상위', '저소득', '수급자', '건강보험료']
    for keyword in special_keywords:
        if keyword in text:
            income_conditions.append(keyword)

    return income_conditions

def extract_family_conditions(text):
    """가족/가구 조건 추출"""
    if not isinstance(text, str):
        return []

    family_patterns = [
        r'(\d+)인\s*가구',
        r'(\d+)자녀',
        r'한부모',
        r'조손',
        r'다자녀',
        r'독거',
        r'1인\s*가구',
        r'미혼모',
        r'이혼',
        r'사별',
        r'다문화',
        r'새터민',
        r'탈북'
    ]

    family_conditions = []
    for pattern in family_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        family_conditions.extend(matches)

    return family_conditions

def extract_housing_conditions(text):
    """주거 조건 추출"""
    if not isinstance(text, str):
        return []

    housing_patterns = [
        r'무주택',
        r'전세',
        r'월세',
        r'임대',
        r'자가',
        r'보증금\s*(\d+)억',
        r'보증금\s*(\d+)만원',
        r'임차보증금'
    ]

    housing_conditions = []
    for pattern in housing_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            housing_conditions.extend(matches)

    return housing_conditions

def extract_employment_conditions(text):
    """고용/직업 조건 추출"""
    if not isinstance(text, str):
        return []

    employment_keywords = [
        '실업', '구직', '취업', '직업훈련', '창업', '자영업',
        '학생', '재학', '졸업', '중퇴',
        '은퇴', '퇴직', '경력단절',
        '구직자', '취업준비생'
    ]

    employment_conditions = []
    for keyword in employment_keywords:
        if keyword in text:
            employment_conditions.append(keyword)

    return employment_conditions

def extract_special_conditions(text):
    """특수 상황 조건 추출"""
    if not isinstance(text, str):
        return []

    special_keywords = [
        '임산부', '출산', '육아', '보육',
        '장애', '장애인',
        '질환', '암', '중증', '희귀병', '난치병',
        '치매', '정신건강',
        '의료급여', '의료비',
        '다문화', '탈북', '새터민',
        '국가유공자', '보훈'
    ]

    special_conditions = []
    for keyword in special_keywords:
        if keyword in text:
            special_conditions.append(keyword)

    return special_conditions

def analyze_welfare_data():
    """복지 데이터 분석"""
    all_conditions = {
        'age': Counter(),
        'income': Counter(),
        'family': Counter(),
        'housing': Counter(),
        'employment': Counter(),
        'special': Counter(),
        'categories': Counter(),
        'target_characteristics': Counter()
    }

    total_services = 0

    for service_type, csv_path in CSV_FILES.items():
        if not Path(csv_path).exists():
            print(f"파일을 찾을 수 없습니다: {csv_path}")
            continue

        print(f"\n=== {service_type.upper()} 데이터 분석 중 ===")

        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            print(f"총 {len(df)} 개 서비스")
            total_services += len(df)

            # 분석할 컬럼 확인
            print("컬럼:", df.columns.tolist())

            # 지원대상 및 선정기준 분석
            target_cols = ['지원대상상세', '지원대상', '선정기준']
            target_text = ""

            for col in target_cols:
                if col in df.columns:
                    target_text += " " + df[col].fillna("").astype(str).str.cat(sep=" ")

            # 카테고리 정보
            if '카테고리' in df.columns:
                categories = df['카테고리'].fillna("").value_counts()
                all_conditions['categories'].update(categories.to_dict())

            # 대상특성 정보
            if '대상특성' in df.columns:
                target_chars = df['대상특성'].fillna("").value_counts()
                all_conditions['target_characteristics'].update(target_chars.to_dict())

            # 조건 추출
            print("조건 추출 중...")
            age_cond = extract_age_conditions(target_text)
            income_cond = extract_income_conditions(target_text)
            family_cond = extract_family_conditions(target_text)
            housing_cond = extract_housing_conditions(target_text)
            employment_cond = extract_employment_conditions(target_text)
            special_cond = extract_special_conditions(target_text)

            # 카운터 업데이트
            all_conditions['age'].update(age_cond)
            all_conditions['income'].update(income_cond)
            all_conditions['family'].update(family_cond)
            all_conditions['housing'].update(housing_cond)
            all_conditions['employment'].update(employment_cond)
            all_conditions['special'].update(special_cond)

        except Exception as e:
            print(f"오류 발생: {e}")

    return all_conditions, total_services

def generate_filter_criteria(conditions):
    """필터링 기준 생성"""
    print("\n" + "="*50)
    print("📊 복지 서비스 자격조건 분석 결과")
    print("="*50)

    filter_criteria = {}

    # 1. 연령 조건
    print("\n🎂 연령 조건:")
    age_filters = []
    age_keywords = ['청년', '노인', '중장년', '아동', '청소년', '영유아', '신생아']

    for keyword in age_keywords:
        count = conditions['age'][keyword]
        if count > 0:
            age_filters.append({'label': keyword, 'count': count})
            print(f"  - {keyword}: {count}개 서비스")

    # 나이 범위 분석
    print("  연령대 분석 (상위 10개):")
    for age, count in conditions['age'].most_common(10):
        if age not in age_keywords:
            print(f"    - {age}: {count}회")

    filter_criteria['age'] = {
        'type': 'select',
        'options': [
            {'value': 'youth', 'label': '청년 (19-39세)', 'keywords': ['청년']},
            {'value': 'middle', 'label': '중장년 (40-64세)', 'keywords': ['중장년']},
            {'value': 'senior', 'label': '노인 (65세 이상)', 'keywords': ['노인']},
            {'value': 'child', 'label': '아동·청소년 (18세 이하)', 'keywords': ['아동', '청소년', '영유아']},
            {'value': 'all', 'label': '연령 무관', 'keywords': []}
        ]
    }

    # 2. 소득 조건
    print("\n💰 소득 조건:")
    income_items = conditions['income'].most_common(15)
    for income, count in income_items:
        print(f"  - {income}: {count}회")

    filter_criteria['income'] = {
        'type': 'select',
        'options': [
            {'value': 'basic', 'label': '기초생활수급자', 'keywords': ['기초생활', '수급자']},
            {'value': 'near_poor', 'label': '차상위계층', 'keywords': ['차상위']},
            {'value': 'low_50', 'label': '기준중위소득 50% 이하', 'keywords': ['중위소득 50%', '중위소득50%']},
            {'value': 'low_100', 'label': '기준중위소득 100% 이하', 'keywords': ['중위소득 100%', '중위소득100%']},
            {'value': 'low_150', 'label': '기준중위소득 150% 이하', 'keywords': ['중위소득 150%', '중위소득150%']},
            {'value': 'middle_income', 'label': '중간소득층', 'keywords': []},
            {'value': 'all', 'label': '소득 무관', 'keywords': []}
        ]
    }

    # 3. 가구 상황
    print("\n👨‍👩‍👧‍👦 가구 상황:")
    family_items = conditions['family'].most_common(10)
    for family, count in family_items:
        print(f"  - {family}: {count}회")

    filter_criteria['family'] = {
        'type': 'checkbox',
        'options': [
            {'value': 'single', 'label': '1인 가구', 'keywords': ['1인가구', '독거']},
            {'value': 'couple', 'label': '2인 가구 (부부)', 'keywords': ['2인가구']},
            {'value': 'multi_child', 'label': '다자녀 가정', 'keywords': ['다자녀', '3자녀', '4자녀']},
            {'value': 'single_parent', 'label': '한부모 가정', 'keywords': ['한부모', '미혼모']},
            {'value': 'grandparent', 'label': '조손 가정', 'keywords': ['조손']},
            {'value': 'multicultural', 'label': '다문화 가정', 'keywords': ['다문화']},
            {'value': 'defector', 'label': '탈북민 가정', 'keywords': ['새터민', '탈북']}
        ]
    }

    # 4. 주거 상황
    print("\n🏠 주거 상황:")
    housing_items = conditions['housing'].most_common(8)
    for housing, count in housing_items:
        print(f"  - {housing}: {count}회")

    filter_criteria['housing'] = {
        'type': 'select',
        'options': [
            {'value': 'homeless', 'label': '무주택자', 'keywords': ['무주택']},
            {'value': 'jeonse', 'label': '전세 거주', 'keywords': ['전세']},
            {'value': 'monthly_rent', 'label': '월세 거주', 'keywords': ['월세']},
            {'value': 'rental', 'label': '임대주택 거주', 'keywords': ['임대']},
            {'value': 'owned', 'label': '자가 소유', 'keywords': ['자가']},
            {'value': 'all', 'label': '주거형태 무관', 'keywords': []}
        ]
    }

    # 5. 고용 상황
    print("\n💼 고용 상황:")
    employment_items = conditions['employment'].most_common(10)
    for employment, count in employment_items:
        print(f"  - {employment}: {count}회")

    filter_criteria['employment'] = {
        'type': 'checkbox',
        'options': [
            {'value': 'unemployed', 'label': '실업자', 'keywords': ['실업', '구직자']},
            {'value': 'job_seeking', 'label': '구직중', 'keywords': ['구직', '취업준비생']},
            {'value': 'student', 'label': '학생/재학중', 'keywords': ['학생', '재학']},
            {'value': 'employed', 'label': '직장인', 'keywords': ['취업', '직장']},
            {'value': 'self_employed', 'label': '자영업자', 'keywords': ['자영업', '창업']},
            {'value': 'retired', 'label': '은퇴/퇴직', 'keywords': ['은퇴', '퇴직']},
            {'value': 'career_break', 'label': '경력단절', 'keywords': ['경력단절']}
        ]
    }

    # 6. 특수 상황
    print("\n🏥 특수 상황:")
    special_items = conditions['special'].most_common(15)
    for special, count in special_items:
        print(f"  - {special}: {count}회")

    filter_criteria['special_condition'] = {
        'type': 'checkbox',
        'options': [
            {'value': 'pregnancy', 'label': '임신/출산/육아', 'keywords': ['임산부', '출산', '육아', '보육']},
            {'value': 'disability', 'label': '장애인', 'keywords': ['장애', '장애인']},
            {'value': 'disease', 'label': '질환자', 'keywords': ['질환', '암', '중증', '희귀병', '난치병', '치매']},
            {'value': 'medical', 'label': '의료지원 필요', 'keywords': ['의료급여', '의료비']},
            {'value': 'veteran', 'label': '국가유공자', 'keywords': ['국가유공자', '보훈']},
            {'value': 'none', 'label': '해당사항 없음', 'keywords': []}
        ]
    }

    # 7. 카테고리별 분석
    print("\n📋 서비스 카테고리:")
    category_items = conditions['categories'].most_common(15)
    for category, count in category_items:
        print(f"  - {category}: {count}개 서비스")

    print("\n🎯 대상 특성:")
    target_items = conditions['target_characteristics'].most_common(15)
    for target, count in target_items:
        print(f"  - {target}: {count}개 서비스")

    return filter_criteria

def main():
    """메인 함수"""
    print("=== 복지 서비스 자격조건 분석 시작 ===")

    # 데이터 분석
    conditions, total_services = analyze_welfare_data()

    print(f"\n총 분석된 서비스 수: {total_services}")

    # 필터링 기준 생성
    filter_criteria = generate_filter_criteria(conditions)

    # JSON 파일로 저장
    output_file = "welfare_filter_criteria.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filter_criteria, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 필터링 기준이 '{output_file}'에 저장되었습니다.")

    return filter_criteria

if __name__ == "__main__":
    main()