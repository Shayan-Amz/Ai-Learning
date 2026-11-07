# معماری Local Research Agent

این سند معماری نسخه‌ی قابل‌استفاده‌ی وب را توضیح می‌دهد. این پروژه Agent پژوهشگر فایل‌های محلی است؛ Pathfinder در `backend/` و `frontend/` فقط prototype تاریخی است.

## جریان یک درخواست

```text
پرسش کاربر
  → Planner پیشنهاد می‌دهد
  → Agent سیاست مرحله را بررسی می‌کند
  → Registry فقط ابزار ثبت‌شده را اجرا می‌کند
  → Observation ثبت می‌شود
  → Planner ادامه می‌دهد یا FinalAnswer می‌دهد
  → Citationها با readهای واقعی تطبیق داده می‌شوند
  → پاسخ، منابع و trace به UI برمی‌گردد
```

1. کاربر فایل‌های `.md` یا `.txt` مشخصی را در رابط وب انتخاب می‌کند. فایل‌ها در `.local_data/knowledge/` ذخیره می‌شوند؛ هیچ پوشه‌ی Home یا Drive به‌صورت خودکار crawl نمی‌شود.
2. برای پرسش، `ExtractivePlanner` در حالت پیش‌فرض query را به ابزار `search_documents` می‌دهد. Search با رتبه‌بندی واژگانی BM25-style بین chunkهای شش‌خطی جست‌وجو می‌کند.
3. Agent اجازه نمی‌دهد اولین action خواندن مستقیم فایل باشد. مسیر فایل باید در نتیجه‌ی search قبلی آمده باشد.
4. `read_document` فقط بازه‌ی محدود خط‌ها را برمی‌گرداند و شماره‌ی خط را نگه می‌دارد.
5. Planner آفلاین passageهای پیدا‌شده را عیناً و با citation نشان می‌دهد. Planner مدل‌محور، اگر تنظیم شده باشد، می‌تواند آن‌ها را خلاصه کند.
6. Agent citation را فقط وقتی می‌پذیرد که path و بازه‌ی خط دقیقاً در Observation خواندن وجود داشته باشد. پاسخ مدل با citation نامعتبر یا بدون citationِ قابل‌تأیید نمایش داده نمی‌شود.
7. اجرای هر پرسش سقف step دارد و `stop_reason`، ابزارها و نتیجه‌ی آن‌ها در trace ثبت می‌شوند.

## اجزای کد

| مسیر | مسئولیت |
|---|---|
| `local_research_agent/core.py` | قرارداد action/observation، Registry، loop محدود، اجبار search-before-read و اعتبارسنجی citation |
| `local_research_agent/tools.py` | ranker، chunking خط‌محور، سقف حجم و فایل، بررسی مسیر و ابزارهای read-only |
| `local_research_agent/planner.py` | planner آفلاین و planner سازگار با OpenAI Chat Completions و tool calling |
| `local_research_agent/config.py` | خواندن تنظیمات محیط، تشخیص مدل محلی/راه‌دور و کنترل URL امن |
| `local_research_agent/api.py` | FastAPI، مدیریت سند، consent راه‌دور، پاسخ ساخت‌یافته و UI استاتیک |
| `local_research_agent/static/` | رابط وب responsive؛ متن فایل و خروجی مدل با `textContent` درج می‌شوند، نه HTML اجرایی |
| `local_research_agent/evaluate.py` | محاسبه‌ی Hit@k و MRR روی مجموعه‌ی کوچک نمونه |

## Plannerها

### Offline / ExtractivePlanner

- بدون کلید، مدل، اینترنت یا هزینه اجرا می‌شود.
- از پرسش، جست‌وجو می‌کند و حداکثر سه passage را می‌خواند.
- متن شواهد را با شماره‌ی خط نمایش می‌دهد؛ خلاصه‌ی ساختگی تولید نمی‌کند.

### OpenAICompatiblePlanner

- فقط زمانی فعال می‌شود که هم `LOCAL_RESEARCH_LLM_BASE_URL` و هم `LOCAL_RESEARCH_LLM_MODEL` تنظیم شده باشند.
- schema ابزارها فقط `search_documents`، `read_document` و `finish` را تعریف می‌کند؛ `finish` action نهایی است و ابزار اجرایی نیست.
- در هر درخواست حداکثر یک action از مدل گرفته می‌شود؛ Registry و سیاست Agent همچنان مرجع نهایی مجوزند.
- Ollama روی loopback به‌عنوان مدل محلی شناخته می‌شود. Endpoint راه‌دور باید HTTPS باشد و برای هر پرسش consent صریح رابط لازم است.

## قراردادهای API

- `GET /api/health`: وضعیت، تعداد سند، mode مدل و نام ابزارهای مجاز؛ مسیر کامل پوشه و API key برگردانده نمی‌شود.
- `GET /api/documents`: نام نسبی و metadata فایل‌های مجاز.
- `POST /api/documents`: افزودن فایل‌های انتخاب‌شده با سقف تعداد، اندازه، فرمت و UTF-8.
- `DELETE /api/documents/{path}`: حذف فقط فایل داخل workspace و فقط با درخواست UI تأییدشده.
- `POST /api/ask`: پرسش، پاسخ، citationهای قابل‌تأیید و trace.
- `GET /api/docs`: OpenAPI UI محلی.

## تنظیمات و داده

- `.env.example` الگوی بی‌رمز است؛ `.env` در Git نادیده گرفته می‌شود.
- `.local_data/` شامل سندهای انتخاب‌شده است و در Git ثبت نمی‌شود.
- تنظیمات مدل هرگز شامل transcript ذخیره‌شده نیست؛ هر پرسش یک اجرای مستقل است.
- میزبان پیش‌فرض `127.0.0.1` است. سرویس برای چندکاربره یا اینترنت عمومی طراحی نشده است.
