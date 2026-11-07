# ارزیابی Local Research Agent

## ارزیابی retrieval

مجموعه‌ی `local_research_agent/evaluation_set.json` شش پرسش دستی و فایل مرتبط مورد انتظار را نگه می‌دارد. اجرا:

```powershell
.\.venv\Scripts\python.exe -m local_research_agent.evaluate --k 5
```

معیارها:

- **Hit@k:** نسبت پرسش‌هایی که دست‌کم یک فایل مرتبط در k نتیجه‌ی اول پیدا شده است.
- **MRR:** میانگین معکوس رتبه‌ی اولین فایل مرتبط؛ اگر رتبه ۱ باشد امتیاز ۱، رتبه ۲ امتیاز ۰٫۵، و اگر پیدا نشود صفر است.

این مجموعه فقط دو سند نمونه دارد؛ امتیاز ۱۰۰٪ روی شش مثال کوچک، معیار کیفیت عمومی، معنایی یا فارسی نیست. هنگام تغییر ranker، queryها را بازبینی و نمونه‌های دشوارتر اضافه کن.

## تست‌های نرم‌افزار

```powershell
.\.venv\Scripts\python.exe -m ruff check local_research_agent tests
.\.venv\Scripts\python.exe -m pytest --cov=local_research_agent --cov-report=term-missing
```

تست‌ها پاسخ، stop condition، citation، tool allowlist، path traversal، symlink، upload، consent مدل و parsing پاسخ tool-call را پوشش می‌دهند. Coverage حداقل CI در `pyproject.toml` تنظیم شده است.

## ارزیابی مدل زبانی

در حال حاضر برای مدل‌های مختلف benchmark کیفیت پاسخ ذخیره‌شده نداریم. Planner راه‌دور/local با mock HTTP در تست‌ها از نظر قرارداد tool call و citation بررسی می‌شود، اما کیفیت معناشناختی مدل با LLM-as-judge سنجیده نشده است. برای ارزیابی واقعی، لازم است مجموعه‌ی test پرسش/پاسخ/منبع مستقل و قضاوت انسانی اضافه شود؛ پاسخ‌های نمونه‌ی مدل را نباید جای annotation واقعی جا زد.
