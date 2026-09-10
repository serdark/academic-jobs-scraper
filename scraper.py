import os
import time
import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# "üniversitesi" kelimesini de test için ekledim.
KEYWORDS = [
    "görsel", "görsel iletişim", "iletişim tasarım", "iletişim ve tasarımı", 
    "iletişim tasarımı", "grafik", "gastronomi", "mutfak sanatları", "üniversitesi"
]

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
            # Link ayrıştırma hatasını düzelttiğim satır:
            if href and "ilan.gov.tr/ilan/" in href and "/kategori/" not in href and "/tum-ilanlar" not in href and text:
                if any(kw in text for kw in KEYWORDS):
                    unique_jobs[href] = link.text.strip()
        except: continue
    driver.quit()
    
    seen_file = "seen_jobs.json"
    seen_history = json.load(open(seen_file)) if os.path.exists(seen_file) else []
    
    new_jobs = [(url, title) for url, title in unique_jobs.items() if url not in seen_history]
    
    for url, title in new_jobs:
        send_telegram_message(f"🔔 <b>YENİ İLAN!</b>\n\n<b>{title}</b>\n\n<a href='{url}'>İlanı Görüntüle</a>")
        seen_history.append(url)
        time.sleep(1)
        
    with open(seen_file, "w") as f:
        json.dump(seen_history, f)

if __name__ == "__main__":
    main()
