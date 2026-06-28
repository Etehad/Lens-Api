from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import requests
import re
from urllib.parse import quote
import time

app = FastAPI()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml",
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

@app.get("/lens")
async def lens(pic: str, q: str = "معنی این عکس چیه"):
    try:
        # اول redirect به صفحه Lens
        session = requests.Session()
        session.headers.update(HEADERS)
        
        lens_url = f"https://lens.google.com/uploadbyurl?url={quote(pic)}&hl=fa"
        resp = session.get(lens_url, allow_redirects=True, timeout=30)
        
        text = resp.text
        
        # سعی استخراج Gemini part
        gemini_match = re.search(r'(?:این تصویر|این عکس|Gemini|توضیح|خلاصه|شناسایی|تحلیل).*?(\.|!|\?|\n\n)', text, re.S | re.I)
        
        if gemini_match:
            response_text = gemini_match.group(0)
        else:
            response_text = "جواب Gemini استخراج نشد. تصویر رو دستی در Google Lens تست کن."
        
        return {
            "status": "success",
            "image_url": pic,
            "gemini_response": response_text.strip()[:800],
        }
        
    except Exception as e:
        raise HTTPException(500, str(e))
