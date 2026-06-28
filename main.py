from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright
import asyncio
import re
from urllib.parse import quote

app = FastAPI(title="Google Lens + Gemini Proxy")

@app.get("/lens")
async def lens(pic: str, q: str = "معنی این عکس چیه؟ توضیح کامل بده"):
    if not pic or not pic.startswith(("http://", "https://")):
        raise HTTPException(400, "pic باید URL معتبر تصویر باشه")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            page = await browser.new_page(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            lens_url = f"https://lens.google.com/uploadbyurl?url={quote(pic)}&hl=fa"
            await page.goto(lens_url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(5)
            await page.wait_for_load_state("networkidle", timeout=30000)
            
            # استخراج متن
            content = await page.evaluate("""() => {
                return Array.from(document.body.querySelectorAll('div, p, span, article, section'))
                    .map(el => el.innerText.trim())
                    .filter(t => t.length > 15)
                    .join('\\n\\n');
            }""")
            
            # استخراج بخش Gemini
            gemini_part = re.search(r'(?:این تصویر|این عکس|توضیح|Gemini|خلاصه|شناسایی|تحلیل).*?(?=\n{3,}|\Z)', content, re.S | re.I)
            response_text = gemini_part.group(0) if gemini_part else content[:4000]
            
            await browser.close()
            
            return {
                "status": "success",
                "image_url": pic,
                "query": q,
                "gemini_response": response_text.strip(),
                "raw_length": len(content)
            }
            
    except Exception as e:
        raise HTTPException(500, f"خطا: {str(e)}")
