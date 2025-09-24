# RAG 증강 산출물
생성 시각: 2025-09-24T09:42:12.600749

## 산출물
- feature_stats.csv : 컬럼별 기본 통계(결측률, 평균/표준편차/백분위)
- feature_mapping.csv : 원본→표준화(*_std), 표준화→파생(delta3m/trend12m) 매핑
- month_coverage.csv : 월별 행 수
- per_month_numeric_std.csv : 숫자형 컬럼의 월별 표준편차
- kb_chunks.jsonl : 벡터 인덱싱용 JSONL 청크(개요/매핑/월커버리지)
- README.md : 사용 가이드

## 인덱싱 가이드
- kb_chunks.jsonl 를 벡터 인덱스에 임베딩하세요.
- 표 파일(CSV)들은 RAG 응답 단계에서 수치 근거로 함께 로드하세요.

## 옵션: 규칙 파일(rules.yml)
- --rules_path 를 넘기면 규칙 신호명 ↔ 실제 컬럼 매핑 미리보기 청크가 추가됩니다.