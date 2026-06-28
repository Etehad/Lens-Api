from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from playwright.sync_api import sync_playwright
import time
import re
import os
from urllib.parse import quote

app = FastAPI(title="Google Lens + Gemini API Proxy")

@app.get("/lens")
async def lens(pic: str, q: str = "معنی این عکس چیه؟ توضیح کامل بده"):
    if not pic.startswith("http"):
        raise HTTPException(400, "pic باید URL معتبر تصویر باشه")
    
    try:
        with sync_playwright() as p:
            # headless=True، viewport مناسب
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            page = browser.new_page(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            encoded_url = quote(pic)
            lens_url = f"https://lens.google.com/uploadbyurl?url={encoded_url}&hl=fa"  # hl=fa برای فارسی
            
            page.goto(lens_url, wait_until="networkidle", timeout=60000)
            time.sleep(4)  # صبر برای لود اولیه Gemini
            
            # صبر برای ظاهر شدن بخش AI summary (Gemini)
            try:
                page.wait_for_selector('div[role="main"] div[class*="gemini"], textarea, [data-attrid*="gemini"]', timeout=15000)
            except:
                pass  # ادامه می‌ده حتی اگر دقیق پیدا نکنه
            
            # استخراج تمام متن‌های قابل مشاهده (به خصوص Gemini response)
            content = page.evaluate('''() => {
                const texts = Array.from(document.querySelectorAll('div, p, span, h1, h2, article'))
                    .map(el => el.innerText.trim())
                    .filter(t => t.length > 10);
                return [...new Set(texts)].join('\\n\\n');  // حذف تکراری
            }''')
            
            # تمیز کردن و پیدا کردن بخش اصلی Gemini
            gemini_match = re.search(r'(?:این تصویر|این عکس|Gemini|خلاصه|توضیح).*?(?=\n\n\n|\Z)', content, re.S | re.I)
            response_text = gemini_match.group(0) if gemini_match else content[:3000]
            
            browser.close()
            
            return JSONResponse({
                "status": "success",
                "query": q,
                "image_url": pic,
                "gemini_response": response_text.strip(),
                "full_content_length": len(content)
            })
            
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
