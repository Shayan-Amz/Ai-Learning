# درس ۱۰ — شناسه‌ی token و نگاشت واژگان

## هدف و منبع

این تمرین، بخش بعدی از ایده‌های [Phase 10, Lesson 01: Tokenizers](https://github.com/rohitg00/ai-engineering-from-scratch/tree/main/phases/10-llms-from-scratch/01-tokenizers) را با یک واژگان toy نشان می‌دهد. کد و خروجی ASCII هستند تا در PowerShell خوانا بمانند.

## مدل ذهنی

Tokenizer قطعه‌های متن را به شناسه‌های عددی تبدیل می‌کند. خود شناسه عددی فقط یک **index/برچسب** در واژگان است؛ `3` ذاتاً معنادارتر یا بزرگ‌تر از `1` نیست. مدل واقعی برای هر شناسه یک بردار آموخته‌شده دارد، پس tokenizer و مدل باید دقیقاً از همان نگاشت سازگار استفاده کنند.

## کد اجرایی

فایل `token_ids_demo.py`:

```python
vocab = {
    "abab": 0,
    "ab": 1,
    "a": 2,
    "c": 3,
}

tokens = ["ab", "a", "c"]
token_ids = [vocab[token] for token in tokens]

id_to_token = {
    token_id: token
    for token, token_id in vocab.items()
}

decoded_tokens = [id_to_token[token_id] for token_id in token_ids]

print("Tokens:", tokens)
print("Token IDs:", token_ids)
print("Decoded text:", "".join(decoded_tokens))
```

اجرا از PowerShell:

```powershell
.\.venv\Scripts\python.exe .\token_ids_demo.py
```

## توضیح بخش‌به‌بخش

- `vocab` از قطعه‌ی متنی به ID نگاشت می‌کند.
- `vocab[token]` ID همان قطعه را می‌خواند؛ list comprehension این کار را برای همه‌ی قطعه‌ها انجام می‌دهد.
- `id_to_token` همان نگاشت را برعکس می‌کند.
- با lookup معکوس، IDها را به قطعه‌ها برمی‌گردانیم و با `"".join(...)` این مثال ساده را به `abac` می‌چسبانیم.

## آزمایش تغییر شناسه‌ها

کاربر ابتدا خروجی `[1, 2, 3]` و `abac` را گرفت. سپس `ab` و `c` را در `vocab` جابه‌جا کرد:

```python
vocab = {
    "abab": 0,
    "ab": 3,
    "a": 2,
    "c": 1,
}
```

خروجی دوم او:

```text
Tokens: ['ab', 'a', 'c']
Token IDs: [3, 2, 1]
Decoded text: abac
```

این نشان می‌دهد encoder و decoder تا وقتی از یک نگاشت مشترک استفاده کنند، قطعه‌ها را round-trip می‌کنند. **در مدل واقعی نباید IDهای tokenizer را خودسرانه عوض کرد**: هر ID به ردیف معینی در embedding table مدل وصل است.

## محدودیت toy example

واژگان دستی بالا tokenizer کامل یا واژگان provider نیست؛ متن را هم segment نمی‌کند، فقط قطعه‌هایی را که از قبل در فهرست `tokens` داده‌ایم lookup می‌کند. Tokenizer واقعی باید مرزها، نویسه‌ها/بایت‌ها، قواعد normalization و شناسه‌های آموزش‌دیده‌ی همان مدل را رعایت کند.

## مرور پایان درس ۱۰

### خلاصه

- متن به قطعه‌ها می‌رسد؛ tokenizer برای هر قطعه ID واژگان را پیدا می‌کند.
- IDها شماره‌گذاری دلخواه درون یک واژگان ثابت‌اند، نه نمره یا درجه‌ی معنی.
- در toy مثال، تغییر نگاشت IDها، `Token IDs` را عوض کرد ولی decode با همان نگاشت جدید دوباره `abac` ساخت.
- در مدل واقعی، tokenizer و embedding table باید هماهنگ بمانند؛ شناسه‌های toy را نمی‌توان جایگزین کرد.

### کدها و ساختارهای مهم

| ساختار | کاربرد |
|---|---|
| `vocab[token]` | lookup شناسه‌ی یک قطعه |
| `[vocab[token] for token in tokens]` | ساخت فهرست IDها از فهرست قطعه‌ها |
| `id_to_token` | نگاشت معکوس از ID به متن |
| `"".join(decoded_tokens)` | چسباندن قطعه‌های نمونه برای بازسازی رشته |

### خودآزمایی با پاسخ

1. آیا ID برابر `3` ذاتاً معنای بیشتری از `1` دارد؟ **نه؛ فقط شناسه‌ای در واژگان است.**
2. چرا پس از جابه‌جایی IDها متن همچنان `abac` شد؟ **چون نگاشت معکوس هم از واژگان جابه‌جا‌شده ساخته شد.**
3. آیا می‌توان همین IDها را به هر مدل واقعی داد؟ **نه؛ باید با tokenizer و embedding همان مدل سازگار باشد.**
