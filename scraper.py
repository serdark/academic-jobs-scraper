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

def translate_title(title):
    t = title.replace("Rektörlüğünden", "").replace("Rektörlüğü", "").replace("Başkanlığından", "").replace("Başkanlığı", "")
    t = t.replace("Üniversitesi", "University").replace("Üniversite", "University")
    t = t.replace("Enstitüsü", "Institute").replace("Enstitü", "Institute")
    t = t.replace("Vakfı", "Foundation")
    t = t.replace("Öğretim Üyesi", "Faculty Member").replace("Öğretim Elemanı", "Academic Staff")
    t = t.replace("Öğretim Görevlisi", "Lecturer").replace("Araştırma Görevlisi", "Research Assistant")
    t = t.replace("Akademik Personel", "Academic Staff").replace("Alım İlanı", "Recruitment")
    t = t.replace("Alımı İlanı", "Recruitment").replace("Alımı", "Recruitment")
    t = t.replace("İlanı", "Announcement").replace("İlan", "Announcement").replace("Düzeltme", "Correction")
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
    
    seen_file = "seen_jobs.json"
    seen_history = json.load(open(seen_file)) if os.path.exists(seen_file) else []
    
    all_links = {}
    
    # Sadece 1. ve 2. sayfadaki linkleri topluyoruz
    for page in [0, 1]:
        driver.get(f"https://www.ilan.gov.tr/ilan/kategori/73/akademik-personel-alimlari?currentPage={page}&field=publish_time&order=desc")
        time.sleep(10)
        
        elements = driver.find_elements(By.TAG_NAME, "a")
        for el in elements:
            try:
                href = el.get_attribute('href')
                text = el.text.strip()
                if href and "ilan.gov.tr/ilan/" in href and "/kategori/" not in href and "/tum-ilanlar" not in href and text:
                    # Sadece daha önce hiç tıklamadığımız YENİ linkleri listeye al
                    if href not in seen_history:
                        all_links[href] = text
            except: continue
            
    # Topladığımız tüm yeni ilanların içine tek tek girip metni okuyoruz
    for url, title in all_links.items():
        try:
            driver.get(url)
            time.sleep(3) # İlan detayının yüklenmesini bekle
            body_text = turkish_lower(driver.find_element(By.TAG_NAME, "body").text)
            
            # Eğer ilanın detay metninde aradığımız bölüm/kelime varsa mesaj at!
            if any(kw in body_text for kw in KEYWORDS):
                english_title = translate_title(title)
                send_telegram_message(f"<b>{english_title}</b>\n\n<a href='{url}'>View Details</a>")
                time.sleep(1)
                
            # Aradığımız kelime yoksa bile (veya varsa da) ilanı 'okundu' olarak kaydet ki bir dahaki sefer içine girmesin
            seen_history.append(url)
        except Exception as e:
            pass
            
    driver.quit()
    
    with open(seen_file, "w") as f:
        json.dump(seen_history, f)

if __name__ == "__main__":
    main()
