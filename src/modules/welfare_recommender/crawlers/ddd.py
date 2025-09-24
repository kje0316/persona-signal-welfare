# import requests
# import certifi
# import ssl
# import math
# import csv
# import xml.etree.ElementTree as ET
# from requests.adapters import HTTPAdapter
# from urllib3.poolmanager import PoolManager

# # ---------------------------------------------------------------------
# # 1. TLS1.2 강제용 어댑터 정의
# class TLS12Adapter(HTTPAdapter):
#     def init_poolmanager(self, *args, **kwargs):
#         ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)  # TLS1.2 강제
#         ctx.load_verify_locations(certifi.where())
#         kwargs['ssl_context'] = ctx
#         return super().init_poolmanager(*args, **kwargs)
# # ---------------------------------------------------------------------

# # ---------------------------------------------------------------------
# # 2. 세션 준비 (방법 선택)
# def make_session(use_tls12=False):
#     s = requests.Session()
#     s.verify = certifi.where()
#     s.trust_env = False  # 시스템 프록시 무시 (방법①)
#     if use_tls12:        # TLS1.2 강제 (방법②)
#         s.mount("https://", TLS12Adapter())
#     return s
# # ---------------------------------------------------------------------

# # ---------------------------------------------------------------------
# # 3. API 설정
# SERVICE_KEY = "6d4c8b3d1ac688d415302faaf9fd536a3db85e19308ebc90cea7302c56fc9de7"
# URL = "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations/LcgvWelfarelist"

# NUM_OF_ROWS = 100  # 페이지당 최대 건수
# PARAMS = {
#     "serviceKey": SERVICE_KEY,
#     "pageNo": 1,
#     "numOfRows": NUM_OF_ROWS,
# }
# # ---------------------------------------------------------------------

# # ---------------------------------------------------------------------
# # 4. 데이터 수집 함수
# def fetch_all_welfare_data(use_tls12=False, out_csv="welfare_list.csv"):
#     session = make_session(use_tls12=use_tls12)

#     # (1) totalCount 확인
#     resp = session.get(URL, params=PARAMS, timeout=10)
#     root = ET.fromstring(resp.text)
#     total_count = int(root.findtext(".//totalCount", "0"))
#     total_pages = math.ceil(total_count / NUM_OF_ROWS)

#     print(f"총 건수: {total_count}, 총 페이지: {total_pages}")

#     # (2) CSV 저장 준비
#     with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
#         writer = csv.writer(f)
#         writer.writerow(["servId", "servNm"])  # 헤더

#         # (3) 전체 페이지 반복
#         for page in range(1, total_pages + 1):
#             PARAMS["pageNo"] = page
#             r = session.get(URL, params=PARAMS, timeout=10)
#             root = ET.fromstring(r.text)

#             for service in root.findall(".//servList"):
#                 sid = service.findtext("servId", "정보 없음")
#                 snm = service.findtext("servNm", "정보 없음")
#                 writer.writerow([sid, snm])

#             print(f"페이지 {page}/{total_pages} 완료")

#     print(f"👉 {out_csv} 파일로 저장 완료")
# # ---------------------------------------------------------------------

# # ---------------------------------------------------------------------
# # 실행 예시
# if __name__ == "__main__":
#     # 방법①: 프록시 무시 (session.trust_env = False)
#     fetch_all_welfare_data(use_tls12=False, out_csv="welfare_proxy_bypass.csv")

#     # 방법②: TLS1.2 강제
#     fetch_all_welfare_data(use_tls12=True, out_csv="welfare_tls12.csv")
# # ---------------------------------------------------------------------
import socket, ssl

hostname = "apis.data.go.kr"
port = 443

# TLS1.2로 강제
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

with socket.create_connection((hostname, port)) as sock:
    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
        print("연결 성공 ✅")
        print("협상된 TLS 버전:", ssock.version())
        print("협상된 암호화 방식:", ssock.cipher())
