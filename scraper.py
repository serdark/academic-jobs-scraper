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

def check_aydin(driver):
    # Sadece 29 Eylül 2026 TSİ 08:00'dan sonra çalışmaya başlar
    now = datetime.utcnow()
    start_time = datetime(2026, 9, 29, 5, 0) # TSİ 08:00
    
    if now < start_time:
        return
        
    seen_file = "seen_aydin.json"
    seen_history = json.load(open(seen_file)) if os.path.exists(seen_file) else []
    new_found = False
    
    try:
        driver.get("https://www.aydin.edu.tr/haberler/Pages/default.aspx?lang=tr")
        time.sleep(5)
        links = driver.find_elements(By.TAG_NAME, "a")
        
        all_hrefs = {}
        for link in links:
            try:
                href = link.get_attribute("href")
                text = link.text.strip()
                if href and ("aydin.edu.tr" in href) and len(text) > 5:
                    if "haberler" in href.lower() or "duyuru" in href.lower() or "default.aspx" in href.lower():
                        all_hrefs[href] = text
            except: continue
            
        for href, text in all_hrefs.items():
            if href not in seen_history:
                # 1. Aşama: Linkin dışarıdaki metninde kelime var mı?
                text_lower = turkish_lower(text)
                found = False
                
                if "sonuç" in text_lower or "değerlendirme" in text_lower:
                    found = True
                    page_title = text
                else:
                    # 2. Aşama: PDF değilse içine girip başlığına bak
                    if not href.endswith(".pdf"):
                        driver.get(href)
                        time.sleep(2)
                        page_title = driver.title if driver.title else text
                        title_lower = turkish_lower(page_title)
                        if "sonuç" in title_lower or "değerlendirme" in title_lower:
                            found = True
                            
                if found:
                    msg = f"📢 <b>Aydın Üniversitesi Duyurusu</b>\n\n"
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
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Bugün 29 Eylül mü?
    now = datetime.utcnow()
    is_critical_day = (now.day == 29 and now.month == 9)
    
    if is_critical_day:
        # BUGÜN İÇİN: 5.5 Saatlik aralıksız nöbetçi döngüsü (Aydın Üniv için)
        for i in range(22):
            driver = webdriver.Chrome(options=options)
            try:
                check_aydin(driver)
                check_academic_jobs(driver)
            except:
                pass
            finally:
                driver.quit()
                
            if i < 21:
                time.sleep(15 * 60) # 15 dakika bekle
    else:
        # NORMAL GÜNLER
        driver = webdriver.Chrome(options=options)
        try:
            check_aydin(driver)
            check_academic_jobs(driver)
        except:
            pass
        finally:
            driver.quit()

if __name__ == "__main__":
    main()
