# درس ۶ — متغیر محیطی و header احراز هویت

## هدف

APIهای واقعی معمولاً برای احراز هویت به secret مثل API key نیاز دارند. secret نباید داخل کد، URL، Git یا چت نوشته شود. اول یاد می‌گیریم برنامه آن را از محیط بگیرد و header بسازد؛ در این درس **کلید واقعی لازم نیست**.

## مدل ذهنی

- **Environment variable** تنظیمی است که بیرون از فایل Python به برنامه می‌رسد.
- در PowerShell، `$env:AI_API_KEY = "..."` متغیر را برای همین ترمینال و برنامه‌هایی که از آن اجرا می‌شوند تنظیم می‌کند.
- `os.getenv("AI_API_KEY")` مقدار را در Python می‌خواند؛ اگر وجود نداشته باشد، `None` می‌دهد.
- Headerهایی مثل `Authorization: Bearer ...` معمولاً اطلاعات احراز هویت را حمل می‌کنند. نام و قالب دقیق header به مستندات همان provider بستگی دارد.

## مرحله‌ی ۱: ساخت متغیر آزمایشی

این دستور را در **ترمینال PowerShell داخلی VS Code** اجرا کن، نه داخل فایل Python یا پنجره‌ی `>>>`. این مقدار ساختگی است و API key واقعی نیست:

```powershell
$env:AI_API_KEY = 'demo-only-not-a-real-key'
```

اگر این شکل را نمی‌توانی paste کنی، PowerShell معادلش را هم می‌پذیرد:

```powershell
Set-Item -Path Env:AI_API_KEY -Value 'demo-only-not-a-real-key'
```

## مرحله‌ی ۲: خواندن و استفاده‌ی امن از آن

در VS Code فایلی به نام `auth_demo.py` بساز:

```python
import os

api_key = os.getenv("AI_API_KEY")

if not api_key:
    raise RuntimeError("AI_API_KEY is not set")

authorization_header = f"Bearer {api_key}"
scheme = authorization_header.partition(" ")[0]

print("Key loaded:", bool(api_key))
print("Authorization scheme:", scheme)
```

پیش از اجرا حدس بزن دو خط خروجی چه خواهند بود. بعد اجرا کن:

```powershell
.\.venv\Scripts\python.exe .\auth_demo.py
```

خروجی فقط وجود مقدار و نام scheme را نشان می‌دهد؛ **خود مقدار secret چاپ نمی‌شود**.

## توضیح کد

1. `import os` ابزار دسترسی به تنظیمات محیط سیستم‌عامل را می‌آورد.
2. `os.getenv("AI_API_KEY")` مقدار را می‌خواند، بدون این‌که مجبور باشیم آن را در فایل Python بنویسیم.
3. `if not api_key` نبودن مقدار را زود تشخیص می‌دهد؛ بهتر است به‌جای فرستادن درخواست ناقص، برنامه واضح متوقف شود.
4. `f"Bearer {api_key}"` نمونه‌ی ساخت مقدار یک header رایج است. در درخواست واقعی آن را در `Authorization` قرار می‌دهیم؛ هنوز هیچ درخواست authenticated نفرستاده‌ایم.
5. `partition(" ")[0]` فقط کلمه‌ی `Bearer` را جدا می‌کند تا secret را چاپ نکنیم.
6. `bool(api_key)` فقط True/False چاپ می‌کند، نه خود secret.

## نکات امنیتی

- هیچ‌وقت API key را در Python source، URL، screenshot، log یا Git commit نگذار.
- `.env` را هم باید از Git نادیده گرفت؛ بااین‌حال فایل `.env` متن ساده است و خودش رمزنگاری یا حفاظت از سیستم‌عامل نیست.
- متغیر PowerShell با `$env:` فقط در همان session فعال است. برای secret واقعی از روش مناسب محیط اجرا/مدیریت secrets استفاده می‌کنیم و مقدار واقعی را این‌جا به اشتراک نمی‌گذاری.
- بعضی سرویس‌ها به‌جای Bearer از نام header دیگری استفاده می‌کنند؛ مستندات provider ملاک است.

## تمرین

1. پیش از اجرا، خروجی دو print را حدس بزن.
2. مقدار ساختگی را از همان ترمینال پاک کن و دوباره برنامه را اجرا کن:

   ```powershell
   Remove-Item Env:AI_API_KEY
   ```

   این‌بار چرا برنامه پیش از ساخت header متوقف می‌شود؟
3. توضیح بده چرا `.gitignore` شامل `.env` است، اما `.env` به‌تنهایی یک secret manager امن نیست.

## نتیجه‌ی اجرای اول

با متغیر آزمایشی در PowerShell، خروجی این بود:

```text
Key loaded: True
Authorization scheme: Bearer
```

این نشان می‌دهد Python متغیر را خوانده و scheme را ساخته، بدون این‌که مقدار کلید چاپ شود. آزمایش حالتِ متغیر مفقود هنوز مانده است.

## مرور پایان درس ۶

### موضوع و مدل ذهنی

برنامه secret را از فایل Python نمی‌گیرد؛ آن را از environment همان process می‌خواند. اگر مقدار وجود نداشت، قبل از هر درخواست متوقف می‌شود. در درخواست‌های احراز هویت‌شده، مقدار معمولاً در header مناسب provider قرار می‌گیرد، نه در URL یا متن کد.

### فرمان‌ها و اجزای مهم

| فرمان/کد | چه می‌کند؟ |
|---|---|
| `$env:AI_API_KEY = 'demo-only-not-a-real-key'` | مقدار آزمایشی را در session فعلی PowerShell تنظیم می‌کند؛ در این درس کلید واقعی نیست. |
| `Set-Item -Path Env:AI_API_KEY -Value '...'` | راه جایگزین برای تنظیم همان متغیر در PowerShell است. |
| `os.getenv("AI_API_KEY")` | مقدار متغیر محیطی را می‌خواند؛ اگر نباشد `None` می‌دهد. |
| `if not api_key` | نبودن مقدار را زود تشخیص می‌دهد تا برنامه درخواست ناقص نفرستد. |
| `f"Bearer {api_key}"` | قالب رایج header احراز هویت را می‌سازد؛ provider واقعی ممکن است روش دیگری بخواهد. |
| `partition(" ")[0]` | فقط scheme یعنی `Bearer` را جدا می‌کند تا خود secret چاپ نشود. |
| `Remove-Item Env:AI_API_KEY` | متغیر را از همان session PowerShell حذف می‌کند. |

### خروجی‌هایی که خودت گرفتی

- وقتی مقدار آزمایشی حاضر بود: `Key loaded: True` و `Authorization scheme: Bearer`؛ خود مقدار چاپ نشد.
- پس از `Remove-Item`: برنامه عمداً با `RuntimeError: AI_API_KEY is not set` متوقف شد.
- هیچ API key واقعی ساخته، ارسال یا در Git ثبت نشد.

### نکات و اشتباه‌های رایج

- متغیر را در همان ترمینالی تنظیم کن که برنامه را از آن اجرا می‌کنی؛ ترمینال جدید session جداگانه‌ای است.
- دستور PowerShell را در ترمینال وارد کن، نه داخل فایل `.py` یا prompt پایتون `>>>`.
- `.env` و متغیر محیطی ابزار ساده‌ی تنظیم‌اند، نه رمزنگاری یا جایگزین کامل secret manager.
- نام و شکل header به مستندات سرویس بستگی دارد؛ Bearer یک الگوی رایج است، نه قانون همه‌ی APIها.

### خودآزمایی

1. وقتی `os.getenv` مقدار پیدا نمی‌کند، چه چیزی برمی‌گرداند؟
2. چرا `if not api_key` را قبل از ساخت header گذاشتیم؟
3. چرا چاپ‌کردن خود `api_key` یا گذاشتنش در URL خطرناک است؟
4. آیا `Key loaded: True` به معنی ارسال‌شدن کلید به API است؟

### پاسخ سؤال اول

اگر متغیر تعریف نشده باشد، `os.getenv("AI_API_KEY")` مقدار `None` برمی‌گرداند. شرط `if not api_key` این حالت را می‌گیرد و `RuntimeError` را بالا می‌برد تا برنامه بدون credential لازم ادامه ندهد یا درخواست ناقص نفرستد.
