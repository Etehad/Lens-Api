from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from playwright.sync_api import sync_playwright
import time
import re
from urllib.parse import quote

app = FastAPI(title="Google Lens + Gemini Proxy")

@app.get("/lens")
async def lens(pic: str, q: str = "معنی این عکس چیه؟ توضیح کامل بده"):
    if not pic or not pic.startswith(("http://", "https://")):
        raise HTTPException(400, "pic باید URL معتبر باشه")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            page = browser.new_page(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            lens_url = f"https://lens.google.com/uploadbyurl?url={quote(pic)}&hl=fa"
            page.goto(lens_url, wait_until="domcontentloaded", timeout=45000)
            
            # صبر برای لود Gemini
            time.sleep(5)
            page.wait_for_load_state("networkidle", timeout=30000)
            
            # استخراج متن
            content = page.evaluate("""() => {
                return Array.from(document.body.querySelectorAll('div, p, span, article, section'))
                    .map(el => el.innerText.trim())
                    .filter(t => t.length > 15)
                    .join('\\n\\n');
            }""")
            
            # سعی برای استخراج بخش اصلی Gemini
            gemini_part = re.search(r'(?:این تصویر|این عکس|توضیح|Gemini|خلاصه|شناسایی).*?(?=\n{3,}|\Z)', content, re.S | re.I)
            response_text = gemini_part.group(0) if gemini_part else content[:3500]
            
            browser.close()
            
            return {
                "status": "success",
                "image": pic,
                "query": q,
                "gemini_response": response_text.strip(),
            }
            
    except Exception as e:
        raise HTTPException(500, f"خطا: {str(e)}")
