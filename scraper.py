import os
import time
import requests
import json
import re
from datetime import datetime
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

def check_yeditepe(driver):
    now = datetime.utcnow()
    start_time = datetime(2026, 9, 18, 5, 0)
    end_time = datetime(2026, 9, 18, 20, 59)
    
    if not (start_time <= now <= end_time):
        return
        
    seen_file = "seen_yeditepe.json"
    seen_history = json.load(open(seen_file)) if os.path.exists(seen_file) else []
    new_found = False
    
    YEDITEPE_KEYWORDS = ["dijital oyun tasarımı", "nihai değerlendirme", "araştırma görevlisi"]
    
    try:
        driver.get("https://www.yeditepe.edu.tr/tr/duyuru")
        time.sleep(3)
        links = driver.find_elements(By.TAG_NAME, "a")
        
        all_hrefs = set()
        for link in links:
            try:
                href = link.get_attribute("href")
                if href and "/tr/duyuru/" in href:
                    all_hrefs.add(href)
            except: continue
                
        for href in all_hrefs:
            if href not in seen_history:
                driver.get(href)
                time.sleep(2)
                page_title = driver.title.split("|")[0].split("-")[0].strip() if driver.title else "Yeditepe Duyurusu"
                
                body_text = turkish_lower(driver.find_element(By.TAG_NAME, "body").text)
                title_lower = turkish_lower(page_title)
                
                if any(kw in title_lower or kw in body_text for kw in YEDITEPE_KEYWORDS):
                    msg = f"📢 <b>Yeditepe Duyurusu</b>\n\n"
                    msg += f"{page_title}\n\n"
                    msg += f"<a href='{href}'>Görüntüle</a>"
                    send_telegram_message(msg)
                    time.sleep(1)
                
                seen_history.append(href)
                new_found = True
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
    # Bugün 18 Eylül mü diye kontrol et
    is_critical_day = datetime.utcnow().day == 18 and datetime.utcnow().month == 9
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    if is_critical_day:
        # BUGÜN İÇİN: 5.5 Saatlik aralıksız nöbetçi döngüsü (GitHub sınırı 6 saattir)
        # Her döngü sonu 15 dakika uyur.
        for i in range(22):
            driver = webdriver.Chrome(options=options)
            try:
                check_yeditepe(driver)
                check_academic_jobs(driver)
            except:
                pass
            finally:
                driver.quit()
                
            if i < 21:
                time.sleep(15 * 60) # 15 dakika bekle
    else:
        # YARINDAN İTİBAREN: Eski tas tamam normal rutinine geri döner
        driver = webdriver.Chrome(options=options)
        try:
            check_yeditepe(driver)
            check_academic_jobs(driver)
        except:
            pass
        finally:
            driver.quit()

if __name__ == "__main__":
    main()
