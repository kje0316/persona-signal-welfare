# import pandas as pd

# # --- 설정 (입력 파일과 출력 파일 이름) ---
# INPUT_CSV_PATH = "bokjiro_final_processed.csv"   # 기존 파일
# OUTPUT_CSV_PATH = "bokjiro_final_processed.csv"  # 같은 파일명으로 덮어쓰기

# if __name__ == "__main__":
#     try:
#         # 1. 원본 CSV 파일 읽기
#         df = pd.read_csv(INPUT_CSV_PATH)
#         print(f"'{INPUT_CSV_PATH}' 파일을 읽는 중...")
#         print(f"📊 원본 행 개수: {len(df)}, 셀 개수: {df.size}")

#         # 2. 복지사업ID 기준 중복 처리 (중앙부처만 유지)
#         before_dup = len(df)
#         df = df.sort_values(by=["출처"], ascending=False)  # 중앙부처가 먼저 오도록
#         df = df.drop_duplicates(subset=["복지사업ID"], keep="first")
#         after_dup = len(df)
#         print(f"📊 복지사업ID 중복 제거 후 행 개수: {after_dup} (제거된 행 {before_dup - after_dup})")

#         # 3. 종료일 필터링 (1970XXXX 유지, 202501XX ~ 202508XX 제거)
#         df["종료일"] = df["종료일"].astype(str).str.strip()

#         # 제거할 종료일 패턴 정의
#         remove_prefixes = tuple([f"20250{i:02d}" for i in range(1, 9)])

#         before_filter = len(df)
#         df = df[
#             (df["종료일"].str.startswith("1970")) | 
#             (~df["종료일"].str[:6].isin(remove_prefixes))
#         ]
#         after_filter = len(df)
#         print(f"📊 종료일 필터링 후 행 개수: {after_filter} (제거된 행 {before_filter - after_filter})")

#         # 4. 최종 결과 저장
#         df.to_csv(OUTPUT_CSV_PATH, index=False, encoding="utf-8-sig")

#         print("\n==============================================")
#         print(f"✅ 최종 완료! '{OUTPUT_CSV_PATH}' 파일이 저장되었습니다.")
#         print(f"📊 최종 행 개수: {len(df)}")
#         print(f"📊 최종 셀 개수: {df.size}")
#         print("==============================================")

#     except FileNotFoundError:
#         print(f"🚨 오류: '{INPUT_CSV_PATH}' 파일을 찾을 수 없습니다.")
#     except Exception as e:
#         print(f"🚨 처리 중 오류 발생: {e}")

import pandas as pd

# --- 설정 (입력 파일과 출력 파일 이름) ---
INPUT_CSV_PATH = "bokjiro_final_processed.csv"  # 입력 파일
OUTPUT_CSV_PATH = "bokjiro_final_processed.csv" # 저장 파일 (덮어쓰기)

if __name__ == "__main__":
    try:
        # 1. 원본 CSV 파일 읽기
        df = pd.read_csv(INPUT_CSV_PATH)
        print(f"'{INPUT_CSV_PATH}' 파일을 읽었습니다.")
        print(f"📊 원본 행 개수: {len(df)}")

        # 2. 종료일 필터링 (요청사항 정확히 반영)
        # '종료일' 컬럼을 문자열로 변환합니다.
        df["종료일"] = df["종료일"].astype(str).str.strip()

        # 제거할 종료일의 연도-월(YYYYMM) 패턴을 정의합니다. (2025년 1월 ~ 8월)
        remove_prefixes = [f"20250{i}" for i in range(1, 9)] # 결과: ['202501', '202502', ..., '202508']

        before_filter_count = len(df)

        # 필터링 조건:
        # 조건 1: 종료일이 '1970'으로 시작하는 데이터는 "유지"
        condition_1970 = df["종료일"].str.startswith("1970")
        
        # 조건 2: 종료일의 앞 6자리(YYYYMM)가 remove_prefixes 리스트에 포함되지 "않는" 데이터 "유지"
        condition_2025 = ~df["종료일"].str[:6].isin(remove_prefixes)
        
        # 두 조건 중 하나라도 만족하면 최종 유지
        df_filtered = df[condition_1970 | condition_2025]
        
        after_filter_count = len(df_filtered)
        
        print(f"📊 종료일 필터링 후 행 개수: {after_filter_count} (제거된 행: {before_filter_count - after_filter_count})")

        # 3. 최종 결과 저장
        df_filtered.to_csv(OUTPUT_CSV_PATH, index=False, encoding="utf-8-sig")

        print("\n==============================================")
        print(f"✅ 최종 완료! '{OUTPUT_CSV_PATH}' 파일이 저장되었습니다.")
        print(f"📊 최종 행 개수: {len(df_filtered)}")
        print("==============================================")

    except FileNotFoundError:
        print(f"🚨 오류: '{INPUT_CSV_PATH}' 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"🚨 처리 중 오류 발생: {e}")