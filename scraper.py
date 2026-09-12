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

KEYWORDS = [
    "görsel", "görsel iletişim", "iletişim tasarım", "iletişim ve tasarımı", 
    "iletişim tasarımı", "grafik", "gastronomi", "mutfak sanatları"
]

def turkish_lower(text):
    return text.replace("İ", "i").replace("I", "ı").lower()

def extract_university_name(title):
    # Gereksiz tüm Türkçe ekleri ve unvanları temizleyip sadece Üniversite adını İngilizce bırakır
    t = title.replace("Rektörlüğünden", "").replace("Rektörlüğü", "").replace("Başkanlığından", "").replace("Başkanlığı", "")
    t = t.replace("Öğretim Üyesi", "").replace("Öğretim Elemanı", "")
    t = t.replace("Öğretim Görevlisi", "").replace("Araştırma Görevlisi", "")
    t = t.replace("Akademik Personel", "").replace("Alım İlanı", "")
    t = t.replace("Alımı İlanı", "").replace("Alımı", "")
    t = t.replace("İlanı", "").replace("İlan", "").replace("Düzeltme", "")
    
    t = t.replace("Üniversitesi", "University").replace("Üniversite", "University")
    t = t.replace("Enstitüsü", "Institute").replace("Enstitü", "Institute")
    t = t.replace("Vakfı", "Foundation")
    
    t = re.sub(r'\(.*?\)', '', t) # Parantez içlerini temizle
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})

def main():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    
    seen_file = "seen_jobs.json"
    seen_history = json.load(open(seen_file)) if os.path.exists(seen_file) else []
    
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
            
            # 1. KURAL: Kesinlikle Araştırma Görevlisi kelimesi geçmeli
            if "araştırma görevlisi" not in body_text:
                seen_history.append(url)
                continue
            
            # 2. KURAL: Sizin belirlediğiniz anahtar kelimelerden biri geçmeli
            matched_kws = [kw for kw in KEYWORDS if kw in body_text]
            
            if matched_kws:
                page_title = driver.title.split("-")[0].strip() if driver.title else ""
                uni_name = extract_university_name(page_title)
                
                # Hangi kelimeler bulunduysa yan yana ve baş harfi büyük yazılır
                fields = ", ".join(matched_kws).title()
                
                msg = f"<b>{uni_name}</b>\n\n"
                msg += f"<b>Position:</b> Research Assistant\n"
                msg += f"<b>Field:</b> {fields}\n\n"
                msg += f"<a href='{url}'>View Details</a>"
                
                send_telegram_message(msg)
                time.sleep(1)
                
            seen_history.append(url)
        except Exception as e:
            pass
            
    driver.quit()
    
    with open(seen_file, "w") as f:
        json.dump(seen_history, f)

if __name__ == "__main__":
    main()
