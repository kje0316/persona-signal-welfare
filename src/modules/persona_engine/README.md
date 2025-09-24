# PersonaGen 엔진 - 도메인 적응형 데이터 증강 플랫폼

## 🎯 개요

PersonaGen 엔진은 서울시 1인가구 통신 데이터 분석을 바탕으로 현실적인 AI 페르소나를 생성하는 시스템입니다. RAG(Retrieval-Augmented Generation) 기술을 활용하여 통계적 클러스터링과 지식 기반 스토리텔링을 결합합니다.

## 🏗️ 시스템 아키텍처

```
📊 Raw Data (396K+ records)
    ↓
🔄 Data Analysis Pipeline
    ├── clustering.py (K-means 페르소나 그룹화)
    ├── eda.py (시계열 패턴 분석)
    └── build_rag_aug.py (RAG 지식 베이스 구축)
    ↓
🎭 Persona Generation
    ├── persona_generator.py (핵심 생성 로직)
    ├── rag_storyteller.py (스토리 강화)
    └── api_service.py (API 서비스)
    ↓
🌐 Frontend Integration
    └── generation.py (통합 인터페이스)
```

## 🚀 주요 기능

### 1. 데이터 기반 페르소나 생성
- 396,864개 행의 서울시 1인가구 통신 생활패턴 데이터 활용
- K-means 클러스터링으로 5개 대표 페르소나 그룹 도출
- 하드 라벨 + 소프트 멤버십 확률로 세밀한 분류

### 2. RAG 지식 증강
- kb_chunks.jsonl: 통계적 메타데이터를 텍스트 지식으로 변환
- 정책 문서와 연구 논문 기반 복지 서비스 매핑
- 현실적인 페르소나 스토리텔링

### 3. 복지 욕구 예측
- 7가지 복지 카테고리별 위험도 점수
- 개인화된 복지 서비스 추천
- 시계열 변화 패턴 반영

## 📦 설치 및 설정

### 1. 의존성 설치

```bash
pip install numpy pandas scikit-learn
pip install pathlib dataclasses typing
```

### 2. 데이터 준비

필요한 데이터 파일들:
```
src/modules/data_analysis/
├── rag_aug_out/
│   ├── kb_chunks.jsonl          # RAG 지식 베이스
│   ├── feature_stats.csv        # 피처 통계
│   └── feature_mapping.csv      # 피처 매핑
├── risk_scoring/
│   ├── rules.yml               # 복지 위험도 규칙
│   └── *.py                    # 위험도 모델
└── telecom_data.csv            # 원본 통신 데이터 (선택)
```

## 🎮 사용법

### 1. 기본 사용 (CLI)

```bash
# 5개 페르소나 생성
python generation.py --personas 5

# 스토리 강화 포함
python generation.py --personas 5 --stories

# 프론트엔드용 내보내기
python generation.py --personas 5 --stories --export

# 시스템 메트릭 확인
python generation.py --personas 5 --metrics
```

### 2. Python API 사용

```python
from persona_engine.generation import PersonaGen

# PersonaGen 엔진 초기화
generator = PersonaGen()

# 페르소나 생성
personas = generator.generate_personas(n_personas=5)

# 스토리 강화
enhanced_personas = generator.enhance_with_stories()

# 복지 서비스 추천
recommendations = generator.get_welfare_recommendations(persona_id=0)

# 프론트엔드용 내보내기
export_path = generator.export_for_frontend()
```

### 3. 백엔드 API 통합

```python
from persona_engine.api_service import PersonaAPIService, create_fastapi_routes
from fastapi import FastAPI

# FastAPI 앱 생성
app = FastAPI()

# 서비스 초기화
service = PersonaAPIService()

# 라우트 추가
create_fastapi_routes(app, service)

# 서버 실행: uvicorn main:app --reload
```

사용 가능한 API 엔드포인트:
- `GET /api/v1/personas` - 페르소나 목록 조회/생성
- `GET /api/v1/personas/{id}` - 특정 페르소나 조회
- `GET /api/v1/stories` - 페르소나 스토리 생성
- `GET /api/v1/personas/{id}/recommendations` - 복지 서비스 추천
- `GET /api/v1/system/status` - 시스템 상태 확인

## 📊 생성되는 페르소나 예시

```json
{
  "id": 0,
  "name": "김민준",
  "age_group": "청년층",
  "gender": "남성",
  "district": "관악구",
  "characteristics": {
    "mobility_level": "높음",
    "digital_engagement": "높음",
    "social_connectivity": "보통",
    "economic_stability": "보통"
  },
  "welfare_needs": {
    "proba_LBL_EMPLOYMENT": 0.73,
    "proba_LBL_HOUSING": 0.65
  },
  "lifestyle_description": "관악구 거주 청년층 김민준는 활발한 이동성을 보이는 적극적인 생활 패턴, 디지털 콘텐츠를 자주 이용하는 현대적 라이프스타일을 보입니다.",
  "recommended_services": [
    "취업지원프로그램",
    "주거급여",
    "청년 창업지원"
  ],
  "character_story": {
    "background_story": "김민준님은 20대 후반의 1인가구로 대학가 근처로 젊은 층이 많은 주거지역에 거주하고 있습니다...",
    "daily_routine": "오전 7-8시경 기상하여 출근 준비를 합니다. 평일에는 대중교통을 이용해 다양한 곳을 이동하며...",
    "challenges": [
      "안정적인 일자리 확보의 어려움",
      "주거 안정성에 대한 불안감"
    ]
  }
}
```

## 🎯 성능 지표

- **데이터 커버리지**: 396,864개 행, 3년간 (2022-2025)
- **피처 수**: 원본 163개 + 표준화 158개 + 파생 316개
- **정확도 향상**: 베이스라인 대비 평균 3.85% 개선
- **생성 품질**: 평균 신뢰도 85% 이상
- **응답 시간**: 5개 페르소나 생성 < 30초

## 🔧 고급 설정

### 1. 커스텀 설정 파일 (config.json)

```json
{
  "data_analysis_path": "/path/to/data_analysis",
  "knowledge_base_path": "/path/to/kb_chunks.jsonl",
  "output_path": "/path/to/output",
  "cache_duration_hours": 24,
  "default_persona_count": 5,
  "domain": "seoul_single_households"
}
```

### 2. 환경별 설정

```python
# 개발 환경
generator = PersonaGen("config/dev.json")

# 운영 환경
generator = PersonaGen("config/prod.json")

# 테스트 환경
generator = PersonaGen("config/test.json")
```

## 🚨 문제 해결

### 일반적인 오류들

1. **데이터 파일을 찾을 수 없음**
   ```
   FileNotFoundError: 데이터 파일을 찾을 수 없습니다
   ```
   → `data_analysis_path` 경로 확인 및 필수 파일 존재 확인

2. **메모리 부족 오류**
   ```
   MemoryError: Unable to allocate array
   ```
   → `n_personas` 수를 줄이거나 서버 메모리 확대

3. **클러스터링 실패**
   ```
   ValueError: K sweep 결과가 비었습니다
   ```
   → 데이터 품질 확인 및 feature 컬럼 존재 확인

### 로그 레벨 설정

```python
import logging
logging.getLogger('persona_engine').setLevel(logging.DEBUG)
```

## 📈 확장 가능성

PersonaGen 엔진은 도메인 적응형 플랫폼으로 설계되어 다른 분야에도 적용 가능:

- **임산부 페르소나**: 출산/육아 관련 서비스 추천
- **고령자 페르소나**: 노인 복지 및 케어 서비스
- **청소년 페르소나**: 교육 및 진로 상담
- **장애인 페르소나**: 맞춤형 지원 서비스

데이터만 교체하면 해당 도메인의 전문 AI 페르소나 시스템으로 전환 가능합니다.

## 🤝 기여하기

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 라이선스

This project is licensed under the MIT License.

## 📞 지원

- 이슈 리포트: GitHub Issues
- 기술 문의: [개발자 이메일]
- 문서: [프로젝트 위키]

---

**PersonaGen 엔진** - 2025 서울 AI 해커톤 출품작
데이터로 현실을 반영하는 AI 페르소나 생성의 새로운 패러다임