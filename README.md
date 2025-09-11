# 서울 동행 나침반: 지능형 복지 추천 솔루션

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-teal)](https://fastapi.tiangolo.com/)
[![RAG AI](https://img.shields.io/badge/Core%20Tech-PersonaGen%20AI-blueviolet)](https://research.ibm.com/blog/retrieval-augmented-generation-RAG)
![Last Update](https://img.shields.io/github/last-commit/BOAZ-ADV-23-Team-Great-Heroe/persona-signal-welfare)

> **[2025 서울 AI 해커톤](https://mediahub.seoul.go.kr/gongmo/2000665)** 출품작으로, 데이터로 사람을 깊이 있게 이해하고, AI로 개인에게 가장 필요한 솔루션을 찾아가는 기술을 제안합니다.

---

## 📌 프로젝트 개요 (Overview)

서울시 1인 가구의 급증과 함께, 기존 복지 시스템으로는 파악하기 어려운 '복지 사각지대' 문제가 심화되고 있습니다. 본 프로젝트는 이러한 문제를 해결하기 위해 **'서비스형 AI 페르소나(Persona-as-a-Service)'** 플랫폼, `PersonaGen`을 제안합니다.

`PersonaGen`은 데이터가 부족한 영역에서도, **RAG(Retrieval-Augmented Generation)** 기술이 외부 지식(정책 보고서, 연구 논문 등)을 참조하여 통계적으로 유의미하고 현실적인 **'가상 시민(AI 페르소나)'** 데이터를 창조합니다.

우리의 최종 목표는 이 핵심 기술을 바탕으로, 사용자가 자신의 정보를 입력하면 **AI가 잠재적 어려움을 가진 페르소나 유형을 진단**하고, **대화형 챗봇을 통해 개인의 상황에 가장 적합한 복지 솔루션을 자동으로 매칭**하여 '신청 기반'이 아닌 '발굴 및 맞춤 기반'의 능동적 복지 시스템을 구현하는 것입니다.

---

## ✨ 주요 기능 (Key Features)

| 기능 | 설명 |
|---|---|
| 🤖 **AI 페르소나 자산 구축** | (백엔드 엔진) 원본 데이터와 외부 지식을 결합하여, 사회적 맥락을 반영한 다양한 페르소나를 자동으로 생성하고, 서비스의 핵심 자산으로 축적합니다. |
| 👤 **AI 프로파일링 및 페르소나 매칭** | 사용자가 자신의 정보를 입력하면, `PersonaGen`이 축적한 페르소나 DB와 비교하여 사용자와 가장 유사한 잠재적 페르소나 유형을 실시간으로 분석하고 진단합니다. |
| 💬 **대화형 솔루션 추천** | AI 프로파일링 결과를 바탕으로, 챗봇이 사용자와의 대화를 통해 구체적인 니즈를 파악하고, 국내/외 복지 서비스 중 가장 적합한 최종 솔루션을 찾아 맞춤형으로 추천합니다. |
| 💡 **데이터 기반 정책 제안** | 해외 우수 복지 사례 API를 연동하여, 국내에 없는 더 나은 해결책이 존재할 경우 이를 비교하여 보여주고 새로운 정책 방향을 제안하는 기능을 포함합니다. |

---

## 🧱 기술 스택 (Tech Stack)

| 구성 요소 | 사용 기술 |
|---|---|
| **Backend** | Python, FastAPI |
| **Frontend** | React.js, Vue.js (예정) |
| **AI / ML** | PyTorch / TensorFlow (Generative Models), Scikit-learn |
| **Core Engine** | LLM (GPT-4 or other), LangChain, Vector DB (Chroma, FAISS) |
| **Database** | SQLite, PostgreSQL (예정) |
| **Version Control** | Git, GitHub |

---

## 📁 디렉토리 구조 (Directory Structure)

프로젝트는 서비스의 흐름에 맞춰 각 기능 모듈이 명확하게 분리되어 있습니다.

```bash
persona-signal-welfare/
├── .github/
├── docs/                 # 프로젝트 관련 문서 (회의록, 기획서, 설계도 등)
├── .gitignore
├── README.md             # 프로젝트 설명 (최신 버전)
├── requirements.txt      # 전체 프로젝트 Python 의존성
├── Dockerfile            # 최종 서비스 빌드를 위한 Dockerfile
├── docker-compose.yml    # 전체 서비스(백엔드, 프론트엔드) 실행
└── src/                  # 소스 코드 루트
    ├── backend/          # 최종 서비스를 제공하는 백엔드 API 서버 (FastAPI)
    │   ├── api/          # API 엔드포인트 라우터 (예: /recommend, /chat)
    │   └── main.py       # FastAPI 앱 실행 파일
    │
    ├── frontend/         # 사용자 인터페이스 (React/Vue)
    │
    ├── common/           # 여러 모듈에서 공통으로 사용하는 유틸리티 (예: 로거, DTO)
    │
    ├── data/             # 데이터셋
    │   ├── raw/          # 원본 1인 가구 데이터
    │   └── processed/    # 전처리된 데이터
    │
    └── modules/          # ⭐ 각 팀원이 담당하는 핵심 기능 모듈 (3개)
        │
        ├── 1_data_processing/  # 데이터 분석 
        │   ├── eda.ipynb       # 원본 데이터 탐색 및 분석 노트북
        │   ├── knowledge_base_builder.py # RAG 지식베이스 구축 스크립트
        │   └── output/         # 분석 결과물 (그래프, 정제된 텍스트 등)
        │
        ├── 2_persona_engine/   # 페르소나 생성
        │   ├── clustering.py   # 그룹화(유형 분류) 로직
        │   ├── rag.py          # RAG 검색 로직
        │   ├── generation.py   # 페르소나/가상 데이터 생성 로직
        │   ├── reflection.py   # 자기반성 및 프롬프트 개선 로직
        │   └── assets/         # 엔진이 사용하는 자산 (Vector DB, Persona DB 등)
        │
        └── 3_welfare_recommender/ # 서비스 매칭
            ├── crawlers/       # 복지 정보 크롤링 스크립트
            ├── db_builder.py   # 크롤링한 정보로 복지 서비스 DB 구축
            ├── matching.py     # 페르소나와 복지 서비스를 매칭하는 로직
            └── assets/         # 구축된 복지 서비스 DB (SQLite 등)

