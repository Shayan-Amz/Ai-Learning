# درس ۱۲ — text embedding و شباهت کسینوسی

## هدف و منبع

این درس از [Phase 11, Lesson 04: Embeddings](https://github.com/rohitg00/ai-engineering-from-scratch/tree/main/phases/11-llm-engineering/04-embeddings) الهام گرفته است؛ تمرکز ما فعلاً بر تفاوت text embedding و token embedding و ایده‌ی similarity است. کد از بردارهای toy و متن ASCII استفاده می‌کند؛ API صدا زده نمی‌شود.

## دو مفهوم متفاوت

- **Token embedding:** درون مدل زبانی، هر token ID به بردار ورودی خودش lookup می‌شود.
- **Text embedding:** مدل embedding برای یک پرسش یا تکه‌متن یک بردار می‌سازد. سامانه‌ی RAG می‌تواند بردار پرسش را با بردار chunkهای سند مقایسه کند تا متن‌های مرتبط را پیدا کند.

شباهت embedding **مدرک یا citation نیست**. Pathfinder همچنان باید URL و مشخصات منبع رسمی را جداگانه نگه دارد و متن بازیابی‌شده را بررسی کند.

## مدل ذهنی شباهت کسینوسی

Cosine similarity جهت دو بردار را مقایسه می‌کند. در مثال ما بردار پرسش `[1.0, 0.0]` است؛ بردار `admissions` تقریباً هم‌جهت آن انتخاب شده، اما `dining` جهت متفاوتی دارد. اعداد عمداً دستی انتخاب شده‌اند؛ این کد هیچ متن واقعی را embed نمی‌کند.

## کد اجرایی

فایل `cosine_toy.py` را با کد ASCII بساز:

```python
from math import sqrt


def cosine_similarity(left, right):
    dot_product = sum(a * b for a, b in zip(left, right))
    magnitude_left = sqrt(sum(value * value for value in left))
    magnitude_right = sqrt(sum(value * value for value in right))
    return dot_product / (magnitude_left * magnitude_right)


query_vector = [1.0, 0.0]

document_vectors = {
    "admissions": [0.9, 0.1],
    "dining": [0.1, 0.9],
}

for name, vector in document_vectors.items():
    score = cosine_similarity(query_vector, vector)
    print(f"{name}: {score:.3f}")
```

اجرا از PowerShell:

```powershell
.\.venv\Scripts\python.exe .\cosine_toy.py
```

## توضیح ساده و خط‌به‌خط

1. `from math import sqrt` تابع جذر را از کتابخانه‌ی داخلی Python می‌آورد.
2. `cosine_similarity(left, right)` تابعی تعریف می‌کند که دو بردار می‌گیرد.
3. `zip(left, right)` عددهای هم‌جایگاه را جفت می‌کند؛ خط `dot_product` حاصل‌ضرب هر جفت را جمع می‌کند.
4. دو خط `magnitude_...` اندازه‌ی هر بردار را محاسبه می‌کنند.
5. `return` ضرب داخلی را بر حاصل‌ضرب اندازه‌ها تقسیم می‌کند؛ این فرمول cosine similarity است.
6. `query_vector` بردار پرسش toy است.
7. `document_vectors` دو بردار فرضی دارد. نام‌ها فقط label هستند و بردارها را دستی انتخاب کرده‌ایم.
8. حلقه نام و بردار هر سند را یکی‌یکی می‌گیرد.
9. `score` شباهت کسینوسی پرسش با آن بردار را حساب می‌کند.
10. `print` نام و امتیاز را با سه رقم اعشار نمایش می‌دهد.

## خروجی واقعی کاربر

```text
admissions: 0.994
dining: 0.110
```

کاربر درست نتیجه گرفت که `0.994` یعنی این دو بردار **در مثال، شباهت زیادی دارند**؛ این عدد احتمال ۹۹٫۴٪ درست‌بودن سند یا پاسخ نیست.

## محدودیت‌ها و خطاهای رایج

- بردارها دستی‌اند؛ `admissions` به‌طور واقعی از متن دانشگاهی encode نشده است.
- امتیاز بالای cosine similarity، حقیقت، رسمی‌بودن، به‌روز بودن یا citation را تضمین نمی‌کند.
- cosine similarity یک معیار مقایسه است، نه احتمال یا confidence score.
- بردار صفر باعث تقسیم بر صفر می‌شود؛ برنامه‌ی production باید ورودی را اعتبارسنجی کند.
- در جست‌وجوی واقعی، query و document باید با مدل و تنظیمات سازگار embed شوند؛ retrieval هم باید روی نمونه‌سؤال‌های واقعی ارزیابی شود.

## مرور پایان درس ۱۲

### خلاصه

- Token embedding برای ورودی داخلی مدل و به‌ازای token ID است.
- Text embedding یک پرسش یا متن را برای کارهایی مثل semantic retrieval نمایش می‌دهد.
- Cosine similarity جهت بردارها را مقایسه می‌کند؛ عدد بزرگ‌تر در این مثال یعنی بردارها هم‌جهت‌ترند.
- `0.994` احتمال صحت نیست و embedding به‌تنهایی منبع یا ارجاع محسوب نمی‌شود.
- کد تمرین فقط ریاضی بردارها را نشان می‌دهد؛ هیچ embedding واقعی تولید و هیچ API صدا نمی‌زند.

### خودآزمایی با پاسخ

1. چرا `admissions` امتیاز بیشتری گرفت؟ **چون بردارش به جهت query نزدیک‌تر انتخاب شده است.**
2. آیا `0.994` یعنی پاسخ ۹۹٫۴٪ درست است؟ **نه؛ فقط مقدار similarity این دو بردار toy است.**
3. آیا این مثال یک text embedding واقعی ساخت؟ **نه؛ بردارها دستی‌اند.**
4. آیا بردار similarity جای URL و منبع رسمی را می‌گیرد؟ **نه؛ metadata و ارجاع باید جدا حفظ شوند.**
