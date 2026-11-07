# Lesson 18 — رابط وب، اجرا و تست‌های نسخه‌ی ۱

## اجرای برنامه

در Windows PowerShell از ریشه‌ی repo:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m local_research_agent.server
```

خط اول محیط جدا می‌سازد، خط دوم وابستگی‌های runtime را در همان محیط نصب می‌کند و خط سوم FastAPI را روی `127.0.0.1:8000` اجرا می‌کند. مرورگر را به `http://127.0.0.1:8000` ببر. مدل نصب نمی‌شود و key لازم نیست.

## رابط کاربری

- سمت چپ فقط فایل‌های انتخاب‌شده و sample notes را فهرست می‌کند.
- افزودن سند از file picker، drag/drop یا POST API می‌گذرد؛ suffix مجاز `.md` و `.txt` است.
- پرسش‌ها به `/api/ask` می‌روند و در حافظه‌ی سرور ذخیره نمی‌شوند.
- جواب شامل stop reason، trace ابزار، citation و quotation است.
- حالت مدل راه‌دور یک warning و checkbox consent قبل از درخواست دارد.
- محتوای پاسخ در DOM با API امن `textContent` درج می‌شود تا string مدل به HTML تبدیل نشود.

## تست و ارزیابی

- `tests/test_local_research_agent.py`: loop، search/read، path boundary، citation و سقف step.
- `tests/test_agent_api.py`: upload، limits، UI header، ask، consent، delete.
- `tests/test_planner.py`: پاسخ API مدل، function call، citations و خطای شبکه.
- `tests/test_config.py`: local/remote endpoint و secret behavior.
- `tests/test_evaluation.py`: floor ارزیابی regression.
- `tests/test_api.py`: تست‌های prototype تاریخی Pathfinder.

برای اندازه‌گیری retrieval، `python -m local_research_agent.evaluate --k 5` Hit@5 و MRR را روی شش query نمونه چاپ می‌کند. این benchmark کوچک نشانه‌ی کیفیت عمومی نیست؛ هدفش جلوگیری از regression در داده‌ی نمونه است.
