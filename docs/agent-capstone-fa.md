# Local Research Agent — مشخصات و معیار تحویل نسخه‌ی ۱

## هدف محصول

یک برنامه‌ی local-first برای پژوهش روی فایل‌های شخصیِ انتخاب‌شده که پاسخ را به سند و بازه‌ی خط قابل‌بررسی وصل می‌کند. پروژه هدفش یادگیری Agent و ارائه‌ی یک نمونه‌ی عملی است؛ Pathfinder Canada فقط prototype تاریخی است.

## قابلیت‌های تکمیل‌شده

- [x] رابط وب responsive در یک سرویس FastAPI؛ برای demo یا اجرای offline، build جداگانه‌ی frontend لازم نیست.
- [x] انتخاب صریح فایل‌های Markdown و متن UTF-8 از browser؛ هیچ folder خودکار crawl نمی‌شود.
- [x] ذخیره در `.local_data/knowledge/` با ignore در Git، محدودیت تعداد/حجم/extension و نمایش library.
- [x] جست‌وجوی lexical رتبه‌بندی‌شده روی chunkهای خط‌محور، citation دقیق خط و read محدود.
- [x] loop با `ToolCall`, `Observation`, `FinalAnswer`, Planner contract، registry allowlist و سقف step.
- [x] شرط search-before-read؛ مدل نمی‌تواند مسیر خواندن را از خودش بسازد.
- [x] citationهای نهایی با داده‌ی واقعی read observation اعتبارسنجی می‌شوند.
- [x] حالت offline قابل‌استفاده بدون API key؛ شواهد را extractive نشان می‌دهد و summary جعلی نمی‌سازد.
- [x] planner اختیاری OpenAI-compatible برای tool calling با مسیر local Ollama یا endpoint راه‌دور HTTPS.
- [x] consent جداگانه برای هر پرسش وقتی مدل راه‌دور است؛ API key در پاسخ سلامت یا log اپلیکیشن نیست.
- [x] ابزارهای Agent فقط read/search؛ حذف سند از UI نیازمند تأیید کاربر است و در اختیار Agent نیست.
- [x] API tests، security regression tests، planner contract tests، retrieval evaluation و CI.
- [x] راهنمای اجرا و توضیح مرزهای اعتماد در README و docs.

## مدل تهدید مختصر

- **ورودی غیرقابل‌اعتماد:** سؤال کاربر، نام فایل و محتوای سند.
- **داده‌ی محافظت‌شده:** فایل‌هایی که کاربر در workspace انتخاب کرده و API key محلی.
- **عامل بالقوه‌ی مخرب:** محتوای سند با prompt injection، مدل ابزارمحور، ورودی path traversal یا درخواست cross-site.
- **مرز مجوز:** allowlist ابزارها، search-before-read، canonical path containment، سقف حجم، citation validator و consent remote model.
- **خطر باقیمانده:** مدل ممکن است citation معتبر را به claim نامربوط وصل کند؛ کاربر باید quotation و سند منبع را بازبینی کند. این برنامه multi-user یا public-server hardening ندارد.

## بیرون از دامنه‌ی نسخه‌ی ۱

- PDF/OCR و Office documents؛ embedding/vector database؛ حساب کاربری یا چندکاربره؛ تاریخچه‌ی دائمی؛ نوشتن فایل توسط Agent؛ ارسال پیام یا اقدام بیرونی.
- هر write/action احتمالی در نسخه‌های بعد باید پشت تأیید صریح انسان و یک permission contract مستقل باشد.
