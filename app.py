import os
import json
import time
import requests
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from urllib.parse import unquote

app = Flask(__name__)

# ---------- تنظیمات کروم برای محیط سرور ----------
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")                # بدون رابط کاربری
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    # در صورتی که روی Render chromium نصب است، مسیر آن را مشخص کنید
    # chrome_options.binary_location = "/usr/bin/chromium"  # در صورت نیاز
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# ---------- تابع دانلود عکس ----------
def download_image(url, save_path="temp.jpg"):
    resp = requests.get(url, stream=True)
    if resp.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(resp.content)
        return save_path
    else:
        raise Exception("خطا در دانلود عکس")

# ---------- تابع اصلی پردازش لنز ----------
def get_gemini_answer(image_url, question):
    driver = None
    try:
        # ۱. دانلود عکس
        img_path = download_image(image_url)

        # ۲. راه‌اندازی مرورگر
        driver = get_driver()
        driver.get("https://lens.google.com")

        # ۳. کلیک روی دکمه آپلود (معمولاً دکمه دوربین یا آپلود)
        # ممکن است المنت‌ها تغییر کنند، ولی معمولاً یک input[type=file] وجود دارد
        # روش مطمئن‌تر: پیدا کردن input فایل و send_keys
        upload_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        upload_input.send_keys(os.path.abspath(img_path))

        # ۴. صبر برای بارگذاری و نمایش نتیجه
        # پس از آپلود، لنز تصویر را پردازش کرده و نتایج را نشان می‌دهد.
        # بخش خلاصه هوش مصنوعی معمولاً در یک div با کلاس خاصی قرار دارد.
        # با توجه به تغییرات احتمالی گوگل، بهتر است از XPath یا Selector انعطاف‌پذیر استفاده کنیم.
        # در حال حاضر (اواخر ۲۰۲۴) خلاصه در قسمتی با عنوان "AI Overview" یا "Gemini" است.
        time.sleep(3)  # اجازه بارگذاری اولیه

        # جستجوی متن خلاصه - ممکن است نیاز به تنظیم داشته باشد
        summary_elem = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'RveJvd')]//span"))
        )
        # یا ممکن است در یک div با data-attrid='description' باشد
        # به‌عنوان جایگزین: تمام متن‌های قابل مشاهده را بگیریم و قسمتی که سوال را پاسخ داده پیدا کنیم
        all_text = driver.find_element(By.TAG_NAME, "body").text
        # سعی می‌کنیم بخش مربوط به Gemini را جدا کنیم - این قسمت وابسته به ساختار صفحه است
        # راه حل بهتر: جستجوی متنی که با "Gemini" یا "AI" شروع می‌شود
        lines = all_text.splitlines()
        answer = None
        for i, line in enumerate(lines):
            if "Gemini" in line or "AI Overview" in line:
                # خط بعدی معمولاً پاسخ است
                if i+1 < len(lines):
                    answer = lines[i+1].strip()
                    break
        if not answer:
            # اگر پیدا نشد، کل متن را برگردانیم (احتیاط)
            answer = all_text

        return answer

    except Exception as e:
        raise Exception(f"خطا در پردازش لنز: {str(e)}")
    finally:
        if driver:
            driver.quit()

# ---------- اندپوینت API ----------
@app.route("/lens", methods=["GET"])
def lens_endpoint():
    pic_url = request.args.get("pic")
    question = request.args.get("q")

    if not pic_url or not question:
        return jsonify({"error": "پارامترهای 'pic' و 'q' الزامی هستند"}), 400

    try:
        pic_url = unquote(pic_url)
        question = unquote(question)  # در صورت نیاز می‌توان از سوال در جستجو استفاده کرد ولی لنز خودکار پاسخ می‌دهد

        # فراخوانی تابع اصلی
        answer = get_gemini_answer(pic_url, question)
        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
