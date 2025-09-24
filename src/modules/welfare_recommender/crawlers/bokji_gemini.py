import requests
import json
import csv
import time
import datetime  # 날짜와 시간을 사용하기 위해 추가
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
    limit이 지정되면 해당 개수만큼만 가져옵니다.
    """
    print("✅ [1단계] 복지 서비스 목록 수집을 시작합니다.")
    list_url = "https://www.bokjiro.go.kr/ssis-tbu/TWAT52005M/twataa/wlfareInfo/selectWlfareInfo.do"
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/json; charset=UTF-8',
        'Referer': 'https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52005M.do',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    }
    payload_template = {
        "dmSearchParam": {"page": "1", "pageUnit": "100", "onlineYn": "", "searchTerm": "", "tabId": "1", "orderBy": "date", "bkjrLftmCycCd": "", "daesang": "", "period": "", "age": "", "region": "", "jjim": "", "subject": "", "favoriteKeyword": "Y", "sido": "", "gungu": "", "endYn": "N"},
        "dmScr": {"curScrId": "tbu/app/twat/twata/twataa/TWAT52005M", "befScrId": ""}
    }
    all_services, current_page = [], 1
    while True:
        if limit and len(all_services) >= limit: break
        print(f"📄 목록 {current_page}페이지를 요청합니다...")
        payload_template["dmSearchParam"]["page"] = str(current_page)
        try:
            response = requests.post(list_url, headers=headers, json=payload_template)
            response.raise_for_status()
            data = response.json()
            services_on_page = []
            for i in range(4): services_on_page.extend(data.get(f"dsServiceList{i}", []))
            if not services_on_page: print("✔️ 더 이상 가져올 목록이 없습니다."); break
            for service in services_on_page: all_services.append({"id": service.get("WLFARE_INFO_ID"), "name": service.get("WLFARE_INFO_NM")})
            if limit and len(all_services) >= limit: print(f"✔️ 요청하신 {limit}개 이상의 목록을 수집하여 중단합니다."); break
            current_page += 1
            time.sleep(0.5)
        except Exception as e: print(f"❌ 목록 요청 중 오류 발생: {e}"); break
    if limit: all_services = all_services[:limit]
    print(f"🎉 총 {len(all_services)}개의 서비스 목록을 수집했습니다.")
    return all_services

def scrape_details_by_clicking_tabs(services):
    """
    자바스크립트 클릭과 안정적인 대기 방식을 사용하여 상세 내용을 스크래핑합니다.
    """
    print("\n✅ [2단계] Selenium으로 상세 정보 스크래핑을 시작합니다.")
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('--log-level=3')
    # options.add_argument("--headless") # 창을 숨기려면 이 줄의 주석을 해제하세요.
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920x1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    final_results, total = [], len(services)
    for i, service in enumerate(services):
        service_id, service_name = service['id'], service['name']
        if not service_id: continue
        detail_url = f"https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={service_id}"
        print(f"({i+1}/{total}) 스크래핑 중: {service_name[:30]}...")
        try:
            driver.get(detail_url)
            try: WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#research_pop .btn-close-pop"))).click()
            except TimeoutException: pass
            
            tabs_to_scrape = ["지원대상", "서비스 내용", "필요서류"]
            scraped_content = {"서비스명": service_name}
            
            for tab_name in tabs_to_scrape:
                try:
                    tab_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, f"//a[@class='cl-text-wrapper' and contains(., '{tab_name}')]")))
                    driver.execute_script("arguments[0].click();", tab_button)
                    time.sleep(1.5)
                    content_container = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.tab-content-inner")))
                    scraped_content[tab_name] = content_container.text.strip()
                except Exception:
                    scraped_content[tab_name] = "내용 없음"
            
            final_results.append(scraped_content)
            
        except Exception as e:
            print(f"  - 페이지 처리 중 심각한 오류 발생: {service_name} ({e.__class__.__name__})")
            final_results.append({"서비스명": service_name, "지원대상": "오류", "서비스 내용": "오류", "필요서류": "오류"})
    driver.quit()
    print("🎉 상세 정보 스크래핑을 완료했습니다.")
    return final_results

def save_results(data, timestamp):
    """
    수집된 데이터를 CSV와 JSON 파일로 저장합니다.
    파일명에 타임스탬프를 추가하여 사본으로 저장합니다.
    """
    if not data: 
        print("⚠️ 저장할 데이터가 없습니다.")
        return
        
    print("\n✅ [3단계] 수집된 데이터를 파일로 저장합니다.")
    
    # --- ✨ 수정된 부분 시작 ✨ ---
    base_filename = "bokjiro_services"
    csv_filename = f"{base_filename}(사본_{timestamp}).csv"
    json_filename = f"{base_filename}(사본_{timestamp}).json"
    # --- ✨ 수정된 부분 끝 ✨ ---
    
    fieldnames = ["서비스명", "지원대상", "서비스 내용", "필요서류"]
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow({key: row.get(key, "") for key in fieldnames})
        print(f"💾 CSV 파일 저장 완료: {csv_filename}")
    except Exception as e: 
        print(f"❌ CSV 파일 저장 중 오류: {e}")
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"💾 JSON 파일 저장 완료: {json_filename}")
    except Exception as e: 
        print(f"❌ JSON 파일 저장 중 오류: {e}")

# --- 메인 코드 실행 ---
if __name__ == "__main__":
    
    # 🧪 테스트: 10개만 가져오려면 아래 줄을 사용하세요.
    services_list = get_all_service_list(limit=10)
    
    # 🚀 전체 실행: 모든 목록을 가져오려면 위 줄을 주석 처리(#)하고 아래 줄의 주석을 해제하세요.
    # services_list = get_all_service_list()
    
    if services_list:
        detailed_data = scrape_details_by_clicking_tabs(services_list)
        
        # --- ✨ 수정된 부분 시작 ✨ ---
        # 파일명에 사용할 현재 시간 생성 (예: 20250920_2203)
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M")
        
        # save_results 함수에 timestamp 전달
        save_results(detailed_data, timestamp_str)
        # --- ✨ 수정된 부분 끝 ✨ ---
        
    print("\n✨ 모든 크롤링 작업이 종료되었습니다.")