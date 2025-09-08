# 서울 동행 나침반: RAG AI 기반 1인 가구 맞춤형 복지 솔루션 플랫폼

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-teal)](https://fastapi.tiangolo.com/)
[![RAG AI](https://img.shields.io/badge/Core%20Tech-RAG%20AI-blueviolet)](https://research.ibm.com/blog/retrieval-augmented-generation-RAG)
![Last Update](https://img.shields.io/github/last-commit/[Your-GitHub-ID]/persona-signal-welfare) 
> **[2025 서울 AI 해커톤](https://mediahub.seoul.go.kr/gongmo/2000665)** 출품작으로, 데이터로 복지 사각지대를 밝히고, AI로 사람을 먼저 찾아가는 기술을 제안합니다.

---

## 📌 프로젝트 개요 (Overview)

서울시 1인 가구의 급증과 함께, 기존 복지 시스템으로는 파악하기 어려운 '복지 사각지대' 문제가 심화되고 있습니다. 본 프로젝트는 이러한 문제를 해결하기 위해 **RAG(Retrieval-Augmented Generation)** 기술을 핵심으로 하는 AI 페르소나 생성 엔진을 제안합니다.

데이터가 부족하여 분석이 어려웠던 영역에서도, RAG가 외부 지식(정책 보고서, 연구 논문 등)을 참조하여 통계적으로 유의미하고 현실적인 **'가상 시민(AI 페르소나)'** 데이터를 생성합니다. 이 기술을 통해 잠재적 위기 그룹을 선제적으로 발굴하고, 개인의 상황에 가장 적합한 복지 솔루션을 자동으로 매칭하여 '신청 기반'이 아닌 '발굴 기반'의 능동적 복지 시스템을 구현하는 것을 목표로 합니다.

---

## ✨ 주요 기능 (Key Features)

| 기능 | 설명 |
|---|---|
| 🤖 **RAG 기반 AI 페르소나 생성** | 소량의 원본 데이터와 외부 지식(보고서, 뉴스)을 결합하여, 사회적 맥락을 반영한 대량의 '지능형 가상 페르소나 데이터'를 생성하고, 그룹별로 구체적인 서사를 부여합니다. |
| 📈 **위기 신호 예측** | 생성된 페르소나 데이터를 시계열로 분석하여, 기존에 발견하기 어려웠던 행동 패턴 변화나 이상 징후를 감지하고 잠재적 위기를 정량적인 '위험도 점수'로 산출합니다. |
| 💌 **맞춤형 복지 솔루션 추천** | 정의된 페르소나와 예측된 위기 신호를 바탕으로, 서울시 복지 서비스 DB와 매칭하여 개인별/그룹별 최적의 솔루션을 추천하고, 정책 실무자에게 'Action Plan'을 제공합니다. |
| 🖥️ **인터랙티브 웹 인터페이스** | 사용자가 AI 분석 과정을 시작하고, 생성된 페르소나, 위기 신호, 추천 솔루션을 한눈에 파악할 수 있는 웹 기반 인터페이스를 제공합니다. |

---

## 🧱 기술 스택 (Tech Stack)

| 구성 요소 | 사용 기술 |
|---|---|
| **Backend** | Python, FastAPI |
| **Frontend** | React.js, Vue.js (예정) |
| **AI / ML** | PyTorch / TensorFlow (Generative Models), Scikit-learn |
| **RAG Engine** | LLM (GPT-4 or other), Vector DB (Chroma, FAISS) |
| **Database** | PostgreSQL, SQLite |
| **DevOps** | Docker, GitHub Actions (예정) |
| **Version Control** | Git, GitHub |

---

## 📁 디렉토리 구조 (Directory Structure)

프로젝트는 모놀리식 아키텍처를 기반으로 하며, 각 기능 모듈이 명확하게 분리되어 협업의 효율성을 높입니다.

```bash
persona-signal-welfare/
├── .github/              # GitHub 관련 설정 (PR 템플릿, CODEOWNERS 등)
│   └── workflows/ci.yml  # CI/CD 설정
├── .gitignore            # Git 추적 제외 파일 설정
├── .env.example          # 환경 변수 샘플
├── README.md             # 프로젝트 설명 (현재 파일)
├── docs/                 # 프로젝트 관련 문서 (회의록, 설계도, 다이어그램 등)
├── requirements.txt      # Python 패키지 의존성 목록
├── Dockerfile            # 전체 백엔드(FastAPI + AI 모듈) 컨테이너 빌드용
├── docker-compose.yml    # 전체 서비스 실행
├── src/                  # 소스 코드 루트
│   ├── backend/          # 백엔드 API (FastAPI)
│   ├── frontend/         # 프론트엔드 (React/Vue)
│   ├── ai_modules/       # 핵심 AI 기능 모듈
│   │   ├── persona_generation/
│   │   ├── crisis_prediction/
│   │   └── recommendation/
│   ├── core/             # 공통 유틸리티
│   ├── config/           # 환경 설정
│   └── data/             # 데이터셋 및 DB 파일
│       ├── raw/
│       ├── processed/
│       └── synthetic/
└── tests/                # 테스트 코드
