# Pathfinder Canada — Graduate Program Explorer

Pathfinder یک ابزار پژوهشی کوچک و قابل‌گسترش برای کشف، بررسی و مقایسه‌ی برنامه‌های کارشناسی ارشد علوم کامپیوتر و هوش مصنوعی در کاناداست. این نسخه روی **منبع رسمی، تاریخ بررسی و اعلام شفافِ اطلاعات جمع‌آوری‌نشده** تمرکز دارد؛ قرار نیست به‌جای متقاضی تصمیم بگیرد یا درخواست ارسال کند.

> **وضعیت:** نمونه‌ی اولیه‌ی end-to-end؛ کاتالوگ اولیه ۳ برنامه را پوشش می‌دهد. داده‌ها snapshot مورخ ۵ نوامبر ۲۰۲۶ هستند و خوراک زنده‌ی پذیرش نیستند.

## تجربه‌ی فعلی

- جست‌وجو و فیلتر برنامه‌ها بر اساس دانشگاه، حوزه، نوع برنامه و استان.
- ذخیره‌ی shortlist در مرورگر؛ شناسه‌ی برنامه‌ها فقط در همان مرورگر نگه‌داری می‌شوند.
- checklist پژوهش برای برنامه‌های shortlistشده؛ یادآورها به factها/منابع موجود وصل‌اند و وضعیت انجام‌شدن فقط محلی ذخیره می‌شود.
- مقایسه‌ی ۲ یا ۳ برنامه بر اساس deadline، پیش‌نیازها، مدت، شیوه‌ی برگزاری، شهریه و اطلاعات قابل‌مقایسه‌ی دیگر.
- مشاهده‌ی جزئیات هر fact و بازکردن صفحه‌ی رسمیِ پشتیبان آن.
- نمایش مقدار `Not captured` به‌جای حدس؛ برای نمونه شهریه‌ی هر سه برنامه هنوز جمع‌آوری نشده است.
- API مستندشده با OpenAPI/Swagger در `/api/docs`.
- اعتبارسنجی داده‌ی کاتالوگ با Pydantic و تست API با pytest.

## دامنه‌ی کاتالوگ اولیه

| برنامه | نوع | دانشگاه / استان | نکته‌ی نمونه |
|---|---|---|---|
| MScAC — Artificial Intelligence | حرفه‌ای | University of Toronto · Ontario | مهلت Fall 2027 ثبت‌شده: ۱ دسامبر ۲۰۲۶ |
| MMath — Computer Science | پژوهشی | University of Waterloo · Ontario | گزینه‌ی thesis؛ مهلت September 2027 ثبت‌شده: ۱ دسامبر ۲۰۲۶ |
| MSc — Computer Science | پژوهشی | The University of British Columbia · British Columbia | مهلت درج‌شده برای شروع September 2027 یا January 2028: ۱۵ دسامبر ۲۰۲۶ |

شرح factها، صفحات رسمی، تاریخ بررسی و محدودیت‌های snapshot در [مستند داده و منابع](docs/data-and-sources-fa.md) آمده است. جزئیات معماری و مرزهای ایمنی در [مستند معماری](docs/architecture-fa.md) ثبت شده‌اند.

## فناوری‌ها

- **Backend:** Python، FastAPI، Pydantic
- **Frontend:** React، TypeScript، Vite
- **Tests:** pytest، FastAPI TestClient
- **Data:** فایل JSON نسخه‌بندی‌شده؛ در این مرحله پایگاه داده، scraping خودکار، LLM یا API key وجود ندارد.

## اجرا در Windows PowerShell

فرمان‌های زیر را از ریشه‌ی مخزن اجرا کن. برای Backend و Frontend دو پنجره‌ی PowerShell جدا باز بگذار.

### ۱) نصب و اجرای Backend — پنجره‌ی اول

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

- `py -m venv .venv` محیط Python جداگانه‌ای به نام `.venv` می‌سازد تا وابستگی‌های پروژه با Python سراسری قاطی نشوند.
- `Activate.ps1` همان محیط را برای پنجره‌ی PowerShell فعلی فعال می‌کند؛ فعال‌سازی در پنجره‌ی جدید باید تکرار شود.
- `python -m pip install -r requirements-dev.txt` FastAPI، Uvicorn، Pydantic و ابزارهای تست را داخل همان محیط نصب می‌کند.
- `python -m uvicorn backend.main:app ...` برنامه‌ی FastAPI را روی پورت `8000` اجرا می‌کند؛ `--reload` هنگام تغییر فایل‌های Backend سرویس توسعه را تازه می‌کند و `--host 0.0.0.0` برای دسترسی از محیط preview لازم است.

اگر PowerShell اجرای اسکریپت فعال‌سازی را در همین پنجره مسدود کرد، این فرمان موقت را اجرا و سپس `Activate.ps1` را دوباره امتحان کن:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

این تنظیم فقط برای همان فرایند PowerShell است و سیاست دائمی سیستم را تغییر نمی‌دهد. اگر نخواستی محیط را فعال کنی، به‌جای دو فرمان آخر Backend از مسیر مستقیم Python محیط استفاده کن:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

فرمان اول وابستگی‌ها را با Python همان محیط نصب می‌کند؛ فرمان دوم Uvicorn همان محیط را برای اجرای API به کار می‌گیرد.

### ۲) نصب و اجرای Frontend — پنجره‌ی دوم

```powershell
cd frontend
npm install
npm run dev
```

- `cd frontend` پوشه‌ی کاری را به Frontend تغییر می‌دهد.
- `npm install` وابستگی‌های React، TypeScript، Vite و آیکون‌ها را از `package.json` نصب می‌کند.
- `npm run dev` سرور توسعه‌ی Vite را اجرا می‌کند؛ درخواست‌های نسبی `/api` از طریق proxy به Backend روی پورت `8000` می‌روند.

در مرورگر محلی آدرس `http://localhost:5173` را باز کن. مستند API محلی در `http://localhost:8000/api/docs` است. در preview محیط Arena، صفحه‌ی Frontend را از preview باز کن؛ لازم است هر دو سرویس در حال اجرا باشند.

## تست و build

برای تست Backend، از ریشه‌ی مخزن و در پنجره‌ای که محیط Python فعال است اجرا کن:

```powershell
python -m pytest
```

این فرمان سناریوهای سلامت API، جست‌وجو، فیلتر، fact ناموجود، ترتیب مقایسه و ارجاع منابع را اجرا می‌کند.

برای بررسی type و ساخت فایل‌های Frontend:

```powershell
cd frontend
npm run build
```

`cd frontend` محل اجرای فرمان را به پوشه‌ی Frontend می‌برد؛ `npm run build` ابتدا TypeScript را بررسی و سپس نسخه‌ی تولیدی Vite را در `frontend/dist/` می‌سازد.

## APIهای اصلی

| درخواست | کاربرد |
|---|---|
| `GET /api/health` | وضعیت سرویس و تاریخ snapshot |
| `GET /api/overview` | تعداد برنامه‌ها، صفحات رسمی و factهای تأییدشده |
| `GET /api/programs` | کاتالوگ؛ فیلترهای اختیاری `q`، `province`، `program_type` و `field` |
| `GET /api/programs/{program_id}` | پروفایل کامل یک برنامه |
| `GET /api/compare?ids=id1,id2` | بازیابی ۲ تا ۳ برنامه برای مقایسه، با حفظ ترتیب انتخاب |

## اصول محصول

1. **ارجاع‌پذیری:** هر fact با وضعیت `verified` به یک شناسه‌ی منبع رسمی وصل است؛ مدل داده این رابطه را اعتبارسنجی می‌کند.
2. **عدم حدس:** `not_collected` باید بدون مقدار بماند. صفر، میانگین، شهریه‌ی حدسی یا شرط استنباط‌شده جای داده‌ی مفقود را نمی‌گیرد.
3. **تاریخ‌دار بودن:** تاریخ بررسی همراه هر برنامه و هر صفحه ثبت می‌شود؛ تاریخ بررسی به‌تنهایی تضمین نمی‌کند اطلاعات هنوز به‌روز باشد.
4. **انسان در حلقه:** ابزار تحقیق و مقایسه می‌کند، اما اپلای، پرداخت یا ارسال پیام خودکار انجام نمی‌دهد.
5. **حداقل دسترسی:** در نسخه‌ی فعلی پروفایل حساس، مدارک متقاضی، رمز، API key یا backend برای ذخیره‌ی اطلاعات شخصی وجود ندارد.

## آرشیو یادگیری

پروژه‌ی Pathfinder جای درس‌های قبلی را نمی‌گیرد؛ تمرکز فعلی روی ساخت محصول است و آرشیو آموزشی در دسترس می‌ماند:

- [نقشه‌راه ۱۶ هفته‌ای](docs/roadmap-fa.md) و [شرح پروژه‌ی پایانی](docs/capstone-fa.md)
- [درس ۰ — مبانی Git](docs/lesson-00-git-basics-fa.md) · [درس ۱ — مبانی API](docs/lesson-01-api-basics-fa.md) · [درس ۲ — query و مجموعه‌ها](docs/lesson-02-api-collections-fa.md)
- [درس ۳ — خطاهای HTTP](docs/lesson-03-api-errors-fa.md) · [درس ۴ — POST و header](docs/lesson-04-post-and-headers-fa.md) · [درس ۵ — اعتبارسنجی Pydantic](docs/lesson-05-pydantic-validation-fa.md) · [درس ۶ — متغیر محیطی و احراز هویت](docs/lesson-06-env-vars-auth-fa.md)
- [درس ۷ — مبانی LLM](docs/lesson-07-llm-fundamentals-fa.md) · [درس ۸ — tokenization](docs/lesson-08-tokenization-fa.md) · [درس ۹ — BPE toy](docs/lesson-09-bpe-toy-fa.md) · [درس ۱۰ — شناسه‌ی token](docs/lesson-10-token-ids-fa.md)
- [درس ۱۱ — token embedding](docs/lesson-11-token-embedding-lookup-fa.md) · [درس ۱۲ — text embeddings](docs/lesson-12-text-embeddings-similarity-fa.md) · [درس ۱۳ — بازیابی toy در RAG](docs/lesson-13-rag-retrieval-toy-fa.md) · [درس ۱۴ — chunking و metadata](docs/lesson-14-chunking-metadata-fa.md) · [درس ۱۵ — top-k و prompt preview](docs/lesson-15-rag-topk-prompt-preview-fa.md)
