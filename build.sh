#!/usr/bin/env bash
# اول پکیج‌ها رو نصب کن
pip install -r requirements.txt

# بعد Playwright و مرورگر رو نصب کن
playwright install chromium --with-deps
