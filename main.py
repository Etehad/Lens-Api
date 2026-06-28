from fastapi import FastAPI, HTTPException
import requests
from urllib.parse import quote

app = FastAPI(title="Image Analysis API")

HF_TOKEN = "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"   # بعداً بذار (اختیاری، بدون توکن هم کار می‌کنه با محدودیت)

@app.get("/lens")
async def lens(pic: str, q: str = "معنی این عکس چیه؟ توضیح کامل و دقیق بده"):
    try:
        # استفاده از مدل vision رایگان Hugging Face
        payload = {
            "inputs": {
                "image": pic,   # مستقیم URL می‌گیره
                "prompt": q
            }
        }
        
        # مدل خوب و سریع
        model = "Salesforce/blip-image-captioning-large"   # یا "google/paligemma-3b-mix-448"
        
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{model}",
            json=payload,
            headers={"Authorization": f"Bearer {HF_TOKEN}" if HF_TOKEN != "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" else ""}
        )
        
        if response.status_code == 200:
            result = response.json()
            description = result[0]["generated_text"] if isinstance(result, list) else str(result)
        else:
            description = f"خطا از HF: {response.text[:200]}"
        
        return {
            "status": "success",
            "image_url": pic,
            "query": q,
            "response": description
        }
        
    except Exception as e:
        raise HTTPException(500, str(e))
