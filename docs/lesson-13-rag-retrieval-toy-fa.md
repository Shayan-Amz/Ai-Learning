# درس ۱۳ — بازیابی toy و نگه‌داشتن metadata منبع

## هدف و منبع

این مثال از الگوی Retrieve در [Phase 11, Lesson 06: RAG](https://github.com/rohitg00/ai-engineering-from-scratch/tree/main/phases/11-llm-engineering/06-rag) الهام گرفته است. فقط بازیابی یک سند را انجام می‌دهیم؛ هنوز prompt را augment نمی‌کنیم و LLM پاسخ تولید نمی‌کند. بردارها دستی‌اند و URLها نمونه‌اند.

## مدل ذهنی

دو مجموعه را با یک شناسه به هم وصل می‌کنیم:

- `document_vectors`: برای هر `doc_id` بردار سند را نگه می‌دارد.
- `documents`: برای همان `doc_id` عنوان، URL و متن را نگه می‌دارد.

ابتدا امتیاز شباهت را حساب می‌کنیم و بهترین `doc_id` را پیدا می‌کنیم. سپس همان ID را برای بازیابی metadata به کار می‌بریم. بردار خودش URL یا citation نیست.

## کد اجرایی

فایل `rag_retrieval_toy.py` با کد ASCII:

```python
from math import sqrt


def cosine_similarity(left, right):
    dot_product = sum(a * b for a, b in zip(left, right))
    magnitude_left = sqrt(sum(value * value for value in left))
    magnitude_right = sqrt(sum(value * value for value in right))
    return dot_product / (magnitude_left * magnitude_right)


documents = {
    "admissions": {
        "title": "Admissions page (demo)",
        "url": "https://university.example/admissions",
        "text": "Applicants need an English test score.",
    },
    "fees": {
        "title": "Tuition page (demo)",
        "url": "https://university.example/tuition",
        "text": "Tuition is listed by program.",
    },
}

document_vectors = {
    "admissions": [0.9, 0.1],
    "fees": [0.1, 0.9],
}

query_vector = [1.0, 0.0]
scored_documents = []

for doc_id, vector in document_vectors.items():
    score = cosine_similarity(query_vector, vector)
    scored_documents.append((score, doc_id))

best = max(scored_documents, key=lambda result: result[0])
best_score, best_id = best
best_document = documents[best_id]

print("Title:", best_document["title"])
print(f"Score: {best_score:.3f}")
print("URL:", best_document["url"])
print("Text:", best_document["text"])
```

اجرا از PowerShell:

```powershell
.\.venv\Scripts\python.exe .\rag_retrieval_toy.py
```

## توضیح ساده و خط‌به‌خط

1. `sqrt` برای محاسبه‌ی جذر در تابع شباهت لازم است.
2. `cosine_similarity` دو بردار را می‌گیرد و شباهت‌شان را برمی‌گرداند.
3. `documents` شامل metadata هر سند است: عنوان، URL و متن. دامنه‌ی `.example` عمداً ساختگی است.
4. `document_vectors` بردار toy هر سند را با همان شناسه نگه می‌دارد.
5. `query_vector` بردار toy پرسش است؛ این‌جا دستی ساخته شده و از متن واقعی به دست نیامده.
6. `scored_documents = []` فهرست نتیجه‌های امتیازدار را آماده می‌کند.
7. حلقه هر شناسه و بردار سند را برمی‌دارد، با query مقایسه می‌کند و زوج `(score, doc_id)` را ذخیره می‌کند.
8. `max(..., key=lambda result: result[0])` زوجی را انتخاب می‌کند که عضو اولش، یعنی امتیاز، بزرگ‌تر است.
9. `best_score, best_id = best` زوج را به دو متغیر جدا باز می‌کند.
10. `documents[best_id]` امتیاز را محاسبه نمی‌کند؛ فقط با شناسه‌ی بهترین نتیجه، عنوان/URL/متن را از metadata برمی‌دارد.
11. چهار `print` نتیجه‌ی بازیابی و اطلاعات همان سند را نمایش می‌دهند.

## نتیجه‌ی واقعی کاربر

خروجی، سند پذیرش نمونه را برگرداند:

```text
Title: Admissions page (demo)
Score: 0.994
URL: https://university.example/admissions
Text: Applicants need an English test score.
```

کاربر درست تشخیص داد که URL از `documents` می‌آید. همچنین روشن شد که `max(...)` بالاترین امتیاز را انتخاب می‌کند و `documents[best_id]` metadata همان نتیجه را می‌گیرد.

## محدودیت‌ها و مرز واقعی RAG

- این کد سند واقعی را embed نکرده و بردارهایش دستی‌اند؛ پس semantic search واقعی انجام نمی‌دهد.
- URLها به دامنه‌ی نمونه‌ی `.example` اشاره دارند و منبع رسمی نیستند.
- این کد فقط مرحله‌ی **Retrieve** را نشان می‌دهد. جریان کامل RAG معمولاً query → retrieve → augment prompt → generate است.
- در پروژه‌ی واقعی، هر chunk باید شناسه و metadata قابل‌ردیابی داشته باشد؛ پس از بازیابی باید متن و منبع آن را بررسی کرد. similarity به‌تنهایی حقیقت را ثابت نمی‌کند.

## مرور پایان درس ۱۳

### خلاصه

- `max(scored_documents, key=lambda result: result[0])` بهترین نتیجه را بر اساس امتیاز انتخاب می‌کند.
- `best_id` پل بین بردار نتیجه و metadata است.
- `documents[best_id]` عنوان، متن و URL را می‌گیرد؛ `document_vectors` فقط بردارها را دارد.
- metadata منبع را جدا نگه می‌داریم تا پاسخ بتواند به منبع واقعی ارجاع دهد.
- این مثال toy فقط Retrieve است؛ embedding و generation واقعی ندارد.

### خودآزمایی با پاسخ

1. کدام خط بالاترین similarity را پیدا می‌کند؟ **خط `max(...)`.**
2. `best_document = documents[best_id]` چه می‌کند؟ **metadata سندی را که ID آن برنده شده lookup می‌کند.**
3. URL در بردار ذخیره شده؟ **نه؛ در `documents` و کنار metadata است.**
4. آیا نتیجه‌ی toy ثابت می‌کند صفحه‌ی admissions منبع واقعی یا معتبر است؟ **نه؛ داده و URL صرفاً نمونه‌اند.**
