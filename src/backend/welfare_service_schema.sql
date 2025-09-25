-- 복지 서비스 통합 테이블 스키마
CREATE TABLE welfare_services (
    id SERIAL PRIMARY KEY,
    service_id VARCHAR(50) UNIQUE NOT NULL,           -- 서비스ID
    service_name VARCHAR(500) NOT NULL,               -- 서비스명
    service_type VARCHAR(20) NOT NULL,                -- government/local/private
    service_summary TEXT,                             -- 서비스 개요/요약
    detailed_link VARCHAR(1000),                      -- 상세 링크

    -- 관리기관 정보
    managing_agency VARCHAR(200),                     -- 소관부처/기관
    department VARCHAR(200),                          -- 담당부서
    region_sido VARCHAR(50),                          -- 시도명 (지자체만)
    region_sigungu VARCHAR(50),                       -- 시군구명 (지자체만)
    contact_phone VARCHAR(50),                        -- 연락처
    contact_email VARCHAR(100),                       -- 이메일
    address TEXT,                                     -- 주소

    -- 지원 내용
    support_target TEXT,                              -- 지원대상
    selection_criteria TEXT,                          -- 선정기준
    support_content TEXT,                             -- 지원내용
    support_cycle VARCHAR(50),                        -- 지원주기
    payment_method VARCHAR(50),                       -- 지급방식
    application_method TEXT,                          -- 신청방법
    required_documents TEXT,                          -- 제출서류

    -- 분류 정보
    category VARCHAR(100),                            -- 카테고리
    life_cycle VARCHAR(100),                          -- 생애주기
    target_characteristics VARCHAR(200),              -- 대상특성
    interest_topics VARCHAR(200),                     -- 관심주제/태그

    -- 메타 정보
    application_available BOOLEAN DEFAULT true,       -- 신청가능여부
    service_status VARCHAR(20) DEFAULT 'active',     -- 서비스상태
    start_date DATE,                                  -- 시작일
    end_date DATE,                                    -- 종료일
    view_count INTEGER DEFAULT 0,                    -- 조회수
    last_updated DATE DEFAULT CURRENT_DATE,          -- 최종수정일
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,   -- 생성일시
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP    -- 수정일시
);

-- 인덱스 생성
CREATE INDEX idx_welfare_service_type ON welfare_services(service_type);
CREATE INDEX idx_welfare_category ON welfare_services(category);
CREATE INDEX idx_welfare_region ON welfare_services(region_sido, region_sigungu);
CREATE INDEX idx_welfare_target_characteristics ON welfare_services(target_characteristics);
CREATE INDEX idx_welfare_service_status ON welfare_services(service_status);

-- 카테고리별 통계를 위한 뷰
CREATE VIEW welfare_service_stats AS
SELECT
    service_type,
    category,
    COUNT(*) as service_count,
    AVG(view_count) as avg_view_count
FROM welfare_services
WHERE service_status = 'active'
GROUP BY service_type, category;

-- 지역별 서비스 통계 뷰
CREATE VIEW regional_welfare_stats AS
SELECT
    region_sido,
    region_sigungu,
    COUNT(*) as service_count,
    COUNT(DISTINCT category) as category_count
FROM welfare_services
WHERE service_type = 'local' AND service_status = 'active'
GROUP BY region_sido, region_sigungu;