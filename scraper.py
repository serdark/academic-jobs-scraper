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

def translate_title(title):
    # Gereksiz resmi kelimeleri siler
    t = title.replace("Rektörlüğünden", "").replace("Rektörlüğü", "")
    t = t.replace("Başkanlığından", "").replace("Başkanlığı", "")
    
    # Kurum isimlerini İngilizceye çevirir
    t = t.replace("Üniversitesi", "University").replace("Üniversite", "University")
    t = t.replace("Enstitüsü", "Institute").replace("Enstitü", "Institute")
    t = t.replace("Vakfı", "Foundation")
    
    # Unvanları ve Ekleri İngilizceye çevirir
    t = t.replace("Öğretim Üyesi", "Faculty Member")
    t = t.replace("Öğretim Elemanı", "Academic Staff")
    t = t.replace("Öğretim Görevlisi", "Lecturer")
    t = t.replace("Araştırma Görevlisi", "Research Assistant")
    t = t.replace("Akademik Personel", "Academic Staff")
    t = t.replace("Alım İlanı", "Recruitment")
    t = t.replace("Alımı İlanı", "Recruitment")
    t = t.replace("Alımı", "Recruitment")
    t = t.replace("İlanı", "Announcement")
    t = t.replace("İlan", "Announcement")
    t = t.replace("Düzeltme", "Correction")
    
    # Fazladan boşlukları temizler
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
    driver = webdriver.Chrome(options=options)
    
    driver.get("https://www.ilan.gov.tr/ilan/kategori/73/akademik-personel-alimlari?currentPage=0&field=publish_time&order=desc")
    time.sleep(10)
    
    links = driver.find_elements(By.TAG_NAME, "a")
    unique_jobs = {}
    
    for link in links:
        try:
            href = link.get_attribute('href')
            text = link.text.strip().lower()
            if href and "ilan.gov.tr/ilan/" in href and "/kategori/" not in href and "/tum-ilanlar" not in href and text:
                if any(kw in text for kw in KEYWORDS):
                    unique_jobs[href] = link.text.strip()
        except: continue
    driver.quit()
    
    seen_file = "seen_jobs.json"
    seen_history = json.load(open(seen_file)) if os.path.exists(seen_file) else []
    
    new_jobs = [(url, title) for url, title in unique_jobs.items() if url not in seen_history]
    
    for url, title in new_jobs:
        english_title = translate_title(title)
        send_telegram_message(f"<b>{english_title}</b>\n\n<a href='{url}'>View Details</a>")
        seen_history.append(url)
        time.sleep(1)
        
    with open(seen_file, "w") as f:
        json.dump(seen_history, f)

if __name__ == "__main__":
    main()
