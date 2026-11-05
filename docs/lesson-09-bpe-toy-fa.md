# درس ۹ — ادغام جفت‌های پرتکرار با BPE

## هدف و منبع

این تمرین کوچک از ایده‌ی BPE در [Phase 10, Lesson 01: Tokenizers](https://github.com/rohitg00/ai-engineering-from-scratch/tree/main/phases/10-llms-from-scratch/01-tokenizers) الهام گرفته است. می‌خواهیم ببینیم جفت‌های مجاور چطور با شمارش و ادغام ساخته می‌شوند؛ این پیاده‌سازی toy است، نه tokenizer واقعی یک مدل.

## مدل ذهنی

در نسخه‌ی آموزشی BPE، از نمادهای کوچک شروع می‌کنیم. در هر دور، جفت‌های **مجاور** را در corpus می‌شماریم، پرتکرارترین جفت را انتخاب می‌کنیم و همه‌ی رخدادهای غیرهم‌پوشانش را به یک نماد تازه تبدیل می‌کنیم. سپس از روی توالی‌های تازه دوباره می‌شماریم.

الگوریتم بر اساس تکرار در داده تصمیم می‌گیرد، نه معنادار بودن زبانی. ممکن است در یک corpus toy، رشته‌ی `abab` به یک نماد تبدیل شود؛ این به‌تنهایی به معنی یک واحد معنایی نیست.

## کد اجرایی

فایل `bpe_toy.py` را با این کد ASCII بساز:

```python
from collections import Counter

corpus = ["abab", "abab", "abac"]
sequences = [list(word) for word in corpus]


def count_pairs(sequences):
    counts = Counter()

    for symbols in sequences:
        counts.update(zip(symbols, symbols[1:]))

    return counts


def merge_pair(sequence, pair):
    merged = []
    i = 0

    while i < len(sequence):
        if (
            i + 1 < len(sequence)
            and (sequence[i], sequence[i + 1]) == pair
        ):
            merged.append(sequence[i] + sequence[i + 1])
            i += 2
        else:
            merged.append(sequence[i])
            i += 1

    return merged


for step in range(2):
    pair_counts = count_pairs(sequences)
    pair, frequency = pair_counts.most_common(1)[0]

    print(f"Step {step + 1}: pair {pair}, frequency {frequency}")
    sequences = [merge_pair(sequence, pair) for sequence in sequences]
    print("Sequences:", sequences)
```

اجرا در PowerShell:

```powershell
.\.venv\Scripts\python.exe .\bpe_toy.py
```

## توضیح بخش‌به‌بخش

- `corpus` سه نمونه دارد: دو بار `abab` و یک بار `abac`.
- `list(word)` در مثال ساده‌ی ما هر رشته را به نویسه‌هایش می‌شکند؛ مثلاً `abab` می‌شود `[a, b, a, b]`.
- `zip(symbols, symbols[1:])` جفت‌های مجاور را می‌سازد. از `[a, b, a, b]` می‌گیریم `(a,b)`, `(b,a)`, `(a,b)`.
- `Counter` دفعات جفت‌ها را جمع می‌کند؛ `most_common(1)[0]` جفت پرتکرار و تعدادش را می‌گیرد.
- `merge_pair` از چپ به راست می‌رود. وقتی جفت هدف را دید، آن را به رشته‌ی ترکیبی تبدیل می‌کند و از دو عضو رد می‌شود تا همان دو عضو دوباره مصرف نشوند.
- `range(2)` فقط دو دور ادغام اجرا می‌کند؛ BPE این‌جا دنبال نقطه‌ای نمی‌گردد که یک واژه «معنادار» شود.

## ردگیری خروجی واقعی کاربر

ابتدا، در هر `abab` دو `(a,b)` وجود دارد؛ چون `abab` دو بار آمده، این `4` رخداد است. `abac` هم یک `(a,b)` دارد. پس مجموعاً `(a,b)` پنج بار است و دور اول آن را ادغام می‌کند.

پس از دور اول:

```text
[a, b, a, b] -> [ab, ab]
[a, b, a, b] -> [ab, ab]
[a, b, a, c] -> [ab, a, c]
```

در دور دوم، هرکدام از دو `[ab, ab]` یک `(ab,ab)` دارند؛ بنابراین تعداد آن جفت `2` است. توالی `[ab, a, c]` سه نماد دارد و دو جفت مجاورش `(ab,a)` و `(a,c)` هستند.

خروجی‌ای که کاربر گرفت:

```text
Step 1: pair ('a', 'b'), frequency 5
Sequences: [['ab', 'ab'], ['ab', 'ab'], ['ab', 'a', 'c']]
Step 2: pair ('ab', 'ab'), frequency 2
Sequences: [['abab'], ['abab'], ['ab', 'a', 'c']]
```

کاربر درست تشخیص داد که یک توالی با چهار نماد سه جفت مجاور دارد؛ پس توالی سه‌نمادی `[ab, a, c]` دو جفت دارد.

## محدودیت این مثال

این toy از نویسه‌ها شروع می‌کند تا محاسبه ساده بماند. برخی tokenizerهای واقعی BPE، از جمله byte-level BPE، از بایت‌ها شروع می‌کنند؛ الگوریتم‌های tokenizer همگی یکسان نیستند. این اسکریپت تعداد token هیچ provider یا مدل واقعی را حساب نمی‌کند.

## مرور پایان درس ۹

### خلاصه

- BPE جفت‌های مجاور را بر اساس تکرار در corpus ادغام می‌کند؛ معیارش «معنادار بودن کلمه» نیست.
- بعد از هر ادغام، توالی‌ها عوض می‌شوند و شمارش دور بعد از نو انجام می‌شود.
- در توالی `n` نمادی، `n - 1` جفت مجاور داریم.
- `Counter`, `zip`, `most_common` و `merge_pair` به‌ترتیب برای شمارش، ساخت جفت‌ها، انتخاب پرتکرارترین جفت و ادغام آن به کار رفتند.
- این پیاده‌سازی toy است و معادل tokenizer مدل واقعی نیست.

### خطاهای رایج

1. فرض این‌که BPE تا رسیدن به یک «کلمه‌ی معنادار» ادامه می‌دهد.
2. شمردن `ab` به‌عنوان دو نماد پس از ادغام؛ در توالی تازه `ab` یک عضو است.
3. یکی گرفتن تعداد جفت‌ها با تعداد نمادها؛ برای `n` نماد، `n - 1` جفت مجاور هست.
4. استفاده از خروجی این مثال برای ادعای تعداد tokenهای یک API واقعی.

### خودآزمایی با پاسخ

1. چرا جفت `(a,b)` در دور اول پنج‌بار دیده شد؟ **چهار بار در دو `abab`، به‌علاوه یک بار در `abac`.**
2. چرا `(ab,ab)` در دور دوم دو بار است؟ **در هرکدام از دو توالی `[ab,ab]` یک‌بار.**
3. آیا الگوریتم معنی `abab` را می‌فهمد؟ **نه؛ فقط فراوانی جفت‌ها را می‌شمارد.**
4. آیا این کد tokenizer دقیق یک مدل API را پیاده می‌کند؟ **نه؛ فقط مثال آموزشی ساده‌شده است.**
