# درس ۴ — POST، body و header

## هدف

تا این‌جا با `GET` داده خواندیم. حالا یاد می‌گیریم برنامه چطور یک داده‌ی JSON را با `POST` برای یک API می‌فرستد و header چه اطلاعاتی درباره‌ی آن درخواست می‌دهد. این الگو در بسیاری از APIهای LLM هم دیده می‌شود.

## مدل ذهنی

- `GET`: معمولاً برای خواندن داده.
- `POST`: معمولاً برای فرستادن داده یا ایجاد/اجرای چیزی در سرویس.
- **body**: داده‌ی اصلی درخواست؛ در این مثال یک JSON object.
- **header**: توضیح درباره‌ی درخواست، مثل نوع body. `Content-Type: application/json` می‌گوید body را JSON فرستاده‌ایم.

در این درس از JSONPlaceholder استفاده می‌کنیم. این سرویس پاسخ ایجاد رکورد را شبیه‌سازی می‌کند؛ رکورد واقعی را دائمی ذخیره نمی‌کند.

## کد

در `api_lesson.py` این کد را بگذار. قبل از اجرا، حدس بزن status، عنوان و شناسه‌ی برگشتی چه خواهند بود.

```python
import json
from urllib.request import Request, urlopen

url = "https://jsonplaceholder.typicode.com/todos"
payload = {
    "title": "Learn API POST",
    "completed": False,
    "userId": 1,
}

body = json.dumps(payload).encode("utf-8")
request = Request(
    url,
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urlopen(request, timeout=10) as response:
    print("HTTP status:", response.status)
    response_body = response.read().decode("utf-8")

created = json.loads(response_body)
print("Created ID:", created["id"])
print("Title:", created["title"])
print("Owner ID:", created["userId"])
```

اجرا در PowerShell داخلی VS Code:

```powershell
.\.venv\Scripts\python.exe .\api_lesson.py
```

معمولاً پاسخ آزمایشی status برابر `201` دارد و یک `id` جدید شبیه `201` می‌دهد. پاسخ JSON را بررسی کن؛ ممکن است ترتیب فیلدها یا جزئیات نمایش فرق کند.

## توضیح بخش‌به‌بخش

1. `payload` یک dictionary معمولی Python است؛ هنوز JSON نیست.
2. `json.dumps(payload)` آن را به متن JSON تبدیل می‌کند.
3. `.encode("utf-8")` متن را به bytes تبدیل می‌کند تا در body درخواست فرستاده شود.
4. `Request(...)` درخواست سفارشی می‌سازد: آدرس، body، headers و method.
5. `headers={"Content-Type": "application/json"}` نوع body را به سرویس اعلام می‌کند.
6. `method="POST"` روشن می‌کند که داده می‌فرستیم؛ در مقابل، درخواست‌های قبلی GET برای خواندن بودند.
7. `urlopen(request, timeout=10)` درخواست را می‌فرستد و پاسخ را می‌دهد.
8. response body را دوباره با `json.loads` به dictionary تبدیل می‌کنیم تا فیلد `id` و `title` را بخوانیم.

**نکته‌ی امنیتی:** در این مثال کلید API نداریم. وقتی به API نیازمند احراز هویت برسیم، secret را در URL یا کد ثابت نمی‌گذاریم؛ روش امن را جداگانه یاد می‌گیریم.

## تمرین

1. پیش از اجرا حدس بزن چرا `payload` را هم `json.dumps` و هم `encode` می‌کنیم.
2. فقط عنوان را به نام دیگری تغییر بده و اجرا کن؛ بررسی کن response همان عنوان را برگرداند.
3. فرق body و header را با یک جمله توضیح بده.

## مرور پایان درس

### مفهوم اصلی

در درخواست `POST`، برنامه داده را در **body** می‌فرستد. header می‌گوید این body چه قالبی دارد. پس دیکشنری Python باید اول به JSON و سپس به bytes تبدیل شود:

```text
Python dict → json.dumps → JSON string → encode("utf-8") → request body bytes
```

پاسخ هم برعکس خوانده می‌شود:

```text
response bytes → decode("utf-8") → JSON text → json.loads → Python dict
```

### کدها و اجزای مهم

| کد/ساختار | چه می‌کند؟ |
|---|---|
| `Request(url, ...)` | درخواست HTTP سفارشی می‌سازد. |
| `method="POST"` | نوع درخواست را POST قرار می‌دهد؛ معمولاً برای فرستادن داده/ساختن منبع. |
| `data=body` | body بایتی درخواست را تعیین می‌کند. |
| `headers={"Content-Type": "application/json"}` | به سرور اعلام می‌کند body از نوع JSON است. این header خودِ داده نیست. |
| `json.dumps(payload)` | دیکشنری Python را به متن JSON تبدیل می‌کند. |
| `.encode("utf-8")` | متن JSON را به bytes تبدیل می‌کند تا در درخواست HTTP فرستاده شود. **خود `encode` دیکشنری را تبدیل نمی‌کند.** |
| `response.status` | status HTTP پاسخ را می‌خواند؛ `201` معمولاً به معنی Created است. |
| `json.loads(response_body)` | متن JSON پاسخ را دوباره به داده‌ی Python تبدیل می‌کند. |
| `\.venv\Scripts\python.exe .\api_lesson.py` | اسکریپت را با Python محیط مجازی اجرا می‌کند. |

### اصلاح ظریف پاسخ تو

حدست درباره‌ی دیکشنری درست بود، اما ترتیب دقیق این است: `json.dumps` دیکشنری را به **متن** تبدیل می‌کند؛ بعد `encode` آن متن را به **bytes** تبدیل می‌کند. این bytes در body درخواست قرار می‌گیرند.

### نتیجه‌ای که خودت گرفتی

- status برابر `201` بود؛ سرویس می‌گوید درخواست ایجاد منبع را شبیه‌سازی کرده است.
- ID آزمایشی `201` برگشت.
- `Title` و `Owner ID` با مقادیری که فرستادیم، یعنی `Learn API POST` و `1`، مطابقت داشتند.
- JSONPlaceholder این تغییر را واقعاً به‌صورت دائمی ذخیره نمی‌کند.

### خودآزمایی کوتاه

1. فرق `json.dumps(payload)` با `.encode("utf-8")` چیست؟
2. کدام‌یک داده‌ی اصلی را حمل می‌کند: body یا header؟ header چه چیزی را توضیح می‌دهد؟
3. آیا پاسخ موفق این API آزمایشی یعنی رکورد برای همیشه ذخیره شده است؟

**پاسخ تو به سؤال اول:** مسیر اصلی را درست گفتی: دیکشنری به JSON text و بعد به bytes تبدیل می‌شود. دقیق‌تر از نظر نوع Python: `json.dumps(payload)` یک `str` برمی‌گرداند که محتوایش JSON است؛ `.encode("utf-8")` آن را به `bytes` تبدیل می‌کند. JSON خودش یک قالب متنی است، نه یک نوع جداگانه‌ی Python.
