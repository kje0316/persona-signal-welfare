# # --- 라이브러리 임포트 ---
# import pandas as pd
# import requests
# from bs4 import BeautifulSoup
# import re
# import json
# import io
# import pdfplumber
# import time

# # --- 함수 정의 부분 ---

# def get_pdf_info_from_service_url(service_url):
#     """
#     (수정됨) 복지 서비스 상세 페이지 URL에서 'initParameter' 데이터를 분석하여
#     첨부된 PDF 파일의 Payload 정보와 전체 텍스트를 추출하는 함수
#     """
#     try:
#         headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
#         response = requests.get(service_url, headers=headers)
#         response.raise_for_status()
        
#         # 1. initParameter가 포함된 script 태그 찾기
#         match = re.search(r'cpr\.core\.Platform\.INSTANCE\.initParameter\((.*?)\);', response.text, re.DOTALL)
#         if not match:
#             return "정보 없음", "정보 없음"

#         # 2. 전체 데이터 파싱
#         init_data = json.loads(match.group(1))
#         file_list_str = init_data.get("initValue", {}).get("dsWlfareInfoDtl", "[]")
#         file_list = json.loads(file_list_str)

#         # 3. 파일 목록에서 PDF 정보 찾기
#         pdf_info = None
#         for file_item in file_list:
#             if file_item.get("oriFileNm", "").endswith(".pdf"):
#                 pdf_info = file_item
#                 break
        
#         if not pdf_info:
#             return "정보 없음 (PDF 없음)", "정보 없음 (PDF 없음)"
            
#         # 4. 서버에 보낼 Payload 재조립
#         payload_data = {
#             'dmFileInfo': {
#                 'atcflId': pdf_info.get('atcflId'),
#                 'atcflSn': pdf_info.get('atcflSn'),
#                 'wlfareInfoId': pdf_info.get('wlfareInfoId')
#             }
#         }

#         # 5. Payload를 이용해 PDF 다운로드 요청 (POST)
#         download_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52011M/CmmFileUtil/download.do"
#         pdf_response = requests.post(download_url, json=payload_data)
#         pdf_response.raise_for_status()
        
#         # 6. 메모리에서 PDF 텍스트 추출
#         pdf_file_in_memory = io.BytesIO(pdf_response.content)
#         text = ""
#         with pdfplumber.open(pdf_file_in_memory) as pdf:
#             for page in pdf.pages:
#                 page_text = page.extract_text()
#                 if page_text:
#                     text += page_text + "\n"
        
#         full_text = text.strip() if text else "텍스트 없음"
#         return payload_data, full_text

#     except Exception as e:
#         return f"오류 발생: {e}", f"오류 발생: {e}"


# def find_required_documents(full_text):
#     """
#     PDF 전체 텍스트에서 '필요서류' 관련 부분만 추출하는 함수 (기존과 동일)
#     """
#     if not isinstance(full_text, str) or "정보 없음" in full_text or "오류 발생" in full_text or "텍스트 없음" in full_text:
#         return full_text

#     keywords = ['필요서류', '제출서류', '구비서류', '준비서류', '신청서류']
#     lines = full_text.split('\n')
#     start_index = -1
#     for i, line in enumerate(lines):
#         for keyword in keywords:
#             if keyword in line:
#                 start_index = i
#                 break
#         if start_index != -1:
#             break
#     if start_index == -1:
#         return "필요서류 정보 없음"
#     extracted_lines = []
#     for i in range(start_index, len(lines)):
#         line = lines[i].strip()
#         if len(extracted_lines) > 15: break
#         if not line and len(extracted_lines) > 0 and not extracted_lines[-1]: break
#         extracted_lines.append(line)
#     return "\n".join(extracted_lines).strip()


# # --- 메인 실행 부분 ---
# if __name__ == "__main__":
#     INPUT_CSV_PATH = "bokjiro_final_processed.csv"
#     OUTPUT_CSV_PATH = "bokjiro_final_with_docs_v2.csv" # 새 버전으로 파일명 변경
    
#     print(f"'{INPUT_CSV_PATH}' 파일을 읽습니다...")
#     df = pd.read_csv(INPUT_CSV_PATH)

#     df['pdf_payload'] = ""
#     df['required_documents'] = ""
#     total_rows = len(df)
#     print(f"총 {total_rows}개의 복지 서비스에 대한 정보 추출을 시작합니다.")

#     for index, row in df.iterrows():
#         service_id = row.get('복지사업ID', '')
#         service_name = row.get('서비스명', '이름 없음')
#         if not service_id:
#             continue

#         target_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}"
#         print(f"[{index + 1}/{total_rows}] '{service_name}' 처리 중...")
        
#         payload, full_text = get_pdf_info_from_service_url(target_url)
#         required_docs = find_required_documents(full_text)
        
#         df.at[index, 'pdf_payload'] = str(payload)
#         df.at[index, 'required_documents'] = required_docs
        
#         time.sleep(1)

#     print("\n✅ 모든 작업 완료! 결과를 파일로 저장합니다...")
#     df.to_csv(OUTPUT_CSV_PATH, index=False, encoding='utf-8-sig')
#     print(f"🎉 최종 결과가 '{OUTPUT_CSV_PATH}' 파일에 저장되었습니다.")

# --- 라이브러리 임포트 ---
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import json
import io
import pdfplumber
import time
import os

# --- 함수 정의 ---

def get_pdf_text_from_service(service_id):
    """
    복지사업 ID를 이용해 상세 페이지에 접속 → 첨부 PDF → 필요서류 텍스트 추출
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        service_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}&wlfareInfoReldBztpCd=01"
        response = requests.get(service_url, headers=headers)
        response.raise_for_status()

        # 상세페이지 안의 <script> 태그에서 initParameter JSON 찾기
        match = re.search(r'cpr\.core\.Platform\.INSTANCE\.initParameter\((.*?)\);',
                          response.text, re.DOTALL)
        if not match:
            return "첨부파일 정보 없음"

        init_data = json.loads(match.group(1))
        file_list_str = init_data.get("initValue", {}).get("dsAtchFile", "[]")
        file_list = json.loads(file_list_str)

        # PDF 첨부파일만 선택
        pdf_info = None
        for file_item in file_list:
            if file_item.get("oriFileNm", "").endswith(".pdf"):
                pdf_info = file_item
                break

        if not pdf_info:
            return "PDF 없음"

        # Payload 준비
        payload = {
            "dtfInfo": [{
                "atcId": pdf_info.get("atcId"),
                "atcIdSn": pdf_info.get("atcIdSn"),
                "wlfareInfoId": pdf_info.get("wlfareInfoId")
            }]
        }

        # PDF 다운로드
        down_url = "https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/downFile.do"
        pdf_resp = requests.post(down_url, json=payload, headers=headers)
        pdf_resp.raise_for_status()

        # PDF 텍스트 추출
        pdf_file = io.BytesIO(pdf_resp.content)
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            return "텍스트 없음"

        # 필요서류 부분만 발췌
        keywords = ['필요서류', '제출서류', '구비서류', '준비서류', '신청서류']
        lines = text.splitlines()
        start_index = -1
        for i, line in enumerate(lines):
            if any(k in line for k in keywords):
                start_index = i
                break
        if start_index == -1:
            return "필요서류 정보 없음"

        extracted_lines = []
        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            if len(extracted_lines) > 15:  # 너무 길게 안 뽑도록 제한
                break
            if not line and extracted_lines:  # 빈 줄 만나면 종료
                break
            extracted_lines.append(line)

        return "\n".join(extracted_lines).strip()

    except Exception as e:
        return f"오류 발생: {e}"


# --- 메인 실행 ---
if __name__ == "__main__":
    INPUT_CSV = "bokjiro_final_processed.csv"
    OUTPUT_CSV = "bokjiro_final_with_docs.csv"

    df = pd.read_csv(INPUT_CSV)

    # 새 컬럼만 추가
    df["필요서류_추출"] = ""

    total = len(df)
    print(f"총 {total}개 복지 서비스 처리 시작...")

    for idx, row in df.iterrows():
        service_id = row["복지사업ID"]
        service_name = row["복지사업명"]

        print(f"[{idx+1}/{total}] {service_name} ({service_id}) 처리 중...")

        required_docs = get_pdf_text_from_service(service_id)
        df.at[idx, "필요서류_추출"] = required_docs

        time.sleep(1)  # 서버 부하 방지

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n✅ 완료! 결과는 '{OUTPUT_CSV}' 파일에 저장되었습니다.")
