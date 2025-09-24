# import requests
# import json
# import time
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager

# def get_service_list_for_test(count=10):
#     """
#     cURL 정보를 기반으로 완전히 수정된 API 요청 함수입니다.
#     """
#     print(f"✅ 테스트를 위해 {count}개의 서비스 목록을 가져옵니다.")
    
#     # 1. URL 변경
#     list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
    
#     # 2. 헤더 변경 (cURL 기반)
#     headers = {
#         'Accept': 'application/json, text/javascript, */*; q=0.01',
#         'Content-Type': 'application/json; charset=UTF-8',
#         'Origin': 'https://www.bokjiro.go.kr',
#         'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
#         'X-Requested-With': 'XMLHttpRequest'
#     }
    
#     # 3. 데이터 형식 변경 (cURL 기반 JSON)
#     payload = {
#         "dmSearchParam": {
#             "page": "1", # 페이지 번호는 여기에서 변경됩니다.
#             "pageUnit": str(count), # 한 페이지에 가져올 개수
#             "onlineYn": "", "searchTerm": "", "tabId": "1", "orderBy": "date",
#             "bkjrLftmCycCd": "", "daesang": "", "period": "", "age": "",
#             "region": "", "jjim": "", "subject": "", "favoriteKeyword": "Y",
#             "sido": "", "gungu": "", "endYn": "N"
#         },
#         "dmScr": {
#             "curScrId": "tbu/app/twat/twata/twataa/TWAT52005M",
#             "befScrId": ""
#         }
#     }
    
#     try:
#         # requests.post 호출 시 'data=' 대신 'json='을 사용합니다.
#         response = requests.post(list_url, headers=headers, json=payload)
#         response.raise_for_status()
#         data = response.json()
        
#         # 4. 응답 데이터 구조에 맞춰 파싱 로직 변경
#         services = data.get("data", {}).get("resultList", [])
        
#         service_list = [
#             {"id": s.get("wlfareInfoId"), "name": s.get("wlfareInfoNm")}
#             for s in services
#         ]
#         print(f"✔️ {len(service_list)}개 목록 가져오기 성공.")
#         return service_list
        
#     except Exception as e:
#         print(f"❌ 목록 요청 중 오류 발생: {e}")
#         return []

# def scrape_details_for_test(services):
#     """
#     Selenium으로 각 서비스의 '지원대상' 관련 내용을 스크래핑합니다. (이 부분은 변경 없음)
#     """
#     print("\n✅ Selenium으로 상세 정보 스크래핑을 시작합니다.")
    
#     options = webdriver.ChromeOptions()
#     options.add_argument("--headless")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
#     results = []
#     total = len(services)
    
#     for i, service in enumerate(services):
#         service_id = service['id']
#         service_name = service['name']
        
#         if not service_id: continue
            
#         detail_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}&wlfareInfoReldBztpCd=01"
        
#         print(f"({i+1}/{total}) 스크래핑 중: {service_name[:30]}...")
        
#         try:
#             driver.get(detail_url)
#             wait = WebDriverWait(driver, 10)
#             target_content_area = wait.until(
#                 EC.presence_of_element_located((By.XPATH, "//h3[text()='지원대상']/following-sibling::div[1]"))
#             )
#             content_text = target_content_area.text.strip()
            
#             results.append({
#                 "서비스명": service_name,
#                 "지원대상_내용": content_text
#             })
            
#         except Exception as e:
#             print(f"  - 오류 발생: {service_name} ({e})")
#             results.append({
#                 "서비스명": service_name,
#                 "지원대상_내용": "스크래핑 오류 발생"
#             })
    
#     driver.quit()
#     return results

# # --- 메인 실행 ---
# if __name__ == "__main__":
#     # 10개 대신 5개만 가져오도록 수정 (테스트 속도 향상)
#     test_services = get_service_list_for_test(5)
    
#     if test_services:
#         scraped_data = scrape_details_for_test(test_services)
        
#         print("\n\n--- 최종 스크래핑 결과 (5개) ---")
#         for item in scraped_data:
#             print(f"\n[서비스명] {item['서비스명']}")
#             print(f"[지원대상 내용]\n{item['지원대상_내용']}")
#             print("-" * 20)

# 
# import requests
# import json
# import time
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager

# def get_service_list_for_test(count=10):
#     """
#     서버 응답 구조에 맞춰 파싱 로직을 수정한 최종 버전입니다.
#     """
#     print(f"✅ {count}개의 서비스 목록을 요청합니다.")
    
#     list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
    
#     headers = {
#         'Accept': 'application/json, text/javascript, */*; q=0.01',
#         'Content-Type': 'application/json; charset=UTF-8',
#         'Origin': 'https://www.bokjiro.go.kr',
#         'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
#         'X-Requested-With': 'XMLHttpRequest'
#     }
    
#     payload = {
#         "dmSearchParam": {
#             "page": "1", "pageUnit": str(count), "onlineYn": "", "searchTerm": "", "tabId": "1", "orderBy": "date",
#             "bkjrLftmCycCd": "", "daesang": "", "period": "", "age": "", "region": "", "jjim": "",
#             "subject": "", "favoriteKeyword": "Y", "sido": "", "gungu": "", "endYn": "N"
#         },
#         "dmScr": {"curScrId": "tbu/app/twat/twata/twataa/TWAT52005M", "befScrId": ""}
#     }
    
#     try:
#         response = requests.post(list_url, headers=headers, json=payload)
#         response.raise_for_status()
#         data = response.json()
        
#         # --- ✨ 수정한 부분 시작 ✨ ---
#         # dsServiceList0, 1, 2, 3 에 나뉘어 담긴 목록을 모두 가져와 합칩니다.
#         all_services_raw = []
#         for i in range(4): # dsServiceList0 부터 dsServiceList3 까지 확인
#             all_services_raw.extend(data.get(f"dsServiceList{i}", []))
        
#         # 필요한 ID와 이름만 추출합니다.
#         service_list = [
#             {"id": s.get("WLFARE_INFO_ID"), "name": s.get("WLFARE_INFO_NM")}
#             for s in all_services_raw
#         ]
#         # --- ✨ 수정한 부분 끝 ✨ ---
        
#         # 실제 가져온 서비스 개수만큼만 슬라이싱 (요청 개수보다 많을 수 있음)
#         service_list = service_list[:count]

#         print(f"✔️ {len(service_list)}개 목록 가져오기 성공.")
#         return service_list
        
#     except Exception as e:
#         print(f"❌ 목록 요청 중 오류 발생: {e}")
#         return []

# def scrape_details_for_test(services):
#     """
#     Selenium으로 각 서비스의 '지원대상' 관련 내용을 스크래핑합니다.
#     """
#     print("\n✅ Selenium으로 상세 정보 스크래핑을 시작합니다.")
    
#     options = webdriver.ChromeOptions()
#     options.add_argument("--headless")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
#     results = []
#     total = len(services)
    
#     for i, service in enumerate(services):
#         service_id = service['id']
#         service_name = service['name']
        
#         if not service_id: continue
            
#         detail_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}&wlfareInfoReldBztpCd=01"
        
#         print(f"({i+1}/{total}) 스크래핑 중: {service_name[:30]}...")
        
#         try:
#             driver.get(detail_url)
#             wait = WebDriverWait(driver, 10)
#             target_content_area = wait.until(
#                 EC.presence_of_element_located((By.XPATH, "//h3[text()='지원대상']/following-sibling::div[1]"))
#             )
#             content_text = target_content_area.text.strip()
            
#             results.append({
#                 "서비스명": service_name,
#                 "지원대상_내용": content_text
#             })
            
#         except Exception as e:
#             print(f"  - 오류 발생: {service_name} ({e})")
#             results.append({
#                 "서비스명": service_name,
#                 "지원대상_내용": "스크래핑 오류 발생"
#             })
    
#     driver.quit()
#     return results

# # --- 메인 실행 ---
# if __name__ == "__main__":
#     test_services = get_service_list_for_test(10)
    
#     if test_services:
#         scraped_data = scrape_details_for_test(test_services)
        
#         print("\n\n--- 최종 스크래핑 결과 (10개) ---")
#         for item in scraped_data:
#             print(f"\n[서비스명] {item['서비스명']}")
#             print(f"[지원대상 내용]\n{item['지원대상_내용']}")
#             print("-" * 20)

# import requests
# import json
# import time
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager

# def get_service_list_for_test(count=10):
#     # 이 부분은 정상 작동하므로 변경 없습니다.
#     print(f"✅ {count}개의 서비스 목록을 요청합니다.")
#     list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
#     headers = {
#         'Accept': 'application/json, text/javascript, */*; q=0.01',
#         'Content-Type': 'application/json; charset=UTF-8',
#         'Origin': 'https://www.bokjiro.go.kr',
#         'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
#         'X-Requested-With': 'XMLHttpRequest'
#     }
#     payload = {
#         "dmSearchParam": {"page": "1", "pageUnit": str(count), "onlineYn": "", "searchTerm": "", "tabId": "1", "orderBy": "date", "bkjrLftmCycCd": "", "daesang": "", "period": "", "age": "", "region": "", "jjim": "", "subject": "", "favoriteKeyword": "Y", "sido": "", "gungu": "", "endYn": "N"},
#         "dmScr": {"curScrId": "tbu/app/twat/twata/twataa/TWAT52005M", "befScrId": ""}
#     }
#     try:
#         response = requests.post(list_url, headers=headers, json=payload)
#         response.raise_for_status()
#         data = response.json()
#         all_services_raw = []
#         for i in range(4):
#             all_services_raw.extend(data.get(f"dsServiceList{i}", []))
#         service_list = [{"id": s.get("WLFARE_INFO_ID"), "name": s.get("WLFARE_INFO_NM")} for s in all_services_raw]
#         service_list = service_list[:count]
#         print(f"✔️ {len(service_list)}개 목록 가져오기 성공.")
#         return service_list
#     except Exception as e:
#         print(f"❌ 목록 요청 중 오류 발생: {e}")
#         return []

# def scrape_details_for_test(services):
#     """
#     안정성 옵션을 추가하고 headless 모드를 비활성화하여 수정한 버전입니다.
#     """
#     print("\n✅ Selenium으로 상세 정보 스크래핑을 시작합니다.")
    
#     options = webdriver.ChromeOptions()
    
#     # --- ✨ 수정된 부분 시작 ✨ ---
#     # options.add_argument("--headless")  # 원인이 될 수 있으므로 잠시 주석 처리 (창이 보이게 됨)
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
    
#     # 안정성을 높이는 옵션 추가
#     options.add_argument("--disable-gpu") # GPU 가속 비활성화 (충돌 방지)
#     options.add_argument("window-size=1920x1080") # 창 크기 지정
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
#     # --- ✨ 수정된 부분 끝 ✨ ---

#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
#     results = []
#     total = len(services)
    
#     for i, service in enumerate(services):
#         service_id = service['id']
#         service_name = service['name']
        
#         if not service_id: continue
            
#         detail_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}&wlfareInfoReldBztpCd=01"
        
#         print(f"({i+1}/{total}) 스크래핑 중: {service_name[:30]}...")
        
#         try:
#             driver.get(detail_url)
#             wait = WebDriverWait(driver, 10)
#             target_content_area = wait.until(
#                 EC.presence_of_element_located((By.XPATH, "//h3[text()='지원대상']/following-sibling::div[1]"))
#             )
#             content_text = target_content_area.text.strip()
            
#             results.append({"서비스명": service_name, "지원대상_내용": content_text})
            
#         except Exception as e:
#             # 오류 메시지를 더 자세히 보기 위해 e를 출력하도록 변경
#             print(f"  - 오류 발생: {service_name} ({e.__class__.__name__})")
#             results.append({"서비스명": service_name, "지원대상_내용": "스크래핑 오류 발생"})
    
#     driver.quit()
#     return results

# # --- 메인 실행 ---
# if __name__ == "__main__":
#     test_services = get_service_list_for_test(10)
    
#     if test_services:
#         scraped_data = scrape_details_for_test(test_services)
        
#         print("\n\n--- 최종 스크래핑 결과 (10개) ---")
#         for item in scraped_data:
#             print(f"\n[서비스명] {item['서비스명']}")
#             print(f"[지원대상 내용]\n{item['지원대상_내용']}")
#             print("-" * 20)

# import requests
# import json
# import time
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException # 예외 처리를 위해 추가
# from webdriver_manager.chrome import ChromeDriverManager

# # get_service_list_for_test 함수는 변경 없이 그대로 사용합니다.
# def get_service_list_for_test(count=10):
#     print(f"✅ {count}개의 서비스 목록을 요청합니다.")
#     list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
#     headers = {'Accept': 'application/json, text/javascript, */*; q=0.01', 'Content-Type': 'application/json; charset=UTF-8', 'Origin': 'https://www.bokjiro.go.kr', 'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36', 'X-Requested-With': 'XMLHttpRequest'}
#     payload = {"dmSearchParam": {"page": "1", "pageUnit": str(count), "onlineYn": "", "searchTerm": "", "tabId": "1", "orderBy": "date", "bkjrLftmCycCd": "", "daesang": "", "period": "", "age": "", "region": "", "jjim": "", "subject": "", "favoriteKeyword": "Y", "sido": "", "gungu": "", "endYn": "N"}, "dmScr": {"curScrId": "tbu/app/twat/twata/twataa/TWAT52005M", "befScrId": ""}}
#     try:
#         response = requests.post(list_url, headers=headers, json=payload)
#         response.raise_for_status()
#         data = response.json()
#         all_services_raw = []
#         for i in range(4):
#             all_services_raw.extend(data.get(f"dsServiceList{i}", []))
#         service_list = [{"id": s.get("WLFARE_INFO_ID"), "name": s.get("WLFARE_INFO_NM")} for s in all_services_raw]
#         service_list = service_list[:count]
#         print(f"✔️ {len(service_list)}개 목록 가져오기 성공.")
#         return service_list
#     except Exception as e:
#         print(f"❌ 목록 요청 중 오류 발생: {e}")
#         return []

# def scrape_details_for_test(services):
#     """
#     팝업창 닫기 로직이 추가된 최종 버전입니다.
#     """
#     print("\n✅ Selenium으로 상세 정보 스크래핑을 시작합니다.")
    
#     options = webdriver.ChromeOptions()
#     # options.add_argument("--headless") # 최종 완료 시 주석 해제하여 사용
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("window-size=1920x1080")
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
#     results = []
#     total = len(services)
    
#     for i, service in enumerate(services):
#         service_id = service['id']
#         service_name = service['name']
        
#         if not service_id: continue
            
#         detail_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}&wlfareInfoReldBztpCd=01"
        
#         print(f"({i+1}/{total}) 스크래핑 중: {service_name[:30]}...")
        
#         try:
#             driver.get(detail_url)
#             wait = WebDriverWait(driver, 10)
            
#             # --- ✨ 팝업 처리 로직 시작 ✨ ---
#             try:
#                 # 팝업의 '닫기' 버튼이 5초 안에 나타나면 찾아서 클릭
#                 popup_close_button = WebDriverWait(driver, 5).until(
#                     EC.element_to_be_clickable((By.CSS_SELECTOR, "#research_pop .btn-close-pop"))
#                 )
#                 popup_close_button.click()
#                 print("  - 팝업창을 닫았습니다.")
#             except TimeoutException:
#                 # 5초 안에 팝업이 안 나타나면 그냥 넘어감
#                 print("  - 팝업이 나타나지 않았습니다.")
#                 pass
#             # --- ✨ 팝업 처리 로직 끝 ✨ ---
            
#             # 이제 팝업이 없으므로, 원래 찾으려던 '지원대상' 내용을 찾습니다.
#             target_content_area = wait.until(
#                 EC.presence_of_element_located((By.XPATH, "//h3[contains(text(),'지원대상')]/following-sibling::div[1]"))
#             )
#             content_text = target_content_area.text.strip()
            
#             results.append({"서비스명": service_name, "지원대상_내용": content_text})
            
#         except Exception as e:
#             print(f"  - 오류 발생: {service_name} ({e.__class__.__name__})")
#             results.append({"서비스명": service_name, "지원대상_내용": "스크래핑 오류 발생"})
    
#     driver.quit()
#     return results

# # --- 메인 실행 ---
# if __name__ == "__main__":
#     test_services = get_service_list_for_test(10)
    
#     if test_services:
#         scraped_data = scrape_details_for_test(test_services)
        
#         print("\n\n--- 최종 스크래핑 결과 (10개) ---")
#         for item in scraped_data:
#             print(f"\n[서비스명] {item['서비스명']}")
#             print(f"[지원대상 내용]\n{item['지원대상_내용']}")
#             print("-" * 20)

# import requests
# import json
# import csv
# import time
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
# from webdriver_manager.chrome import ChromeDriverManager

# def get_all_service_list():
#     """
#     복지로 API를 호출하여 전체 서비스 목록(ID, 이름)을 가져옵니다.
#     페이지를 자동으로 넘기며 모든 목록을 수집합니다.
#     """
#     print("✅ [1단계] 전체 복지 서비스 목록 수집을 시작합니다.")
#     list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
#     headers = {
#         'Accept': 'application/json, text/javascript, */*; q=0.01',
#         'Content-Type': 'application/json; charset=UTF-8',
#         'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
#     }
#     payload_template = {
#         "dmSearchParam": {"page": "1", "pageUnit": "100", "orderBy": "date", "endYn": "N"},
#         "dmScr": {"curScrId": "tbu/app/twat/twata/twataa/TWAT52005M"}
#     }
    
#     all_services = []
#     current_page = 1
    
#     while True:
#         print(f"📄 목록 {current_page}페이지를 요청합니다...")
#         payload_template["dmSearchParam"]["page"] = str(current_page)
        
#         try:
#             response = requests.post(list_url, headers=headers, json=payload_template)
#             response.raise_for_status()
#             data = response.json()
            
#             services_on_page = []
#             for i in range(4): # dsServiceList0 ~ dsServiceList3 확인
#                 services_on_page.extend(data.get(f"dsServiceList{i}", []))

#             if not services_on_page:
#                 print("✔️ 더 이상 가져올 목록이 없습니다.")
#                 break
            
#             for service in services_on_page:
#                 all_services.append({
#                     "id": service.get("WLFARE_INFO_ID"),
#                     "name": service.get("WLFARE_INFO_NM")
#                 })
            
#             current_page += 1
#             time.sleep(0.5)
            
#         except Exception as e:
#             print(f"❌ 목록 요청 중 오류 발생: {e}")
#             break
            
#     print(f"🎉 총 {len(all_services)}개의 서비스 목록을 수집했습니다.")
#     return all_services

# def scrape_details_by_clicking_tabs(services):
#     """
#     Selenium으로 각 서비스의 탭을 클릭하며 상세 내용을 스크래핑합니다.
#     """
#     print("\n✅ [2단계] Selenium으로 상세 정보 스크래핑을 시작합니다.")
    
#     options = webdriver.ChromeOptions()
#     options.add_experimental_option('excludeSwitches', ['enable-logging'])
#     options.add_argument('--log-level=3')
#     options.add_argument("--headless") # 백그라운드 실행을 원하면 이 줄의 주석을 해제
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("window-size=1920x1080")
    
#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
#     final_results = []
#     total = len(services)
    
#     for i, service in enumerate(services):
#         service_id = service['id']
#         service_name = service['name']
        
#         if not service_id: continue
            
#         detail_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}"
        
#         print(f"({i+1}/{total}) 스크래핑 중: {service_name[:30]}...")
        
#         try:
#             driver.get(detail_url)
            
#             # 팝업 처리
#             try:
#                 popup_close_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#research_pop .btn-close-pop")))
#                 popup_close_button.click()
#             except TimeoutException:
#                 pass
            
#             # 스크래핑할 탭 이름 목록
#             tabs_to_scrape = ["지원대상", "서비스 내용"] # '신청방법' 등 추가 가능
#             scraped_content = {"서비스명": service_name}
            
#             for tab_name in tabs_to_scrape:
#                 try:
#                     # 1. 탭 버튼을 찾아서 클릭
#                     # XPath를 사용해 텍스트를 포함하는 <a> 태그를 찾음
#                     tab_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, f"//a[@class='cl-text-wrapper' and contains(., '{tab_name}')]")))
#                     tab_button.click()
                    
#                     # 2. 내용이 로딩될 시간을 잠시 줌 (클릭 후 DOM이 변경되는 시간)
#                     time.sleep(0.5) 
                    
#                     # 3. 내용이 표시되는 컨테이너를 찾아 텍스트 추출
#                     content_container = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.tab-content-inner")))
#                     scraped_content[tab_name] = content_container.text.strip()
                    
#                 except Exception as tab_e:
#                     print(f"  - '{tab_name}' 탭 처리 중 오류: {tab_e.__class__.__name__}")
#                     scraped_content[tab_name] = "내용을 가져올 수 없음"
            
#             final_results.append(scraped_content)
            
#         except Exception as e:
#             print(f"  - 페이지 처리 중 심각한 오류 발생: {service_name} ({e.__class__.__name__})")
#             final_results.append({"서비스명": service_name, "지원대상": "오류", "서비스 내용": "오류"})
    
#     driver.quit()
#     print("🎉 상세 정보 스크래핑을 완료했습니다.")
#     return final_results

# def save_results(data):
#     """
#     수집된 데이터를 CSV와 JSON 파일로 저장합니다.
#     """
#     if not data:
#         print("⚠️ 저장할 데이터가 없습니다.")
#         return
        
#     print("\n✅ [3단계] 수집된 데이터를 파일로 저장합니다.")
    
#     # CSV 파일로 저장
#     try:
#         with open('bokjiro_services.csv', 'w', newline='', encoding='utf-8-sig') as f:
#             # 동적으로 필드 이름을 설정 (서비스명, 지원대상, 서비스 내용, ...)
#             fieldnames = list(data[0].keys())
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             writer.writerows(data)
#         print("💾 CSV 파일 저장 완료: bokjiro_services.csv")
#     except Exception as e:
#         print(f"❌ CSV 파일 저장 중 오류: {e}")
        
#     # JSON 파일로 저장
#     try:
#         with open('bokjiro_services.json', 'w', encoding='utf-8') as f:
#             json.dump(data, f, ensure_ascii=False, indent=4)
#         print("💾 JSON 파일 저장 완료: bokjiro_services.json")
#     except Exception as e:
#         print(f"❌ JSON 파일 저장 중 오류: {e}")

# # --- 메인 코드 실행 ---
# if __name__ == "__main__":
#     # 테스트를 위해 목록 개수 제한: services_list = get_all_service_list()[:10]
#     services_list = get_all_service_list()
    
#     if services_list:
#         detailed_data = scrape_details_by_clicking_tabs(services_list)
#         save_results(detailed_data)
        
#     print("\n✨ 모든 크롤링 작업이 종료되었습니다.")

# import requests
# import json
# import csv
# import time
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
# from webdriver_manager.chrome import ChromeDriverManager

# def get_all_service_list():
#     """
#     복지로 API를 호출하여 전체 서비스 목록(ID, 이름)을 가져옵니다.
#     """
#     print("✅ [1단계] 전체 복지 서비스 목록 수집을 시작합니다.")
#     list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
#     headers = {
#         'Accept': 'application/json, text/javascript, */*; q=0.01',
#         'Content-Type': 'application/json; charset=UTF-8',
#         'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
#     }
    
#     # --- ✨ 수정된 부분: 누락되었던 필수 요청값을 모두 복원 ---
#     payload_template = {
#         "dmSearchParam": {
#             "page": "1", "pageUnit": "100", "onlineYn": "", "searchTerm": "", "tabId": "1", "orderBy": "date",
#             "bkjrLftmCycCd": "", "daesang": "", "period": "", "age": "", "region": "", "jjim": "",
#             "subject": "", "favoriteKeyword": "Y", "sido": "", "gungu": "", "endYn": "N"
#         },
#         "dmScr": {"curScrId": "tbu/app/twat/twata/twataa/TWAT52005M", "befScrId": ""}
#     }
#     # ---
    
#     all_services = []
#     current_page = 1
    
#     while True:
#         print(f"📄 목록 {current_page}페이지를 요청합니다...")
#         payload_template["dmSearchParam"]["page"] = str(current_page)
        
#         try:
#             response = requests.post(list_url, headers=headers, json=payload_template)
#             response.raise_for_status()
#             data = response.json()
            
#             services_on_page = []
#             for i in range(4):
#                 services_on_page.extend(data.get(f"dsServiceList{i}", []))

#             if not services_on_page:
#                 print("✔️ 더 이상 가져올 목록이 없습니다.")
#                 break
            
#             for service in services_on_page:
#                 all_services.append({
#                     "id": service.get("WLFARE_INFO_ID"),
#                     "name": service.get("WLFARE_INFO_NM")
#                 })
            
#             current_page += 1
#             time.sleep(0.5)
            
#         except Exception as e:
#             print(f"❌ 목록 요청 중 오류 발생: {e}")
#             break
            
#     print(f"🎉 총 {len(all_services)}개의 서비스 목록을 수집했습니다.")
#     return all_services

# def scrape_details_by_clicking_tabs(services):
#     """
#     Selenium으로 각 서비스의 탭을 클릭하며 상세 내용을 스크래핑합니다.
#     """
#     print("\n✅ [2단계] Selenium으로 상세 정보 스크래핑을 시작합니다.")
    
#     options = webdriver.ChromeOptions()
#     options.add_experimental_option('excludeSwitches', ['enable-logging'])
#     options.add_argument('--log-level=3')
#     # options.add_argument("--headless")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("window-size=1920x1080")
    
#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
#     final_results = []
#     total = len(services)
    
#     for i, service in enumerate(services):
#         service_id = service['id']
#         service_name = service['name']
        
#         if not service_id: continue
            
#         detail_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}"
        
#         print(f"({i+1}/{total}) 스크래핑 중: {service_name[:30]}...")
        
#         try:
#             driver.get(detail_url)
            
#             try:
#                 popup_close_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#research_pop .btn-close-pop")))
#                 popup_close_button.click()
#             except TimeoutException:
#                 pass
            
#             tabs_to_scrape = ["지원대상", "서비스 내용"]
#             scraped_content = {"서비스명": service_name}
            
#             for tab_name in tabs_to_scrape:
#                 try:
#                     tab_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, f"//a[@class='cl-text-wrapper' and contains(., '{tab_name}')]")))
#                     tab_button.click()
#                     time.sleep(0.5) 
#                     content_container = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.tab-content-inner")))
#                     scraped_content[tab_name] = content_container.text.strip()
#                 except Exception as tab_e:
#                     print(f"  - '{tab_name}' 탭 처리 중 오류: {tab_e.__class__.__name__}")
#                     scraped_content[tab_name] = "내용을 가져올 수 없음"
            
#             final_results.append(scraped_content)
            
#         except Exception as e:
#             print(f"  - 페이지 처리 중 심각한 오류 발생: {service_name} ({e.__class__.__name__})")
#             final_results.append({"서비스명": service_name, "지원대상": "오류", "서비스 내용": "오류"})
    
#     driver.quit()
#     print("🎉 상세 정보 스크래핑을 완료했습니다.")
#     return final_results

# def save_results(data):
#     """
#     수집된 데이터를 CSV와 JSON 파일로 저장합니다.
#     """
#     if not data:
#         print("⚠️ 저장할 데이터가 없습니다.")
#         return
        
#     print("\n✅ [3단계] 수집된 데이터를 파일로 저장합니다.")
    
#     try:
#         with open('bokjiro_services.csv', 'w', newline='', encoding='utf-8-sig') as f:
#             fieldnames = list(data[0].keys())
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             writer.writerows(data)
#         print("💾 CSV 파일 저장 완료: bokjiro_services.csv")
#     except Exception as e:
#         print(f"❌ CSV 파일 저장 중 오류: {e}")
        
#     try:
#         with open('bokjiro_services.json', 'w', encoding='utf-8') as f:
#             json.dump(data, f, ensure_ascii=False, indent=4)
#         print("💾 JSON 파일 저장 완료: bokjiro_services.json")
#     except Exception as e:
#         print(f"❌ JSON 파일 저장 중 오류: {e}")

# # --- 메인 코드 실행 ---
# # --- 메인 코드 실행 ---
# if __name__ == "__main__":
#     # 테스트를 위해 전체 목록 중 10개만 잘라서 사용
#     services_list = get_all_service_list()[:10]
    
#     if services_list:
#         detailed_data = scrape_details_by_clicking_tabs(services_list)
#         save_results(detailed_data)
        
#     print("\n✨ 모든 크롤링 작업이 종료되었습니다.")

# import requests
# import json
# import csv
# import time
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
# from webdriver_manager.chrome import ChromeDriverManager

# # 원하는 개수만큼만 가져오도록 limit 인자 추가
# def get_all_service_list(limit=None):
#     """
#     복지로 API를 호출하여 서비스 목록을 가져옵니다.
#     limit이 지정되면 해당 개수만큼만 가져오고 중단합니다.
#     """
#     print("✅ [1단계] 복지 서비스 목록 수집을 시작합니다.")
#     # ... (URL, headers, payload 등 다른 부분은 동일) ...
#     list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
#     headers = {'Accept': 'application/json, text/javascript, */*; q=0.01', 'Content-Type': 'application/json; charset=UTF-8', 'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',}
#     payload_template = {"dmSearchParam": {"page": "1", "pageUnit": "100", "onlineYn": "", "searchTerm": "", "tabId": "1", "orderBy": "date", "bkjrLftmCycCd": "", "daesang": "", "period": "", "age": "", "region": "", "jjim": "", "subject": "", "favoriteKeyword": "Y", "sido": "", "gungu": "", "endYn": "N"}, "dmScr": {"curScrId": "tbu/app/twat/twata/twataa/TWAT52005M", "befScrId": ""}}
    
#     all_services = []
#     current_page = 1
    
#     while True:
#         print(f"📄 목록 {current_page}페이지를 요청합니다...")
#         payload_template["dmSearchParam"]["page"] = str(current_page)
        
#         try:
#             response = requests.post(list_url, headers=headers, json=payload_template)
#             response.raise_for_status()
#             data = response.json()
            
#             services_on_page = []
#             for i in range(4):
#                 services_on_page.extend(data.get(f"dsServiceList{i}", []))

#             if not services_on_page:
#                 print("✔️ 더 이상 가져올 목록이 없습니다.")
#                 break
            
#             for service in services_on_page:
#                 all_services.append({"id": service.get("WLFARE_INFO_ID"), "name": service.get("WLFARE_INFO_NM")})
            
#             # --- ✨ 수정된 부분 시작 ✨ ---
#             # 만약 limit이 있고, 수집한 개수가 limit을 넘으면 반복 중단
#             if limit and len(all_services) >= limit:
#                 print(f"✔️ 요청하신 {limit}개 이상의 목록을 수집하여 중단합니다.")
#                 break
#             # --- ✨ 수정된 부분 끝 ✨ ---
            
#             current_page += 1
#             time.sleep(0.5)
            
#         except Exception as e:
#             print(f"❌ 목록 요청 중 오류 발생: {e}")
#             break
    
#     # 최종적으로 limit 개수만큼만 잘라서 반환
#     if limit:
#         all_services = all_services[:limit]

#     print(f"🎉 총 {len(all_services)}개의 서비스 목록을 수집했습니다.")
#     return all_services

# # scrape_details_by_clicking_tabs 함수와 save_results 함수는 변경 없습니다.
# def scrape_details_by_clicking_tabs(services):
#     print("\n✅ [2단계] Selenium으로 상세 정보 스크래핑을 시작합니다.")
#     options = webdriver.ChromeOptions()
#     options.add_experimental_option('excludeSwitches', ['enable-logging'])
#     options.add_argument('--log-level=3')
#     # options.add_argument("--headless")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("window-size=1920x1080")
#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
#     final_results = []
#     total = len(services)
#     for i, service in enumerate(services):
#         service_id, service_name = service['id'], service['name']
#         if not service_id: continue
#         detail_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}"
#         print(f"({i+1}/{total}) 스크래핑 중: {service_name[:30]}...")
#         try:
#             driver.get(detail_url)
#             try:
#                 WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#research_pop .btn-close-pop"))).click()
#             except TimeoutException:
#                 pass
#             tabs_to_scrape = ["지원대상", "서비스 내용"]
#             scraped_content = {"서비스명": service_name}
#             for tab_name in tabs_to_scrape:
#                 try:
#                     WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, f"//a[@class='cl-text-wrapper' and contains(., '{tab_name}')]"))).click()
#                     time.sleep(0.5)
#                     content_container = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.tab-content-inner")))
#                     scraped_content[tab_name] = content_container.text.strip()
#                 except Exception:
#                     scraped_content[tab_name] = "내용을 가져올 수 없음"
#             final_results.append(scraped_content)
#         except Exception:
#             final_results.append({"서비스명": service_name, "지원대상": "오류", "서비스 내용": "오류"})
#     driver.quit()
#     print("🎉 상세 정보 스크래핑을 완료했습니다.")
#     return final_results
# def save_results(data):
#     if not data: print("⚠️ 저장할 데이터가 없습니다."); return
#     print("\n✅ [3단계] 수집된 데이터를 파일로 저장합니다.")
#     try:
#         with open('bokjiro_services.csv', 'w', newline='', encoding='utf-8-sig') as f:
#             fieldnames = list(data[0].keys()); writer = csv.DictWriter(f, fieldnames=fieldnames); writer.writeheader(); writer.writerows(data)
#         print("💾 CSV 파일 저장 완료: bokjiro_services.csv")
#     except Exception as e: print(f"❌ CSV 파일 저장 중 오류: {e}")
#     try:
#         with open('bokjiro_services.json', 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
#         print("💾 JSON 파일 저장 완료: bokjiro_services.json")
#     except Exception as e: print(f"❌ JSON 파일 저장 중 오류: {e}")

# # --- 메인 코드 실행 ---
# if __name__ == "__main__":
#     # 🧪 테스트: 10개만 가져오기
#     services_list = get_all_service_list(limit=10)
    
#     # 🚀 전체 실행: 모든 목록 가져오기
#     # services_list = get_all_service_list()
    
#     if services_list:
#         detailed_data = scrape_details_by_clicking_tabs(services_list)
#         save_results(detailed_data)
        
#     print("\n✨ 모든 크롤링 작업이 종료되었습니다.")

# import requests
# import json
# import csv
# import time
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
# from webdriver_manager.chrome import ChromeDriverManager

# def get_all_service_list(limit=None):
#     """
#     복지로 API를 호출하여 서비스 목록을 가져옵니다.
#     limit이 지정되면 해당 개수만큼만 가져오고 중단하여 테스트 속도를 높입니다.
#     """
#     print("✅ [1단계] 복지 서비스 목록 수집을 시작합니다.")
#     list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
#     headers = {
#         'Accept': 'application/json, text/javascript, */*; q=0.01',
#         'Content-Type': 'application/json; charset=UTF-8',
#         'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
#     }
#     payload_template = {
#         "dmSearchParam": {
#             "page": "1", "pageUnit": "100", "onlineYn": "", "searchTerm": "", "tabId": "1", "orderBy": "date",
#             "bkjrLftmCycCd": "", "daesang": "", "period": "", "age": "", "region": "", "jjim": "",
#             "subject": "", "favoriteKeyword": "Y", "sido": "", "gungu": "", "endYn": "N"
#         },
#         "dmScr": {"curScrId": "tbu/app/twat/twata/twataa/TWAT52005M", "befScrId": ""}
#     }
    
#     all_services = []
#     current_page = 1
    
#     while True:
#         # 루프가 limit을 넘지 않도록 방지 (필수는 아니나 추가적인 안전장치)
#         if limit and len(all_services) >= limit:
#             break
            
#         print(f"📄 목록 {current_page}페이지를 요청합니다...")
#         payload_template["dmSearchParam"]["page"] = str(current_page)
        
#         try:
#             response = requests.post(list_url, headers=headers, json=payload_template)
#             response.raise_for_status()
#             data = response.json()
            
#             services_on_page = []
#             for i in range(4): # dsServiceList0 ~ dsServiceList3 확인
#                 services_on_page.extend(data.get(f"dsServiceList{i}", []))

#             if not services_on_page:
#                 print("✔️ 더 이상 가져올 목록이 없습니다.")
#                 break
            
#             for service in services_on_page:
#                 all_services.append({"id": service.get("WLFARE_INFO_ID"), "name": service.get("WLFARE_INFO_NM")})
            
#             # limit이 지정되었고, 수집한 개수가 limit을 넘으면 반복 중단
#             if limit and len(all_services) >= limit:
#                 print(f"✔️ 요청하신 {limit}개 이상의 목록을 수집하여 중단합니다.")
#                 break
            
#             current_page += 1
#             time.sleep(0.5)
            
#         except Exception as e:
#             print(f"❌ 목록 요청 중 오류 발생: {e}")
#             break
    
#     # 최종적으로 limit 개수만큼만 잘라서 반환
#     if limit:
#         all_services = all_services[:limit]

#     print(f"🎉 총 {len(all_services)}개의 서비스 목록을 수집했습니다.")
#     return all_services

# def scrape_details_by_clicking_tabs(services):
#     """
#     Selenium으로 각 서비스의 탭을 클릭하며 상세 내용을 스크래핑합니다.
#     """
#     print("\n✅ [2단계] Selenium으로 상세 정보 스크래핑을 시작합니다.")
    
#     options = webdriver.ChromeOptions()
#     options.add_experimental_option('excludeSwitches', ['enable-logging'])
#     options.add_argument('--log-level=3')
#     # options.add_argument("--headless") # 백그라운드 실행을 원하면 이 줄의 주석을 해제하세요.
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("window-size=1920x1080")
    
#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
#     final_results = []
#     total = len(services)
    
#     for i, service in enumerate(services):
#         service_id = service['id']
#         service_name = service['name']
        
#         if not service_id: continue
            
#         detail_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}"
        
#         print(f"({i+1}/{total}) 스크래핑 중: {service_name[:30]}...")
        
#         try:
#             driver.get(detail_url)
            
#             # 팝업 처리 (3초만 기다림)
#             try:
#                 popup_close_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#research_pop .btn-close-pop")))
#                 popup_close_button.click()
#             except TimeoutException:
#                 pass # 팝업이 없으면 그냥 넘어감
            
#             # 스크래핑할 탭 이름 목록
#             tabs_to_scrape = ["지원대상", "서비스 내용"]
#             scraped_content = {"서비스명": service_name}
            
#             for tab_name in tabs_to_scrape:
#                 try:
#                     # 1. 탭 버튼을 찾아서 클릭
#                     tab_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, f"//a[@class='cl-text-wrapper' and contains(., '{tab_name}')]")))
#                     tab_button.click()
                    
#                     # 2. 내용이 로딩될 시간을 잠시 줌
#                     time.sleep(0.5) 
                    
#                     # 3. 내용이 표시되는 컨테이너를 찾아 텍스트 추출
#                     content_container = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.tab-content-inner")))
#                     scraped_content[tab_name] = content_container.text.strip()
                    
#                 except Exception:
#                     scraped_content[tab_name] = "내용을 가져올 수 없음"
            
#             final_results.append(scraped_content)
            
#         except Exception as e:
#             print(f"  - 페이지 처리 중 심각한 오류 발생: {service_name} ({e.__class__.__name__})")
#             final_results.append({"서비스명": service_name, "지원대상": "오류", "서비스 내용": "오류"})
    
#     driver.quit()
#     print("🎉 상세 정보 스크래핑을 완료했습니다.")
#     return final_results

# def save_results(data):
#     """
#     수집된 데이터를 CSV와 JSON 파일로 저장합니다.
#     """
#     if not data:
#         print("⚠️ 저장할 데이터가 없습니다.")
#         return
        
#     print("\n✅ [3단계] 수집된 데이터를 파일로 저장합니다.")
    
#     try:
#         with open('bokjiro_services.csv', 'w', newline='', encoding='utf-8-sig') as f:
#             fieldnames = list(data[0].keys())
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             writer.writerows(data)
#         print("💾 CSV 파일 저장 완료: bokjiro_services.csv")
#     except Exception as e:
#         print(f"❌ CSV 파일 저장 중 오류: {e}")
        
#     try:
#         with open('bokjiro_services.json', 'w', encoding='utf-8') as f:
#             json.dump(data, f, ensure_ascii=False, indent=4)
#         print("💾 JSON 파일 저장 완료: bokjiro_services.json")
#     except Exception as e:
#         print(f"❌ JSON 파일 저장 중 오류: {e}")

# # --- 메인 코드 실행 ---
# if __name__ == "__main__":
    
#     # 🧪 테스트: 10개만 가져오려면 아래 줄의 주석을 해제하세요.
#     # services_list = get_all_service_list(limit=10)
    
#     # 🚀 전체 실행: 모든 목록을 가져오려면 아래 줄을 사용하세요.
#     services_list = get_all_service_list()
    
#     if services_list:
#         detailed_data = scrape_details_by_clicking_tabs(services_list)
#         save_results(detailed_data)
        
#     print("\n✨ 모든 크롤링 작업이 종료되었습니다.")

# import requests
# import json
# import csv
# import time
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
# from webdriver_manager.chrome import ChromeDriverManager

# def get_all_service_list(limit=None):
#     """
#     복지로 API를 호출하여 서비스 목록을 가져옵니다.
#     limit이 지정되면 해당 개수만큼만 가져오고 중단하여 테스트 속도를 높입니다.
#     """
#     print("✅ [1단계] 복지 서비스 목록 수집을 시작합니다.")
#     list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
#     headers = {
#         'Accept': 'application/json, text/javascript, */*; q=0.01',
#         'Content-Type': 'application/json; charset=UTF-8',
#         'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
#     }
#     payload_template = {
#         "dmSearchParam": {
#             "page": "1", "pageUnit": "100", "onlineYn": "", "searchTerm": "", "tabId": "1", "orderBy": "date",
#             "bkjrLftmCycCd": "", "daesang": "", "period": "", "age": "", "region": "", "jjim": "",
#             "subject": "", "favoriteKeyword": "Y", "sido": "", "gungu": "", "endYn": "N"
#         },
#         "dmScr": {"curScrId": "tbu/app/twat/twata/twataa/TWAT52005M", "befScrId": ""}
#     }
    
#     all_services = []
#     current_page = 1
    
#     while True:
#         if limit and len(all_services) >= limit:
#             break
            
#         print(f"📄 목록 {current_page}페이지를 요청합니다...")
#         payload_template["dmSearchParam"]["page"] = str(current_page)
        
#         try:
#             response = requests.post(list_url, headers=headers, json=payload_template)
#             response.raise_for_status()
#             data = response.json()
            
#             services_on_page = []
#             for i in range(4):
#                 services_on_page.extend(data.get(f"dsServiceList{i}", []))

#             if not services_on_page:
#                 print("✔️ 더 이상 가져올 목록이 없습니다.")
#                 break
            
#             for service in services_on_page:
#                 all_services.append({"id": service.get("WLFARE_INFO_ID"), "name": service.get("WLFARE_INFO_NM")})
            
#             if limit and len(all_services) >= limit:
#                 print(f"✔️ 요청하신 {limit}개 이상의 목록을 수집하여 중단합니다.")
#                 break
            
#             current_page += 1
#             time.sleep(0.5)
            
#         except Exception as e:
#             print(f"❌ 목록 요청 중 오류 발생: {e}")
#             break
    
#     if limit:
#         all_services = all_services[:limit]

#     print(f"🎉 총 {len(all_services)}개의 서비스 목록을 수집했습니다.")
#     return all_services

# def scrape_details_by_clicking_tabs(services):
#     """
#     Selenium으로 각 서비스의 탭을 클릭하며 상세 내용을 스크래핑합니다.
#     """
#     print("\n✅ [2단계] Selenium으로 상세 정보 스크래핑을 시작합니다.")
    
#     options = webdriver.ChromeOptions()
#     options.add_experimental_option('excludeSwitches', ['enable-logging'])
#     options.add_argument('--log-level=3')
#     # options.add_argument("--headless") # 백그라운드 실행을 원하면 이 줄의 주석을 해제하세요.
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("window-size=1920x1080")
    
#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
#     final_results = []
#     total = len(services)
    
#     for i, service in enumerate(services):
#         service_id, service_name = service['id'], service['name']
#         if not service_id: continue
            
#         detail_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}"
#         print(f"({i+1}/{total}) 스크래핑 중: {service_name[:30]}...")
        
#         try:
#             driver.get(detail_url)
            
#             try:
#                 popup_close_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#research_pop .btn-close-pop")))
#                 popup_close_button.click()
#             except TimeoutException:
#                 pass
            
#             tabs_to_scrape = ["지원대상", "서비스 내용"]
#             scraped_content = {"서비스명": service_name}
            
#             for tab_name in tabs_to_scrape:
#                 try:
#                     tab_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, f"//a[@class='cl-text-wrapper' and contains(., '{tab_name}')]")))
#                     tab_button.click()
#                     time.sleep(0.5)
#                     content_container = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.tab-content-inner")))
#                     scraped_content[tab_name] = content_container.text.strip()
#                 except Exception:
#                     scraped_content[tab_name] = "내용을 가져올 수 없음"
            
#             final_results.append(scraped_content)
            
#         except Exception as e:
#             print(f"  - 페이지 처리 중 심각한 오류 발생: {service_name} ({e.__class__.__name__})")
#             final_results.append({"서비스명": service_name, "지원대상": "오류", "서비스 내용": "오류"})
    
#     driver.quit()
#     print("🎉 상세 정보 스크래핑을 완료했습니다.")
#     return final_results

# def save_results(data):
#     """
#     수집된 데이터를 CSV와 JSON 파일로 저장합니다.
#     """
#     if not data:
#         print("⚠️ 저장할 데이터가 없습니다.")
#         return
        
#     print("\n✅ [3단계] 수집된 데이터를 파일로 저장합니다.")
    
#     try:
#         with open('bokjiro_services.csv', 'w', newline='', encoding='utf-8-sig') as f:
#             fieldnames = list(data[0].keys())
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             writer.writerows(data)
#         print("💾 CSV 파일 저장 완료: bokjiro_services.csv")
#     except Exception as e:
#         print(f"❌ CSV 파일 저장 중 오류: {e}")
        
#     try:
#         with open('bokjiro_services.json', 'w', encoding='utf-8') as f:
#             json.dump(data, f, ensure_ascii=False, indent=4)
#         print("💾 JSON 파일 저장 완료: bokjiro_services.json")
#     except Exception as e:
#         print(f"❌ JSON 파일 저장 중 오류: {e}")

# # --- 메인 코드 실행 ---
# if __name__ == "__main__":
    
#     # 🧪 10개만 테스트하려면 아래 줄을 사용하세요.
#     services_list = get_all_service_list(limit=10)
    
#     # 🚀 전체 목록을 가져오려면 위 줄을 주석 처리(#)하고 아래 줄의 주석을 해제하세요.
#     # services_list = get_all_service_list()
    
#     if services_list:
#         detailed_data = scrape_details_by_clicking_tabs(services_list)
#         save_results(detailed_data)
        
#     print("\n✨ 모든 크롤링 작업이 종료되었습니다.")

# import requests
# import json
# import csv
# import time
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
# from webdriver_manager.chrome import ChromeDriverManager


# def get_all_service_list(limit=None):
#     """
#     복지로 API를 호출하여 서비스 목록을 가져옵니다.
#     limit이 지정되면 해당 개수만큼만 가져옵니다.
#     """
#     print("✅ [1단계] 복지 서비스 목록 수집을 시작합니다.")
#     list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
#     headers = {
#         'Accept': 'application/json, text/javascript, */*; q=0.01',
#         'Content-Type': 'application/json; charset=UTF-8',
#         'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
#     }
#     payload_template = {
#         "dmSearchParam": {
#             "page": "1", "pageUnit": "100", "onlineYn": "", "searchTerm": "", "tabId": "1", "orderBy": "date",
#             "bkjrLftmCycCd": "", "daesang": "", "period": "", "age": "", "region": "", "jjim": "",
#             "subject": "", "favoriteKeyword": "Y", "sido": "", "gungu": "", "endYn": "N"
#         },
#         "dmScr": {"curScrId": "tbu/app/twat/twata/twataa/TWAT52005M", "befScrId": ""}
#     }
    
#     all_services = []
#     current_page = 1
    
#     while True:
#         if limit and len(all_services) >= limit:
#             break
            
#         print(f"📄 목록 {current_page}페이지를 요청합니다...")
#         payload_template["dmSearchParam"]["page"] = str(current_page)
        
#         try:
#             response = requests.post(list_url, headers=headers, json=payload_template)
#             response.raise_for_status()
#             data = response.json()
            
#             services_on_page = []
#             for i in range(4):
#                 services_on_page.extend(data.get(f"dsServiceList{i}", []))

#             if not services_on_page:
#                 print("✔️ 더 이상 가져올 목록이 없습니다.")
#                 break
            
#             for service in services_on_page:
#                 all_services.append({
#                     "id": service.get("WLFARE_INFO_ID"),
#                     "name": service.get("WLFARE_INFO_NM")
#                 })
            
#             if limit and len(all_services) >= limit:
#                 print(f"✔️ 요청하신 {limit}개 이상의 목록을 수집하여 중단합니다.")
#                 break
            
#             current_page += 1
#             time.sleep(0.5)
            
#         except Exception as e:
#             print(f"❌ 목록 요청 중 오류 발생: {e}")
#             break
    
#     if limit:
#         all_services = all_services[:limit]

#     print(f"🎉 총 {len(all_services)}개의 서비스 목록을 수집했습니다.")
#     return all_services


# def scrape_details_by_clicking_tabs(services):
#     """
#     Selenium으로 각 서비스의 탭을 클릭하며 상세 내용을 스크래핑합니다.
#     """
#     print("\n✅ [2단계] Selenium으로 상세 정보 스크래핑을 시작합니다.")
    
#     options = webdriver.ChromeOptions()
#     options.add_experimental_option('excludeSwitches', ['enable-logging'])
#     options.add_argument('--log-level=3')
#     options.add_argument("--headless")  # 👉 브라우저 창 숨김 실행
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("window-size=1920x1080")
    
#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
#     final_results = []
#     total = len(services)
    
#     for i, service in enumerate(services):
#         service_id, service_name = service['id'], service['name']
#         if not service_id: 
#             continue
            
#         detail_url = (
#             f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/"
#             f"moveTWAT52011M.do?wlfareInfoId={service_id}&wlfareInfoReldBztpCd=01"
#         )
#         print(f"({i+1}/{total}) 스크래핑 중: {service_name[:30]}...")
        
#         try:
#             driver.get(detail_url)
            
#             # 팝업 닫기 (있을 경우)
#             try:
#                 popup_close_button = WebDriverWait(driver, 3).until(
#                     EC.element_to_be_clickable((By.CSS_SELECTOR, "#research_pop .btn-close-pop"))
#                 )
#                 popup_close_button.click()
#             except TimeoutException:
#                 pass
            
#             # 긁어올 탭 이름들
#             tabs_to_scrape = ["지원대상", "서비스 내용", "필요서류"]
#             scraped_content = {"서비스명": service_name}
            
#             for tab_name in tabs_to_scrape:
#                 try:
#                     # 탭 버튼 클릭
#                     tab_button = WebDriverWait(driver, 15).until(
#                         EC.element_to_be_clickable((
#                             By.XPATH, f"//a[contains(@class, 'cl-text-wrapper')][.//div[text()='{tab_name}']]"
#                         ))
#                     )
#                     tab_button.click()
#                     time.sleep(0.7)
                    
#                     # 본문 컨테이너 찾기
#                     content_container = WebDriverWait(driver, 15).until(
#                         EC.presence_of_element_located((By.CSS_SELECTOR, "div.bokjiConts"))
#                     )
#                     WebDriverWait(driver,15).untill(
#                         lambda d: content_container.text.strip() != ""
#                     )
                    
#                     scraped_content[tab_name] = content_container.text.strip()
#                 except Exception as e:
#                     scraped_content[tab_name] = f"내용을 가져올 수 없음 ({type(e).__name__})"
            
#             final_results.append(scraped_content)
            
#         except Exception as e:
#             print(f"  - 페이지 처리 중 오류 발생: {service_name} ({e.__class__.__name__})")
#             final_results.append({"서비스명": service_name, "지원대상": "오류", "서비스 내용": "오류", "필요서류": "오류"})
    
#     driver.quit()
#     print("🎉 상세 정보 스크래핑을 완료했습니다.")
#     return final_results


# def save_results(data):
#     """
#     수집된 데이터를 CSV와 JSON 파일로 저장합니다.
#     """
#     if not data:
#         print("⚠️ 저장할 데이터가 없습니다.")
#         return
        
#     print("\n✅ [3단계] 수집된 데이터를 파일로 저장합니다.")
    
#     # 필드 순서 고정
#     fieldnames = ["서비스명", "지원대상", "서비스 내용", "필요서류"]
    
#     try:
#         with open('bokjiro_services.csv', 'w', newline='', encoding='utf-8-sig') as f:
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             for row in data:
#                 writer.writerow({key: row.get(key, "") for key in fieldnames})
#         print("💾 CSV 파일 저장 완료: bokjiro_services.csv")
#     except Exception as e:
#         print(f"❌ CSV 파일 저장 중 오류: {e}")
        
#     try:
#         with open('bokjiro_services.json', 'w', encoding='utf-8') as f:
#             json.dump(data, f, ensure_ascii=False, indent=4)
#         print("💾 JSON 파일 저장 완료: bokjiro_services.json")
#     except Exception as e:
#         print(f"❌ JSON 파일 저장 중 오류: {e}")


# # --- 메인 코드 실행 ---
# if __name__ == "__main__":
    
#     # 🧪 테스트용 (10개만 수집)
#     services_list = get_all_service_list(limit=10)
    
#     # 🚀 전체 크롤링하려면 위 줄을 주석처리하고 아래 줄 사용
#     # services_list = get_all_service_list()
    
#     if services_list:
#         detailed_data = scrape_details_by_clicking_tabs(services_list)
#         save_results(detailed_data)
        
#     print("\n✨ 모든 크롤링 작업이 종료되었습니다.")
# import requests
# import json
# import csv
# import time
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
# from webdriver_manager.chrome import ChromeDriverManager

# def get_all_service_list(limit=None):
#     """
#     복지로 API를 호출하여 서비스 목록을 가져옵니다.
#     limit이 지정되면 해당 개수만큼만 가져옵니다.
#     """
#     print("✅ [1단계] 복지 서비스 목록 수집을 시작합니다.")
#     list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
#     headers = {
#         'Accept': 'application/json, text/javascript, */*; q=0.01',
#         'Content-Type': 'application/json; charset=UTF-8',
#         'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
#     }
#     payload_template = {
#         "dmSearchParam": {"page": "1", "pageUnit": "100", "onlineYn": "", "searchTerm": "", "tabId": "1", "orderBy": "date", "bkjrLftmCycCd": "", "daesang": "", "period": "", "age": "", "region": "", "jjim": "", "subject": "", "favoriteKeyword": "Y", "sido": "", "gungu": "", "endYn": "N"},
#         "dmScr": {"curScrId": "tbu/app/twat/twata/twataa/TWAT52005M", "befScrId": ""}
#     }
#     all_services, current_page = [], 1
#     while True:
#         if limit and len(all_services) >= limit: break
#         print(f"📄 목록 {current_page}페이지를 요청합니다...")
#         payload_template["dmSearchParam"]["page"] = str(current_page)
#         try:
#             response = requests.post(list_url, headers=headers, json=payload_template)
#             response.raise_for_status()
#             data = response.json()
#             services_on_page = []
#             for i in range(4): services_on_page.extend(data.get(f"dsServiceList{i}", []))
#             if not services_on_page: print("✔️ 더 이상 가져올 목록이 없습니다."); break
#             for service in services_on_page: all_services.append({"id": service.get("WLFARE_INFO_ID"), "name": service.get("WLFARE_INFO_NM")})
#             if limit and len(all_services) >= limit: print(f"✔️ 요청하신 {limit}개 이상의 목록을 수집하여 중단합니다."); break
#             current_page += 1
#             time.sleep(0.5)
#         except Exception as e: print(f"❌ 목록 요청 중 오류 발생: {e}"); break
#     if limit: all_services = all_services[:limit]
#     print(f"🎉 총 {len(all_services)}개의 서비스 목록을 수집했습니다.")
#     return all_services

# def scrape_details_by_clicking_tabs(services):
#     """
#     Selenium으로 각 서비스의 탭을 클릭하며 상세 내용을 스크래핑하는 최종 안정화 버전입니다.
#     """
#     print("\n✅ [2단계] Selenium으로 상세 정보 스크래핑을 시작합니다.")
#     options = webdriver.ChromeOptions()
#     options.add_experimental_option('excludeSwitches', ['enable-logging'])
#     options.add_argument('--log-level=3')
#     # options.add_argument("--headless") # 창 숨기기
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("window-size=1920x1080")
#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
#     final_results, total = [], len(services)
#     for i, service in enumerate(services):
#         service_id, service_name = service['id'], service['name']
#         if not service_id: continue
#         detail_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}"
#         print(f"({i+1}/{total}) 스크래핑 중: {service_name[:30]}...")
#         try:
#             driver.get(detail_url)
#             try: WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#research_pop .btn-close-pop"))).click()
#             except TimeoutException: pass
            
#             # 스크래핑할 탭 이름 목록
#             tabs_to_scrape = ["지원대상", "서비스 내용", "필요서류"]
#             scraped_content = {"서비스명": service_name}
            
#             for tab_name in tabs_to_scrape:
#                 try:
#                     # 1. 탭 버튼 클릭
#                     tab_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, f"//a[@class='cl-text-wrapper' and contains(., '{tab_name}')]")))
#                     tab_button.click()
                    
#                     # 2. 안정적인 로딩을 위해 1.5초 대기 (가장 중요한 부분)
#                     time.sleep(1.5)
                    
#                     # 3. 정확한 콘텐츠 영역을 지정하여 텍스트 추출
#                     content_container = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.tab-content-inner")))
#                     scraped_content[tab_name] = content_container.text.strip()
#                 except Exception:
#                     # 해당 탭이 없는 경우를 대비
#                     scraped_content[tab_name] = "내용 없음"
            
#             final_results.append(scraped_content)
            
#         except Exception as e:
#             print(f"  - 페이지 처리 중 심각한 오류 발생: {service_name} ({e.__class__.__name__})")
#             final_results.append({"서비스명": service_name, "지원대상": "오류", "서비스 내용": "오류", "필요서류": "오류"})
#     driver.quit()
#     print("🎉 상세 정보 스크래핑을 완료했습니다.")
#     return final_results

# def save_results(data):
#     """
#     수집된 데이터를 CSV와 JSON 파일로 저장합니다.
#     """
#     if not data: print("⚠️ 저장할 데이터가 없습니다."); return
#     print("\n✅ [3단계] 수집된 데이터를 파일로 저장합니다.")
    
#     # CSV 저장 시 필드(열) 순서를 고정하고, 없는 값은 빈칸으로 처리
#     fieldnames = ["서비스명", "지원대상", "서비스 내용", "필요서류"]
#     try:
#         with open('bokjiro_services.csv', 'w', newline='', encoding='utf-8-sig') as f:
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             for row in data:
#                 writer.writerow({key: row.get(key, "") for key in fieldnames})
#         print("💾 CSV 파일 저장 완료: bokjiro_services.csv")
#     except Exception as e: print(f"❌ CSV 파일 저장 중 오류: {e}")
#     try:
#         with open('bokjiro_services.json', 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
#         print("💾 JSON 파일 저장 완료: bokjiro_services.json")
#     except Exception as e: print(f"❌ JSON 파일 저장 중 오류: {e}")

# # --- 메인 코드 실행 ---
# if __name__ == "__main__":
#     services_list = get_all_service_list(limit=10)
#     if services_list:
#         detailed_data = scrape_details_by_clicking_tabs(services_list)
#         save_results(detailed_data)
#     print("\n✨ 모든 크롤링 작업이 종료되었습니다.")

# import requests
# import json
# import csv
# import time
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
# from webdriver_manager.chrome import ChromeDriverManager

# def get_all_service_list(limit=None):
#     """
#     복지로 API를 호출하여 서비스 목록을 가져옵니다.
#     limit이 지정되면 해당 개수만큼만 가져옵니다.
#     """
#     print("✅ [1단계] 복지 서비스 목록 수집을 시작합니다.")
#     list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
#     headers = {
#         'Accept': 'application/json, text/javascript, */*; q=0.01',
#         'Content-Type': 'application/json; charset=UTF-8',
#         'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
#     }
#     payload_template = {
#         "dmSearchParam": {"page": "1", "pageUnit": "100", "onlineYn": "", "searchTerm": "", "tabId": "1", "orderBy": "date", "bkjrLftmCycCd": "", "daesang": "", "period": "", "age": "", "region": "", "jjim": "", "subject": "", "favoriteKeyword": "Y", "sido": "", "gungu": "", "endYn": "N"},
#         "dmScr": {"curScrId": "tbu/app/twat/twata/twataa/TWAT52005M", "befScrId": ""}
#     }
#     all_services, current_page = [], 1
#     while True:
#         if limit and len(all_services) >= limit: break
#         print(f"📄 목록 {current_page}페이지를 요청합니다...")
#         payload_template["dmSearchParam"]["page"] = str(current_page)
#         try:
#             response = requests.post(list_url, headers=headers, json=payload_template)
#             response.raise_for_status()
#             data = response.json()
#             services_on_page = []
#             for i in range(4): services_on_page.extend(data.get(f"dsServiceList{i}", []))
#             if not services_on_page: print("✔️ 더 이상 가져올 목록이 없습니다."); break
#             for service in services_on_page: all_services.append({"id": service.get("WLFARE_INFO_ID"), "name": service.get("WLFARE_INFO_NM")})
#             if limit and len(all_services) >= limit: print(f"✔️ 요청하신 {limit}개 이상의 목록을 수집하여 중단합니다."); break
#             current_page += 1
#             time.sleep(0.5)
#         except Exception as e: print(f"❌ 목록 요청 중 오류 발생: {e}"); break
#     if limit: all_services = all_services[:limit]
#     print(f"🎉 총 {len(all_services)}개의 서비스 목록을 수집했습니다.")
#     return all_services

# def scrape_details_by_clicking_tabs(services):
#     """
#     자바스크립트 클릭을 사용하여 안정성을 극대화한 최종 버전입니다.
#     """
#     print("\n✅ [2단계] Selenium으로 상세 정보 스크래핑을 시작합니다.")
#     options = webdriver.ChromeOptions()
#     options.add_experimental_option('excludeSwitches', ['enable-logging'])
#     options.add_argument('--log-level=3')
#     # options.add_argument("--headless") # 창 숨기기
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("window-size=1920x1080")
#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
#     final_results, total = [], len(services)
#     for i, service in enumerate(services):
#         service_id, service_name = service['id'], service['name']
#         if not service_id: continue
#         detail_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}"
#         print(f"({i+1}/{total}) 스크래핑 중: {service_name[:30]}...")
#         try:
#             driver.get(detail_url)
#             try: WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#research_pop .btn-close-pop"))).click()
#             except TimeoutException: pass
            
#             tabs_to_scrape = ["지원대상", "서비스 내용", "필요서류"]
#             scraped_content = {"서비스명": service_name}
            
#             for tab_name in tabs_to_scrape:
#                 try:
#                     tab_button = WebDriverWait(driver, 5).until(
#                         EC.element_to_be_clickable((
#                             By.XPATH, f"//a[@class='cl-text-wrapper' and contains(., '{tab_name}')]"
#                             ))
#                         )
#                     tab_button.click()
#                     # 컨테이너 여러 개 중 마지막 것 선택
#                     containers = WebDriverWait(driver, 15). untill(
#                         EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.bokjiConts"))
#                     )    
#                     content_container = containers[-1]
                    
#                     WebDriverWait(driver, 15).untill(
#                         lambda d: content_container.text.strip()!=""
#                     )
#                     scraped_content[tab_name] = content_container.text.strip()
#                 except Exception:
#                     scraped_content[tab_name] = "내용 없음"
            
#             final_results.append(scraped_content)
            
#         except Exception as e:
#             print(f"  - 페이지 처리 중 심각한 오류 발생: {service_name} ({e.__class__.__name__})")
#             final_results.append({"서비스명": service_name, "지원대상": "오류", "서비스 내용": "오류", "필요서류": "오류"})
#     driver.quit()
#     print("🎉 상세 정보 스크래핑을 완료했습니다.")
#     return final_results

# def save_results(data):
#     """
#     수집된 데이터를 CSV와 JSON 파일로 저장합니다.
#     """
#     if not data: print("⚠️ 저장할 데이터가 없습니다."); return
#     print("\n✅ [3단계] 수집된 데이터를 파일로 저장합니다.")
#     fieldnames = ["서비스명", "지원대상", "서비스 내용", "필요서류"]
#     try:
#         with open('bokjiro_services.csv', 'w', newline='', encoding='utf-8-sig') as f:
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             for row in data:
#                 writer.writerow({key: row.get(key, "") for key in fieldnames})
#         print("💾 CSV 파일 저장 완료: bokjiro_services.csv")
#     except Exception as e: print(f"❌ CSV 파일 저장 중 오류: {e}")
#     try:
#         with open('bokjiro_services.json', 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
#         print("💾 JSON 파일 저장 완료: bokjiro_services.json")
#     except Exception as e: print(f"❌ JSON 파일 저장 중 오류: {e}")

# # --- 메인 코드 실행 ---
# if __name__ == "__main__":
#     services_list = get_all_service_list(limit=10) # 10개만 테스트
#     if services_list:
#         detailed_data = scrape_details_by_clicking_tabs(services_list)
#         save_results(detailed_data)
#     print("\n✨ 모든 크롤링 작업이 종료되었습니다.")

# import requests
# import json
# import csv
# import time
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
# from webdriver_manager.chrome import ChromeDriverManager


# def get_all_service_list(limit=None):
#     """
#     복지로 API를 호출하여 서비스 목록을 가져옵니다.
#     limit이 지정되면 해당 개수만큼만 가져옵니다.
#     """
#     print("✅ [1단계] 복지 서비스 목록 수집 시작")
#     list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
#     headers = {
#         'Accept': 'application/json, text/javascript, */*; q=0.01',
#         'Content-Type': 'application/json; charset=UTF-8',
#         'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
#     }
#     payload_template = {
#         "dmSearchParam": {
#             "page": "1", "pageUnit": "100", "onlineYn": "", "searchTerm": "", "tabId": "1", "orderBy": "date",
#             "bkjrLftmCycCd": "", "daesang": "", "period": "", "age": "", "region": "", "jjim": "",
#             "subject": "", "favoriteKeyword": "Y", "sido": "", "gungu": "", "endYn": "N"
#         },
#         "dmScr": {"curScrId": "tbu/app/twat/twata/twataa/TWAT52005M", "befScrId": ""}
#     }
    
#     all_services = []
#     current_page = 1
    
#     while True:
#         if limit and len(all_services) >= limit:
#             break
            
#         print(f"📄 목록 {current_page}페이지 요청")
#         payload_template["dmSearchParam"]["page"] = str(current_page)
        
#         try:
#             response = requests.post(list_url, headers=headers, json=payload_template)
#             response.raise_for_status()
#             data = response.json()
            
#             services_on_page = []
#             for i in range(4):
#                 services_on_page.extend(data.get(f"dsServiceList{i}", []))

#             if not services_on_page:
#                 print("✔️ 더 이상 가져올 목록 없음")
#                 break
            
#             for service in services_on_page:
#                 all_services.append({
#                     "id": service.get("WLFARE_INFO_ID"),
#                     "name": service.get("WLFARE_INFO_NM")
#                 })
            
#             if limit and len(all_services) >= limit:
#                 print(f"✔️ {limit}개 수집 완료")
#                 break
            
#             current_page += 1
#             time.sleep(0.5)
            
#         except Exception as e:
#             print(f"❌ 목록 요청 오류: {e}")
#             break
    
#     if limit:
#         all_services = all_services[:limit]

#     print(f"🎉 총 {len(all_services)}개 서비스 수집 완료")
#     return all_services


# def scrape_details_by_clicking_tabs(services):
#     """
#     Selenium으로 각 서비스의 '지원대상', '서비스 내용' 탭을 스크래핑합니다.
#     """
#     print("\n✅ [2단계] 상세 정보 스크래핑 시작")
    
#     options = webdriver.ChromeOptions()
#     options.add_experimental_option('excludeSwitches', ['enable-logging'])
#     options.add_argument('--log-level=3')
#     options.add_argument("--headless")  # 👉 백그라운드 실행
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("window-size=1920x1080")
    
#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
#     final_results = []
#     total = len(services)
    
#     # 탭별 선택자
#     tab_selectors = {
#         "지원대상": "div.bokjiServiceView div.bokjiConts",
#         "서비스 내용": "div.bokjiConts"
#     }
    
#     for i, service in enumerate(services):
#         service_id, service_name = service['id'], service['name']
#         if not service_id: 
#             continue
            
#         detail_url = (
#             f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/"
#             f"moveTWAT52011M.do?wlfareInfoId={service_id}&wlfareInfoReldBztpCd=01"
#         )
#         print(f"({i+1}/{total}) {service_name[:30]} 스크래핑 중...")
        
#         try:
#             driver.get(detail_url)
            
#             # 팝업 닫기 (있을 경우)
#             try:
#                 popup_close_button = WebDriverWait(driver, 3).until(
#                     EC.element_to_be_clickable((By.CSS_SELECTOR, "#research_pop .btn-close-pop"))
#                 )
#                 popup_close_button.click()
#             except TimeoutException:
#                 pass
            
#             # 실제 수집할 탭들
#             tabs_to_scrape = ["지원대상", "서비스 내용"]
#             scraped_content = {"서비스명": service_name}
            
#             for tab_name in tabs_to_scrape:
#                 try:
#                     # 탭 버튼 클릭 (title 속성 활용)
#                     tab_button = WebDriverWait(driver, 10).until(
#                         EC.element_to_be_clickable((By.XPATH, f"//a[contains(@title, '{tab_name}')]"))
#                     )
#                     tab_button.click()

#                     selector = tab_selectors.get(tab_name, "div.bokjiConts")

#                     # 본문 컨테이너 대기
#                     content_container = WebDriverWait(driver, 15).until(
#                         EC.presence_of_element_located((By.CSS_SELECTOR, selector))
#                     )

#                     # 텍스트 로딩 완료까지 대기
#                     WebDriverWait(driver, 15).until(
#                         lambda d: content_container.text.strip() != ""
#                     )

#                     scraped_content[tab_name] = content_container.text.strip()

#                 except Exception as e:
#                     scraped_content[tab_name] = f"내용을 가져올 수 없음 ({type(e).__name__})"
            
#             final_results.append(scraped_content)
            
#         except Exception as e:
#             print(f"  - 페이지 처리 오류: {service_name} ({e.__class__.__name__})")
#             final_results.append({"서비스명": service_name, "지원대상": "오류", "서비스 내용": "오류"})
    
#     driver.quit()
#     print("🎉 상세 정보 스크래핑 완료")
#     return final_results


# def save_results(data):
#     """
#     수집된 데이터를 CSV와 JSON 파일로 저장합니다.
#     """
#     if not data:
#         print("⚠️ 저장할 데이터가 없습니다.")
#         return
        
#     print("\n✅ [3단계] 파일 저장 시작")
    
#     # 필드 순서 고정
#     fieldnames = ["서비스명", "지원대상", "서비스 내용"]
    
#     try:
#         with open('bokjiro_services.csv', 'w', newline='', encoding='utf-8-sig') as f:
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             for row in data:
#                 writer.writerow({key: row.get(key, "") for key in fieldnames})
#         print("💾 CSV 저장 완료: bokjiro_services.csv")
#     except Exception as e:
#         print(f"❌ CSV 저장 오류: {e}")
        
#     try:
#         with open('bokjiro_services.json', 'w', encoding='utf-8') as f:
#             json.dump(data, f, ensure_ascii=False, indent=4)
#         print("💾 JSON 저장 완료: bokjiro_services.json")
#     except Exception as e:
#         print(f"❌ JSON 저장 오류: {e}")


# # --- 메인 실행 ---
# if __name__ == "__main__":
    
#     # 🧪 테스트용 (10개만 수집)
#     services_list = get_all_service_list(limit=10)
    
#     # 🚀 전체 크롤링 하려면 위 줄 주석 처리하고 아래 사용
#     # services_list = get_all_service_list()
    
#     if services_list:
#         detailed_data = scrape_details_by_clicking_tabs(services_list)
#         save_results(detailed_data)
        
#     print("\n✨ 모든 작업 종료")

import requests
import json
import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


def get_all_service_list(limit=None):
    """
    복지로 API를 호출하여 서비스 목록을 가져옵니다.
    limit이 지정되면 해당 개수만큼만 가져오고 중단합니다.
    """
    print("✅ [1단계] 복지 서비스 목록 수집 시작")
    list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/json; charset=UTF-8",
        "Referer": "https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    }
    payload_template = {
        "dmSearchParam": {
            "page": "1",
            "pageUnit": "100",
            "onlineYn": "",
            "searchTerm": "",
            "tabId": "1",
            "orderBy": "date",
            "bkjrLftmCycCd": "",
            "daesang": "",
            "period": "",
            "age": "",
            "region": "",
            "jjim": "",
            "subject": "",
            "favoriteKeyword": "Y",
            "sido": "",
            "gungu": "",
            "endYn": "N",
        },
        "dmScr": {
            "curScrId": "tbu/app/twat/twata/twataa/TWAT52005M",
            "befScrId": "",
        },
    }

    all_services = []
    current_page = 1

    while True:
        if limit and len(all_services) >= limit:
            break

        print(f"📄 목록 {current_page}페이지 요청 중...")
        payload_template["dmSearchParam"]["page"] = str(current_page)

        try:
            response = requests.post(list_url, headers=headers, json=payload_template)
            response.raise_for_status()
            data = response.json()

            services_on_page = []
            for i in range(4):
                services_on_page.extend(data.get(f"dsServiceList{i}", []))

            if not services_on_page:
                print("✔️ 더 이상 가져올 목록 없음")
                break

            for service in services_on_page:
                all_services.append(
                    {
                        "id": service.get("WLFARE_INFO_ID"),
                        "name": service.get("WLFARE_INFO_NM"),
                    }
                )

            if limit and len(all_services) >= limit:
                print(f"✔️ {limit}개 수집 완료, 중단")
                break

            current_page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ 목록 요청 오류: {e}")
            break

    if limit:
        all_services = all_services[:limit]

    print(f"🎉 총 {len(all_services)}개 서비스 목록 수집")
    return all_services


def scrape_details_by_clicking_tabs(services):
    """
    Selenium으로 각 서비스 페이지에서 '지원대상', '서비스 내용' 탭(또는 본문)을 스크래핑
    """
    print("\n✅ [2단계] 상세 정보 스크래핑 시작")

    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920x1080")
    # options.add_argument("--headless")  # 백그라운드 실행하려면 주석 해제

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    final_results = []
    total = len(services)

    # 탭 본문 CSS 선택자 정의
    tab_selectors = {
        "지원대상": "div.bokjiServiceView div.bokjiConts",
        "서비스 내용": "div.bokjiConts",
    }

    for i, service in enumerate(services):
        service_id, service_name = service["id"], service["name"]
        if not service_id:
            continue

        detail_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}"
        print(f"({i+1}/{total}) {service_name[:30]}...")

        scraped_content = {"서비스명": service_name}

        try:
            driver.get(detail_url)

            # 팝업 닫기 시도
            try:
                popup_close_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#research_pop .btn-close-pop"))
                )
                popup_close_button.click()
            except TimeoutException:
                pass

            # 실제 존재하는 탭만 처리
            for tab_name in ["지원대상", "서비스 내용"]:
                try:
                    # 1️⃣ 탭 버튼 확인
                    tab_buttons = driver.find_elements(By.XPATH, f"//a[contains(@title, '{tab_name}')]")

                    if tab_buttons:
                        tab_buttons[0].click()
                        selector = tab_selectors.get(tab_name, "div.bokjiConts")
                    else:
                        # 탭이 없으면 본문 컨테이너 바로 사용
                        selector = "div.bokjiConts"

                    # 2️⃣ 본문 컨테이너 대기
                    content_container = WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )

                    WebDriverWait(driver, 8).until(
                        lambda d: content_container.text.strip() != ""
                    )

                    scraped_content[tab_name] = content_container.text.strip()

                except Exception as e:
                    scraped_content[tab_name] = f"내용을 가져올 수 없음 ({type(e).__name__})"

            final_results.append(scraped_content)

        except Exception as e:
            print(f"  - 페이지 처리 오류: {service_name} ({e})")
            final_results.append(
                {"서비스명": service_name, "지원대상": "오류", "서비스 내용": "오류"}
            )

    driver.quit()
    print("🎉 상세 정보 스크래핑 완료")
    return final_results


def save_results(data):
    """
    CSV와 JSON 파일로 저장
    """
    if not data:
        print("⚠️ 저장할 데이터 없음")
        return

    print("\n✅ [3단계] 파일 저장 시작")

    try:
        with open("bokjiro_services.csv", "w", newline="", encoding="utf-8-sig") as f:
            fieldnames = list(data[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print("💾 CSV 저장 완료: bokjiro_services.csv")
    except Exception as e:
        print(f"❌ CSV 저장 오류: {e}")

    try:
        with open("bokjiro_services.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("💾 JSON 저장 완료: bokjiro_services.json")
    except Exception as e:
        print(f"❌ JSON 저장 오류: {e}")


# --- 메인 실행 ---
if __name__ == "__main__":
    services_list = get_all_service_list(limit=10)  # 테스트 시 limit 사용
    if services_list:
        detailed_data = scrape_details_by_clicking_tabs(services_list)
        save_results(detailed_data)

    print("\n✨ 모든 크롤링 작업 종료")

