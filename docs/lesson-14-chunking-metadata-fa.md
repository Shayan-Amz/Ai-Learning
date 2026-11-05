# درس ۱۴ — chunking و حفظ metadata منبع

## هدف و منبع

این تمرین از بخش chunking در [Phase 11, Lesson 06: RAG](https://github.com/rohitg00/ai-engineering-from-scratch/tree/main/phases/11-llm-engineering/06-rag) الهام گرفته است. یک متن نمونه را به قطعه‌ها می‌شکنیم و عنوان، URL و بخش منبع را همراه هر قطعه نگه می‌داریم. کد و خروجی ASCII هستند؛ URL و متن کاملاً فرضی‌اند.

## مدل ذهنی

سند بلند را می‌شکنیم تا بعداً بتوانیم بخش مرتبط را بازیابی کنیم. هر قطعه باید همچنان به سند اصلی قابل‌ردیابی باشد، پس metadata مانند `source_id`, `title`, `url` و `section` کنار هر chunk می‌آید.

در این تمرین:

- `chunk_size = 8` یعنی حداکثر ۸ بخشِ جداشده با فاصله در هر قطعه؛ این **تعداد token واقعی مدل نیست**.
- `overlap = 2` یعنی دو بخش از انتهای هر قطعه در ابتدای قطعه‌ی بعدی هم تکرار می‌شوند.
- overlap کمک می‌کند زمینه‌ی مرز حفظ شود، اما متن و نتیجه‌ی تکراری هم ایجاد می‌کند.

## کد اجرایی

فایل `chunking_demo.py`:

```python
text = (
    "Applicants submit transcripts. "
    "Applicants provide English test scores. "
    "Some programs require references. "
    "Deadlines vary by program."
)

source = {
    "doc_id": "demo-admissions-2026",
    "title": "Admissions guide (demo)",
    "url": "https://university.example/admissions",
    "section": "Requirements",
}

chunk_size = 8
overlap = 2

words = text.split()

if chunk_size <= 0:
    raise ValueError("chunk_size must be positive")

if overlap < 0 or overlap >= chunk_size:
    raise ValueError("overlap must be smaller than chunk_size")

chunks = []
start = 0

while start < len(words):
    end = start + chunk_size
    current_words = words[start:end]

    chunk = {
        "chunk_id": f"{source['doc_id']}-{len(chunks)}",
        "text": " ".join(current_words),
        "source_id": source["doc_id"],
        "title": source["title"],
        "url": source["url"],
        "section": source["section"],
    }
    chunks.append(chunk)

    if end >= len(words):
        break

    start = end - overlap

for chunk in chunks:
    print("Chunk ID:", chunk["chunk_id"])
    print("Text:", chunk["text"])
    print("Source URL:", chunk["url"])
    print("Section:", chunk["section"])
    print()
```

اجرا در PowerShell:

```powershell
.\.venv\Scripts\python.exe .\chunking_demo.py
```

## توضیح ساده و خط‌به‌خط

1. `text` متن نمونه است؛ کنار هم قرار گرفتن رشته‌ها داخل پرانتز فقط برای خواناتر شدن کد است.
2. `source` دیکشنری metadata سند اصلی است.
3. `chunk_size` سقف اندازه‌ی قطعه را تعیین می‌کند؛ `overlap` مقدار هم‌پوشانی است.
4. `text.split()` متن را در فاصله‌ها جدا می‌کند و فهرست `words` می‌سازد.
5. شرط اول جلوی اندازه‌ی صفر یا منفی را می‌گیرد.
6. شرط دوم جلوی overlap منفی یا overlap هم‌اندازه/بزرگ‌تر از chunk را می‌گیرد؛ چنین تنظیمی ممکن است شروع حلقه را جلو نبرد.
7. `chunks` فهرست خالی است و `start` از ابتدای فهرست شروع می‌شود.
8. در هر دور، `end` انتهای محدوده را مشخص می‌کند؛ sliceِ `words[start:end]` عضو `end` را شامل نمی‌شود.
9. `chunk` یک رکورد شامل شناسه‌ی chunk، متن آن و metadata منبع می‌سازد.
10. `chunks.append(chunk)` رکورد را ذخیره می‌کند.
11. اگر `end` به انتهای متن رسیده یا از آن گذشته باشد، `break` حلقه را تمام می‌کند.
12. در غیر این صورت `start = end - overlap` شروع بعدی را عقب می‌آورد تا کلمات مرزی دوباره بیایند.
13. حلقه‌ی پایانی متن و metadata هر قطعه را چاپ می‌کند.

## نتیجه‌ی واقعی کاربر

### با `overlap = 2`

سه قطعه ساخته شد. قطعه‌ی دوم با `test scores.` و قطعه‌ی سوم با `Deadlines vary` شروع شد؛ این دو جفت کلمه، overlap میان همسایه‌ها بودند.

### پس از تغییر به `overlap = 0`

کاربر درست پیش‌بینی کرد که دو قطعه ساخته می‌شود و قطعه‌ی دوم با `Some` شروع خواهد شد. خروجی واقعی:

```text
Chunk ID: demo-admissions-2026-0
Text: Applicants submit transcripts. Applicants provide English test scores.
Source URL: https://university.example/admissions
Section: Requirements

Chunk ID: demo-admissions-2026-1
Text: Some programs require references. Deadlines vary by program.
Source URL: https://university.example/admissions
Section: Requirements
```

## محدودیت‌ها و خطاهای رایج

- `split()` تعداد کلمه‌های جداشده با فاصله را می‌سنجد، نه tokenهای مدل.
- fixed-size chunking ممکن است مرز جمله یا ایده را بشکند؛ اندازه‌ی عددی همیشه بهترین مرز معنایی نیست.
- overlap زمینه را حفظ می‌کند، ولی بخشی از متن را تکرار می‌کند؛ در retrieval واقعی باید اثرش را با پرسش‌های آزمایشی بسنجیم.
- `.example` منبع واقعی یا رسمی نیست؛ برای Pathfinder فقط URL صفحه‌ی رسمی واقعی را وارد می‌کنیم.
- اگر URL/metadata از هر chunk جدا شود، ممکن است نتوانیم پاسخ را به منبع درست ارجاع دهیم.

## مرور پایان درس ۱۴

### خلاصه

- `text.split()` داده را برای تمرین به بخش‌های جداشده با فاصله تبدیل کرد.
- `chunk_size` اندازه‌ی سقف و `overlap` میزان تکرار میان قطعه‌های مجاور را تعیین کرد.
- شروع قطعه‌ی بعدی برابر `end - overlap` است.
- با ۱۶ بخش، اندازه‌ی ۸ و overlap برابر ۲، شروع‌ها ۰، ۶ و ۱۲ است؛ بنابراین سه قطعه ساخته شد.
- با overlap برابر صفر، شروع‌ها ۰ و ۸ می‌شوند و دو قطعه ساخته می‌شود.
- هر chunk متن و metadata منبع را با هم نگه می‌دارد تا بازیابی قابل‌ارجاع باشد.

### خودآزمایی با پاسخ

1. چرا با overlap برابر ۲ سه chunk به‌وجود آمد؟ **شروع‌ها با گام `8 - 2 = 6` جلو رفتند: ۰، ۶، ۱۲.**
2. اگر overlap صفر باشد، چرا chunk دوم با `Some` شروع شد؟ **شروع دوم برابر ۸ است و `Some` در index 8 قرار دارد.**
3. آیا عدد ۸ این‌جا تعداد tokenهای LLM است؟ **نه؛ تعداد بخش‌های جداشده با فاصله در این مثال است.**
4. چرا metadata را به هر chunk وصل کردیم؟ **تا متن بازیابی‌شده به سند و URL اصلی قابل‌ردیابی باشد.**
