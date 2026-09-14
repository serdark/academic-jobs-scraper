import os
import time
import requests
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

VCD_KEYWORDS = ["görsel", "görsel iletişim", "iletişim tasarım", "iletişim ve tasarımı", "iletişim tasarımı", "grafik"]
GASTRO_KEYWORDS = ["gastronomi", "mutfak sanatları"]

def turkish_lower(text):
    return text.replace("İ", "i").replace("I", "ı").lower()

def extract_university_name(title):
    t = title.replace("Rektörlüğünden", "").replace("Rektörlüğü", "").replace("Başkanlığından", "").replace("Başkanlığı", "")
    t = t.replace("Öğretim Üyesi", "").replace("Öğretim Elemanı", "")
    t = t.replace("Öğretim Görevlisi", "").replace("Araştırma Görevlisi", "")
    t = t.replace("Akademik Personel", "").replace("Alım İlanı", "")
    t = t.replace("Alımı İlanı", "").replace("Alımı", "")
    t = t.replace("İlanı", "").replace("İlan", "").replace("Düzeltme", "")
    
    t = t.replace("Üniversitesi", "University").replace("Üniversite", "University")
    t = t.replace("Enstitüsü", "Institute").replace("Enstitü", "Institute")
    t = t.replace("Vakfı", "Foundation")
    
    t = re.sub(r'\(.*?\)', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})

def check_nisantasi(driver):
    seen_file = "seen_nisantasi.json"
    seen_history = json.load(open(seen_file)) if os.path.exists(seen_file) else []
    new_found = False
    
    try:
        driver.get("https://www.nisantasi.edu.tr/duyurular")
        time.sleep(3)
        cards = driver.find_elements(By.CLASS_NAME, "nev-ann-card")
        for card in cards:
            title = card.find_element(By.CLASS_NAME, "nev-ann-title").text.strip()
            href = card.find_element(By.TAG_NAME, "a").get_attribute("href")
            
            if href and href not in seen_history:
                msg = f"📢 <b>Yeni Nişantaşı Duyurusu</b>\n\n"
                msg += f"{title}\n\n"
                msg += f"<a href='{href}'>Görüntüle</a>"
                send_telegram_message(msg)
                seen_history.append(href)
                new_found = True
                time.sleep(1)
    except Exception as e:
        pass
        
    if new_found or not os.path.exists(seen_file):
        with open(seen_file, "w") as f:
            json.dump(seen_history, f)

def check_academic_jobs(driver):
    seen_file = "seen_jobs.json"
    seen_history = json.load(open(seen_file)) if os.path.exists(seen_file) else []
    new_found = False
    
    all_links = set()
    
    for page in [0, 1, 2, 3]:
        driver.get(f"https://www.ilan.gov.tr/ilan/kategori/73/akademik-personel-alimlari?currentPage={page}&field=publish_time&order=desc")
        time.sleep(10)
        
        elements = driver.find_elements(By.TAG_NAME, "a")
        for el in elements:
            try:
                href = el.get_attribute('href')
                if href and "ilan.gov.tr/ilan/" in href and "/kategori/" not in href and "/tum-ilanlar" not in href:
                    if href not in seen_history:
                        all_links.add(href)
            except: continue
            
    for url in list(all_links):
        try:
            driver.get(url)
            time.sleep(3) 
            
            body_text = turkish_lower(driver.find_element(By.TAG_NAME, "body").text)
            
            if "araştırma görevlisi" not in body_text:
                seen_history.append(url)
                new_found = True
                continue
            
            is_vcd = any(kw in body_text for kw in VCD_KEYWORDS)
            is_gastro = any(kw in body_text for kw in GASTRO_KEYWORDS)
            
            if is_vcd or is_gastro:
                page_title = driver.title.split("-")[0].strip() if driver.title else ""
                uni_name = extract_university_name(page_title)
                
                fields = []
                if is_vcd: fields.append("VCD")
                if is_gastro: fields.append("Gastronomi")
                fields_str = ", ".join(fields)
                
                msg = f"<b>{uni_name}</b>\n\n"
                msg += f"Research Assistant\n"
                msg += f"{fields_str}\n\n"
                msg += f"<a href='{url}'>View Details</a>"
                
                send_telegram_message(msg)
                time.sleep(1)
                
            seen_history.append(url)
            new_found = True
        except Exception as e:
            pass
            
    if new_found or not os.path.exists(seen_file):
        with open(seen_file, "w") as f:
            json.dump(seen_history, f)

def main():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    
    check_nisantasi(driver)
    check_academic_jobs(driver)
    
    driver.quit()

if __name__ == "__main__":
    main()
