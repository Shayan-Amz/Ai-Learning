# درس ۵ — اعتبارسنجی داده‌ی API با Pydantic

## هدف

JSON دریافتی از API را مستقیماً و بدون بررسی مصرف نکنیم. با یک schema تعریف می‌کنیم چه فیلدهایی لازم‌اند و هرکدام چه نوعی باید داشته باشند. Pydantic داده‌ی ورودی را بررسی می‌کند و در صورت مشکل، `ValidationError` می‌دهد.

> اعتبارسنجی ساختار و نوع، تضمین نمی‌کند که محتوای منبع از نظر واقعی درست یا به‌روز باشد؛ فقط شکل داده را کنترل می‌کند.

## ۱. نصب در محیط مجازی

این دستور را در ترمینال VS Code و پوشه‌ی تمرین اجرا کن:

```powershell
.\.venv\Scripts\python.exe -m pip install pydantic
```

به این دلیل از Python داخل `.venv` استفاده می‌کنیم که Pydantic در محیط پروژه نصب شود، نه برای تمام Python سیستم.

## ۲. کد کامل با schema

در `api_lesson.py` از این نمونه استفاده کن:

```python
import json
from urllib.request import urlopen

from pydantic import BaseModel, ValidationError


class Todo(BaseModel):
    userId: int
    id: int
    title: str
    completed: bool


url = "https://jsonplaceholder.typicode.com/todos/2"

with urlopen(url, timeout=10) as response:
    body = response.read().decode("utf-8")

data = json.loads(body)
todo = Todo.model_validate(data)

print("Validated todo:", todo)
print("Title:", todo.title)
print("Completed:", todo.completed)

invalid_data = {
    "userId": 1,
    "id": 99,
    "title": "This payload is missing completed",
}

try:
    Todo.model_validate(invalid_data)
except ValidationError as error:
    print("Invalid data was rejected:")
    print(error)
```

اجرا:

```powershell
.\.venv\Scripts\python.exe .\api_lesson.py
```

## توضیح کد

1. `BaseModel` کلاس پایه‌ای است که از روی آن schema می‌سازیم.
2. `class Todo(BaseModel)` می‌گوید پاسخ مورد انتظار یک Todo با فیلدهای مشخص است.
3. `userId: int`, `id: int`, `title: str`, `completed: bool` نام و نوع مورد انتظار هر فیلدند.
4. `json.loads(body)` متن JSON را به داده‌ی معمولی Python تبدیل می‌کند؛ این مرحله به‌تنهایی schema را بررسی نمی‌کند.
5. `Todo.model_validate(data)` داده را با schema تطبیق می‌دهد و یک object از نوع `Todo` برمی‌گرداند.
6. پس از اعتبارسنجی، به‌جای `todo["title"]` می‌توانیم از `todo.title` استفاده کنیم.
7. `invalid_data` عمداً فیلد `completed` را ندارد؛ چون آن فیلد در مدل اجباری است، Pydantic یک `ValidationError` ایجاد می‌کند.
8. `except ValidationError` خطای اعتبارسنجی را می‌گیرد تا برنامه به‌جای مصرف بی‌صدای داده‌ی ناقص، مشکل را آشکار کند.

## تمرین

1. در `invalid_data` کلید `completed` را با مقدار `False` اضافه کن و دوباره اجرا کن. آیا دیگر خطای «field required» می‌بینی؟
2. مقدار `title` را از رشته به عدد تغییر بده و ببین Pydantic چه می‌کند.
3. با زبان خودت توضیح بده فرق `json.loads` و `Todo.model_validate` چیست.

## رفع خطای رایج

اگر `NameError: name 'BaseModel' is not defined` دیدی، یعنی `BaseModel` قبل از تعریف `class Todo` وارد فایل نشده است. مطمئن شو این خط در ابتدای همان فایل و بالاتر از `class Todo` وجود دارد:

```python
from pydantic import BaseModel, ValidationError
```

نصب package به‌تنهایی نام‌هایش را داخل هر فایل Python تعریف نمی‌کند؛ `import` باید در همان فایل باشد.

اگر `NameError: name 'data' is not defined` دیدی، قبل از `Todo.model_validate(data)` مطمئن شو پاسخ را parse کرده‌ای:

```python
data = json.loads(body)
todo = Todo.model_validate(data)
```

اینجا `body` متن JSON است، `data` دیکشنری Python، و `todo` نمونه‌ی اعتبارسنجی‌شده‌ی `Todo` است. این دستورها باید بعد از خواندن `body` و به همین ترتیب اجرا شوند.

اگر `NameError: name 'url' is not defined` دیدی، قبل از `urlopen(url, ...)` این متغیر را تعریف کن؛ اگر چند NameError پشت‌سرهم می‌بینی، احتمالاً فقط تکه‌هایی از اسکریپت را جایگزین کرده‌ای. ترتیب کامل نمونه در بالا از importها و تعریف `Todo` شروع می‌شود و بعد `url`، دریافت پاسخ، parse و validation را انجام می‌دهد.

## مرور پایان درس ۵

### موضوع و مدل ذهنی

API یک پاسخ JSON می‌دهد؛ اول آن متن را parse می‌کنیم، بعد schema می‌سنجد آیا داده شکل و فیلدهای مورد انتظار را دارد:

```text
HTTP response → body text → json.loads → Python dict → Todo.model_validate → Todo object
```

اعتبارسنجی ساختار، صحت واقعی یا به‌روز بودن منبع را تضمین نمی‌کند.

### دستورها و اجزای مهم

| کد/ساختار | چه می‌کند؟ |
|---|---|
| `python.exe -m pip install pydantic` | Pydantic را برای همان مفسر نصب می‌کند؛ با مسیر `.venv` package فقط به محیط پروژه اضافه می‌شود. |
| `class Todo(BaseModel)` | مدل/schema مورد انتظار را تعریف می‌کند. |
| `userId: int`, `title: str`, ... | فیلدهای الزامی و نوع‌های مورد انتظار را مشخص می‌کنند. |
| `json.loads(body)` | متن JSON را به dictionary Python تبدیل می‌کند؛ به‌تنهایی schema را اعتبارسنجی نمی‌کند. |
| `Todo.model_validate(data)` | داده را با schema تطبیق می‌دهد و در صورت موفقیت شیء `Todo` می‌سازد. |
| `todo.title` | به فیلدهای شیء اعتبارسنجی‌شده دسترسی می‌دهد. |
| `ValidationError` | خطای فیلدِ ناقص یا نامعتبر را می‌گیرد تا برنامه بتواند آن را آگاهانه مدیریت کند. |

### نتیجه‌ای که خودت گرفتی

- پاسخ واقعی به شیء `Todo` تبدیل شد: `id=2`، عنوان `quis ut nam facilis et officia qui` و `completed=False`.
- payload آزمایشی که فیلد `completed` را نداشت رد شد.
- متن خطا دقیقاً گفت `completed` الزامی است (`Field required`).
- Pydantic نسخه‌ی 2.13.5 داخل `.venv` نصب شد؛ packageهای سراسری Python تغییر نکردند.

### خطاهای رایجی که دیدیم

- `BaseModel is not defined`: import از `pydantic` جا افتاده یا پایین‌تر از تعریف کلاس است.
- `data is not defined`: باید `data = json.loads(body)` پیش از `model_validate` اجرا شود.
- `url is not defined`: باید URL را قبل از `urlopen(url, ...)` تعریف کرد.
- معمولاً این خطاها با بررسی ترتیب اجرا حل می‌شوند: import → schema → URL/request → body → data → validation.

### خودآزمایی

1. فرق `json.loads(body)` و `Todo.model_validate(data)` چیست؟
2. چرا payload بدون `completed` رد شد؟
3. اگر Pydantic داده را قبول کند، آیا ثابت می‌شود اطلاعاتش از نظر واقعی درست است؟

**پاسخ تو به سؤال اول درست بود:** `json.loads` متن JSON را به داده‌ی Python تبدیل می‌کند؛ `Todo.model_validate` همان داده را با مدل می‌سنجد و در صورت موفقیت شیء `Todo` می‌سازد.
