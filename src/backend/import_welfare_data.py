#!/usr/bin/env python3
"""
복지 서비스 CSV 데이터를 PostgreSQL DB에 임포트하는 스크립트
"""

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
import sys
from pathlib import Path

# 데이터베이스 연결 정보
DB_CONFIG = {
    'host': 'seoul-ht-11.cpk0oamsu0g6.us-west-1.rds.amazonaws.com',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'yeardream11!!'
}

# CSV 파일 경로
CSV_FILES = {
    'government': 'src/modules/welfare_recommender/crawlers/datapotal/goverment_final_welfare_list_categorized.csv',
    'local': 'src/modules/welfare_recommender/crawlers/datapotal/local_final_welfare_list_categorized.csv',
    'private': 'src/modules/welfare_recommender/crawlers/datapotal/private_final_welfare_list_with_category.csv'
}

def clean_text(text):
    """텍스트 정리 함수"""
    if pd.isna(text) or text == '':
        return None
    return str(text).strip().replace('\n', ' ').replace('\r', ' ')

def parse_government_data(df):
    """중앙부처 데이터 파싱"""
    records = []

    for _, row in df.iterrows():
        try:
            record = {
                'service_id': clean_text(row.get('서비스ID', '')),
                'service_name': clean_text(row.get('서비스명', '')),
                'service_type': 'government',
                'service_summary': clean_text(row.get('서비스개요', '')),
                'detailed_link': clean_text(row.get('상세링크', '')),
                'managing_agency': clean_text(row.get('소관부처', '')),
                'department': None,  # Government data doesn't have department
                'region_sido': None,
                'region_sigungu': None,
                'contact_phone': None,
                'contact_email': None,
                'address': None,
                'support_target': clean_text(row.get('지원대상상세', '')),
                'selection_criteria': clean_text(row.get('선정기준', '')),
                'support_content': clean_text(row.get('지원내용', '')),
                'support_cycle': clean_text(row.get('지원주기', '')),
                'payment_method': clean_text(row.get('지급방식', '')),
                'application_method': None,
                'required_documents': None,
                'category': clean_text(row.get('카테고리', '')),
                'life_cycle': None,
                'target_characteristics': clean_text(row.get('대상특성', '')),
                'interest_topics': None,
                'service_status': 'active',
                'start_date': None,
                'end_date': None,
                'view_count': 0,
                'last_updated': None
            }

            # 필수 필드 검증
            if record['service_id'] and record['service_name']:
                records.append(record)

        except Exception as e:
            print(f"정부 데이터 파싱 오류: {e}")
            continue

    return records

def parse_local_data(df):
    """지자체 데이터 파싱"""
    records = []

    for _, row in df.iterrows():
        try:
            record = {
                'service_id': clean_text(row.get('서비스ID', '')),
                'service_name': clean_text(row.get('서비스명', '')),
                'service_type': 'local',
                'service_summary': clean_text(row.get('서비스 개요', '')),
                'detailed_link': clean_text(row.get('상세 링크', '')),
                'managing_agency': None,  # Local data doesn't have managing_agency
                'department': clean_text(row.get('담당부서명', '')),
                'region_sido': clean_text(row.get('시도명', '')),
                'region_sigungu': clean_text(row.get('시군구명', '')),
                'contact_phone': None,
                'contact_email': None,
                'address': None,
                'support_target': clean_text(row.get('지원대상', '')),
                'selection_criteria': clean_text(row.get('선정기준', '')),
                'support_content': clean_text(row.get('서비스내용', '')),
                'support_cycle': clean_text(row.get('지원주기', '')),
                'payment_method': clean_text(row.get('지급방식', '')),
                'application_method': clean_text(row.get('신청방법상세', '')),
                'required_documents': None,
                'category': clean_text(row.get('카테고리', '')),
                'life_cycle': clean_text(row.get('생애주기', '')),
                'target_characteristics': clean_text(row.get('대상특성', '')),
                'interest_topics': clean_text(row.get('관심주제', '')),
                'service_status': 'active',
                'start_date': None,
                'end_date': None,
                'view_count': int(row.get('조회수', 0)) if pd.notna(row.get('조회수')) else 0,
                'last_updated': None
            }

            # 날짜 파싱
            try:
                last_updated = row.get('최종수정일')
                if pd.notna(last_updated):
                    record['last_updated'] = datetime.strptime(str(last_updated), '%Y%m%d').date()
            except:
                pass

            # 필수 필드 검증
            if record['service_id'] and record['service_name']:
                records.append(record)

        except Exception as e:
            print(f"지자체 데이터 파싱 오류: {e}")
            continue

    return records

def parse_private_data(df):
    """민간 데이터 파싱"""
    records = []

    for _, row in df.iterrows():
        try:
            record = {
                'service_id': clean_text(row.get('서비스ID', '')),
                'service_name': clean_text(row.get('서비스명', '')),
                'service_type': 'private',
                'service_summary': clean_text(row.get('서비스 요약', '')),
                'detailed_link': clean_text(row.get('상세 링크', '')),
                'managing_agency': clean_text(row.get('소관기관', '')),
                'department': None,  # Private data doesn't have department
                'region_sido': None,
                'region_sigungu': None,
                'contact_phone': clean_text(row.get('연락처', '')),
                'contact_email': clean_text(row.get('이메일', '')),
                'address': clean_text(row.get('주소', '')),
                'support_target': clean_text(row.get('지원대상', '')),
                'selection_criteria': None,
                'support_content': clean_text(row.get('지원내용', '')),
                'support_cycle': None,
                'payment_method': None,
                'application_method': clean_text(row.get('신청방법', '')),
                'required_documents': clean_text(row.get('제출서류', '')),
                'category': clean_text(row.get('카테고리', '')),
                'life_cycle': clean_text(row.get('BKJR_LFTM_CYC_CD', '')),
                'target_characteristics': clean_text(row.get('WLFARE_INFO_AGGRP_CD', '')),
                'interest_topics': clean_text(row.get('태그', '')),
                'service_status': 'active',
                'start_date': None,
                'end_date': None,
                'view_count': 0,
                'last_updated': None
            }

            # 날짜 파싱
            try:
                start_date = row.get('시작일')
                if pd.notna(start_date):
                    record['start_date'] = datetime.strptime(str(start_date), '%Y%m%d').date()

                end_date = row.get('종료일')
                if pd.notna(end_date):
                    record['end_date'] = datetime.strptime(str(end_date), '%Y%m%d').date()
            except:
                pass

            # 서비스 상태
            status = clean_text(row.get('진행상태', ''))
            if status == '진행중':
                record['service_status'] = 'active'
            elif status == '종료':
                record['service_status'] = 'inactive'

            # 필수 필드 검증
            if record['service_id'] and record['service_name']:
                records.append(record)

        except Exception as e:
            print(f"민간 데이터 파싱 오류: {e}")
            continue

    return records

def insert_records(records):
    """DB에 레코드 삽입"""
    if not records:
        return 0

    try:
        # DB 연결
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 기존 데이터 삭제 (선택사항)
        service_type = records[0]['service_type']
        cursor.execute("DELETE FROM welfare_services WHERE service_type = %s", (service_type,))
        print(f"{service_type} 기존 데이터 삭제 완료")

        # INSERT 쿼리 준비
        insert_query = """
            INSERT INTO welfare_services (
                service_id, service_name, service_type, service_summary, detailed_link,
                managing_agency, department, region_sido, region_sigungu,
                contact_phone, contact_email, address,
                support_target, selection_criteria, support_content,
                support_cycle, payment_method, application_method, required_documents,
                category, life_cycle, target_characteristics, interest_topics,
                service_status, start_date, end_date, view_count, last_updated
            ) VALUES (
                %(service_id)s, %(service_name)s, %(service_type)s, %(service_summary)s, %(detailed_link)s,
                %(managing_agency)s, %(department)s, %(region_sido)s, %(region_sigungu)s,
                %(contact_phone)s, %(contact_email)s, %(address)s,
                %(support_target)s, %(selection_criteria)s, %(support_content)s,
                %(support_cycle)s, %(payment_method)s, %(application_method)s, %(required_documents)s,
                %(category)s, %(life_cycle)s, %(target_characteristics)s, %(interest_topics)s,
                %(service_status)s, %(start_date)s, %(end_date)s, %(view_count)s, %(last_updated)s
            )
            ON CONFLICT (service_id) DO UPDATE SET
                service_name = EXCLUDED.service_name,
                service_summary = EXCLUDED.service_summary,
                updated_at = CURRENT_TIMESTAMP
        """

        # 레코드 삽입
        success_count = 0
        for record in records:
            try:
                cursor.execute(insert_query, record)
                success_count += 1
            except Exception as e:
                print(f"레코드 삽입 오류: {e}")
                print(f"문제 레코드: {record.get('service_id', 'Unknown')}")
                continue

        conn.commit()
        cursor.close()
        conn.close()

        print(f"{service_type}: {success_count}/{len(records)} 레코드 삽입 완료")
        return success_count

    except Exception as e:
        print(f"DB 연결 오류: {e}")
        return 0

def main():
    """메인 함수"""
    print("=== 복지 서비스 데이터 임포트 시작 ===")

    total_imported = 0

    # 프로젝트 루트 디렉토리로 이동
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    for service_type, csv_path in CSV_FILES.items():
        print(f"\n--- {service_type.upper()} 데이터 처리 ---")

        if not os.path.exists(csv_path):
            print(f"파일을 찾을 수 없습니다: {csv_path}")
            continue

        try:
            # CSV 파일 읽기
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            print(f"CSV 파일 읽기 완료: {len(df)} rows")

            # 데이터 파싱
            if service_type == 'government':
                records = parse_government_data(df)
            elif service_type == 'local':
                records = parse_local_data(df)
            elif service_type == 'private':
                records = parse_private_data(df)

            print(f"파싱된 레코드 수: {len(records)}")

            # DB에 삽입
            imported = insert_records(records)
            total_imported += imported

        except Exception as e:
            print(f"{service_type} 처리 중 오류: {e}")
            continue

    print(f"\n=== 임포트 완료: 총 {total_imported} 레코드 ===")

if __name__ == "__main__":
    main()