# درس ۲ — مجموعه‌ها و query parameter در API

در درس قبل، مسیر `/todos/2` یک رکورد را برگرداند؛ پاسخ JSON آن با `{...}` شروع می‌شد و در Python به `dict` تبدیل شد.

حالا از یک **مجموعه** داده سؤال می‌پرسیم و آن را با پارامتر `userId` فیلتر می‌کنیم:

```text
https://jsonplaceholder.typicode.com/todos?userId=1
```

- `/todos` بخش مسیر است و می‌گوید مجموعه‌ی todoها را می‌خواهیم.
- `?userId=1` یک query parameter است و مجموعه را فیلتر می‌کند؛ علامت `?` شروع query string است.
- پاسخ این بار JSON array است: `[...]`؛ پس در Python به `list` تبدیل می‌شود، نه `dict`.

### فرق این دو URL

| URL | منظور | شکل پاسخ |
|---|---|---|
| `/todos/2` | خودِ کارِ شماره‌ی ۲ (یعنی `id=2`) | یک object، در Python یک `dict` |
| `/todos?userId=2` | فهرست کارهای متعلق به کاربر شماره‌ی ۲ (یعنی `userId=2`) | چند object، در Python یک `list` از `dict`ها |

در خروجی قبلی از `/todos/2` دیدیم `id` برابر ۲ بود، اما `userId` برابر ۱. پس عدد ۲ در این دو URL معنی یکسانی ندارد: در مسیر، شناسه‌ی خودِ todo است؛ در query، شناسه‌ی صاحب todoهاست.

## تمرین

در `api_lesson.py`، کد را موقتاً با این نسخه عوض کن:

```python
import json
from urllib.request import urlopen

url = "https://jsonplaceholder.typicode.com/todos?userId=1"

with urlopen(url, timeout=10) as response:
    print("HTTP status:", response.status)
    body = response.read().decode("utf-8")

todos = json.loads(body)

print("Python type:", type(todos).__name__)
print("Number of records:", len(todos))
print("First title:", todos[0]["title"])
print("First completed:", todos[0]["completed"])
```

اجرا:

```powershell
.\.venv\Scripts\python.exe .\api_lesson.py
```

انتظار داریم status برابر 200 و نوع Python برابر `list` باشد. این API نمونه معمولاً برای `userId=1` بیست مورد برمی‌گرداند.

## تمرین کوتاه

`userId=1` را به `userId=2` تغییر بده و اجرا کن. عنوان اولین مورد را مقایسه کن. بعد با زبان خودت توضیح بده:

1. فرق `/todos/2` با `/todos?userId=2` چیست؟
2. چرا برای رکورد قبلی از `todo["title"]` استفاده کردیم، ولی این‌جا اول باید `todos[0]` را گرفت؟

این سرویس فقط داده‌ی ساختگی/آزمایشی است؛ بعداً همین الگو را برای فهم APIهای واقعی به کار می‌بریم.

## مرور پایان درس ۲

### موضوع

تفاوت مسیرِ شناسایی یک رکورد با query parameter فیلترکننده‌ی یک مجموعه، و این‌که شکل JSON نوع داده‌ی Python را تعیین می‌کند.

### نکته‌ها و کدهای مهم

| کد/ساختار | معنی |
|---|---|
| `/todos/2` | مسیر شامل شناسه‌ی خود رکورد است: `id=2`؛ پاسخ یک object و در Python یک `dict` است. |
| `/todos?userId=2` | `?` شروع query string است؛ `userId=2` مجموعه را بر اساس شناسه‌ی صاحبش فیلتر می‌کند. پاسخ یک array و در Python یک `list` است. |
| `json.loads(body)` | JSON object را به `dict` و JSON array را به `list` تبدیل می‌کند. |
| `len(todos)` | تعداد رکوردهای فهرست را می‌دهد. |
| `todos[0]` | اولین رکورد فهرست را می‌دهد؛ index فهرست از صفر شروع می‌شود. |
| `todos[0]["title"]` | از اولین dictionary، فیلد `title` را می‌خواند. |

### نتیجه‌ای که خودت دیدی

`/todos?userId=2` یک `list` با ۲۰ رکورد برگرداند. اولین رکورد `id=21` و `userId=2` داشت؛ پس ID خود todo با ID کاربر یکی نیست.

### خودآزمایی

1. کدام URL یک todo مشخص را می‌خواهد و کدام یک مجموعه را فیلتر می‌کند؟
2. چرا برای `todos` از `todos[0]["title"]` استفاده می‌کنیم، نه `todos["title"]`؟
3. اگر JSON پاسخ با `[` شروع شود، انتظار داریم Python چه نوعی بسازد؟
