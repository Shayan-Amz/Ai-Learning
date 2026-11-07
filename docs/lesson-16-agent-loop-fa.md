# Lesson 16 — حلقه‌ی Agent در نسخه‌ی قابل‌استفاده

این درس درباره‌ی قراردادهای Agent و چرخه‌ی تصمیم/اجرا است. نسخه‌ی فعلی در `local_research_agent/core.py` قرار دارد و برای وب از planner آفلاین یا اختیاریِ tool-calling استفاده می‌کند.

## مدل ذهنی

یک Agent در این پروژه یک `while` بی‌قید یا chatbot با مجوز عمومی نیست. هر گام باید یک action از دو نوع باشد:

1. `ToolCall`: درخواست اجرای یک ابزار دقیق با arguments مشخص.
2. `FinalAnswer`: پاسخ نهایی همراه citationهایی که باید از evidence واقعی آمده باشند.

`ToolRegistry` تنها handlerهای ثبت‌شده را می‌شناسد. پس از اجرا، `Observation` موفقیت/خطای ابزار را نگه می‌دارد. Planner می‌تواند با دیدن observation بعدی را انتخاب کند؛ ولی policyهای loop خارج از اختیار Planner می‌مانند.

## چرخه‌ی واقعی

1. `ResearchAgent.run(goal)` اعتبار goal و سقف تعداد گام را بررسی می‌کند.
2. Planner یک action می‌دهد.
3. اگر action ابزار ناشناخته باشد Registry آن را اجرا نمی‌کند.
4. اگر ابزار `read_document` باشد، Agent چک می‌کند که مسیر در search قبلی دیده شده باشد.
5. Observation به planner بعدی داده می‌شود.
6. برای پایان، Agent بررسی می‌کند search انجام شده، نتیجه واقعاً خوانده شده و citation با path/lineهای read هم‌پوشانی دقیق دارد.
7. در خطای مدل یا سقف step، Agent با `stop_reason` روشن متوقف می‌شود.

## چرا policy داخل Agent است؟

اگر فقط به prompt بگوییم «فایل خارج از پوشه را نخوان»، آن محدودیت از بین می‌رود اگر مدل prompt را نادیده بگیرد. در این نسخه دو سد کد داریم: ابزارها مسیر را canonicalize و containment را بررسی می‌کنند؛ خود Agent هم `read_document` را به result قبلی search محدود می‌کند. مدل پیشنهاددهنده است، نه مرجع دسترسی.

## نقاط شروع در کد

- `ToolCall`, `Citation`, `FinalAnswer`, `Observation`, `AgentResult`: data contractهای کوچک و ثابت.
- `ToolRegistry.execute`: تنها نقطه‌ی اجرای handlerهای allowlist.
- `ResearchAgent.run`: loop محدود و ثبت observations.
- `ResearchAgent._authorize_tool_call`: شرط search-before-read.
- `ResearchAgent._finish`: شرط evidence و اعتبار citation.
- `Planner` protocol: قرارداد مشترک بین planner آفلاین و LLM.

وقتی آموزش خط‌به‌خط را شروع کنیم، همین مسیر را با اجرای PowerShell و trace واقعی قدم‌به‌قدم باز می‌کنیم؛ این سند عمداً مرز معماری را مشخص می‌کند، نه اینکه کد فعلی را به جعبه‌ی سیاه تبدیل کند.
