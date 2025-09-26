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
| 🤖 **지능형 페르소나 엔진 (`PersonaGen`)** | (핵심 기술) 원본 데이터와 외부 지식(RAG)을 융합하여, 통계적 현실성과 깊이 있는 사회적 맥락을 갖춘 'AI 페르소나'를 창조합니다. 이는 서비스의 모든 지능적인 판단과 공감 능력의 기반이 됩니다. |
| 👤 **AI 프로파일링 및 진단** | 사용자가 입력한 정보를 바탕으로, `PersonaGen`이 축적한 페르소나 DB와 비교하여 사용자의 잠재적 유형을 **'진단'**합니다. 이를 통해 사용자 자신도 몰랐던 어려움을 객관적으로 파악하도록 돕습니다. |
| 💬 **공감형 AI 컨설팅** | AI가 진단한 페르소나 유형에 기반하여, 챗봇이 사용자와의 **공감대 높은 대화**를 통해 최종 솔루션을 함께 찾아갑니다. 단순 정보 검색을 넘어, 사용자의 진짜 필요에 집중합니다. |
| ✍️ **신청 과정 간소화 및 서류 지원** | 복지 서비스를 잘 모르고 신청에 어려움을 겪는 분들을 위해, 챗봇이 복잡한 **신청서류 작성을 자동화**하고, 필요 서류 발급 방법을 상세히 안내하여 정보 취약 계층의 신청 장벽을 획기적으로 낮춥니다. |
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
    │   ├── api/          # API 엔드포인트 라우터 (예: /profile, /recommend, /chat)
    │   └── main.py       # FastAPI 앱 실행 파일
    │
    ├── frontend/         # 사용자 인터페이스 (React/Vue)
    │
    ├── common/           # 여러 모듈에서 공통으로 사용하는 유틸리티 (예: DTO, 로거)
    │
    ├── data/             # 데이터셋 저장소
    │   ├── raw/          # 원본 1인 가구 데이터 
    │   └── processed/   
    │
    └── modules/          # 핵심 기능 모듈 
        │
        ├── data_analysis/      # 데이터 분석 
        │   ├── notebooks/        # 데이터 탐색 및 분석용 Jupyter Notebooks
        │   ├── main.py           # 전체 분석 파이프라인 실행 스크립트
        │   ├── eda.py            # 탐색적 데이터 분석 로직
        │   ├── preprocessing.py  # 데이터 전처리 로직
        │   ├── clustering.py     # 클러스터링(유형 분류) 로직
        │   └── output/           # 분석 결과물 (그래프, 분석 보고서.md 등)
        │
        ├── persona_engine/     # AI 엔진 개발 
        │   ├── knowledge_base/   # RAG가 참조할 지식 문서(.txt) 저장소
        │   ├── assets/           # 엔진이 생성/사용하는 자산 (Vector DB, Persona DB 등)
        │   ├── build_rag_db.py   # knowledge_base/의 문서를 Vector DB로 구축하는 스크립트
        │   ├── generation.py     # RAG, LLM을 활용한 페르소나/가상 데이터 생성 로직
        │   └── reflection.py     # 자기반성 및 프롬프트 개선 로직
        │
        └── welfare_recommender/ # 서비스 매칭 
            ├── assets/           # 구축된 복지 서비스 DB (SQLite 등)
            ├── crawlers/         # 복지 정보 크롤링 스크립트
            ├── db_builder.py     # 크롤링한 정보로 복지 서비스 DB를 구축하는 스크립트
            └── matching.py       # 사용자 프로필과 페르소나를 매칭하는 로직
