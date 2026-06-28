from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright
import asyncio
import re
from urllib.parse import quote

app = FastAPI(title="Google Lens + Gemini Proxy")

@app.get("/lens")
async def lens(pic: str, q: str = "معنی این عکس چیه؟ توضیح کامل بده"):
    if not pic.startswith(("http",)):
        raise HTTPException(400, "pic نامعتبر")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-infobars',
                    '--window-size=1280,900'
                ]
            )
            page = await browser.new_page(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            )
            
            # مخفی کردن اتوماتیک بودن
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            """)
            
            lens_url = f"https://lens.google.com/uploadbyurl?url={quote(pic)}&hl=fa&re=df"
            await page.goto(lens_url, wait_until="domcontentloaded", timeout=60000)
            
            await asyncio.sleep(6)  # صبر بیشتر
            await page.wait_for_load_state("networkidle", timeout=40000)
            
            # استخراج بهتر
            content = await page.evaluate("""() => document.body.innerText""")
            
            # فیلتر بهتر برای Gemini response
            patterns = [
                r'(?:این تصویر|این عکس|نشان می‌دهد|Gemini|خلاصه|توضیح|تحلیل|شناسایی).*?(?=\n{4,}|\Z)',
                r'(.{100,600}?(?:توضیح|معنی|چیست|است))'  # fallback
            ]
            
            gemini_response = "جواب Gemini پیدا نشد"
            for pattern in patterns:
                match = re.search(pattern, content, re.S | re.I)
                if match:
                    gemini_response = match.group(0).strip()
                    break
            
            await browser.close()
            
            return {
                "status": "success",
                "image_url": pic,
                "query": q,
                "gemini_response": gemini_response,
                "raw_length": len(content)
            }
            
    except Exception as e:
        raise HTTPException(500, f"خطا: {str(e)}")
