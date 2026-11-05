# داده‌ها و منابع رسمی Pathfinder — prototype قبلی

> این snapshot فقط برای prototype قبلیِ Pathfinder نگه داشته شده است و هدف فعلی آموزش/ساخت Agent نیست.

## وضعیت snapshot

- تاریخ بررسی کاتالوگ: **۵ نوامبر ۲۰۲۶**.
- دامنه‌ی فعلی: ۳ برنامه، ۴ صفحه‌ی رسمی یکتا و ۱۵ fact تأییدشده.
- این مجموعه دستی و کوچک است؛ زنده‌بودن صفحه یا به‌روزبودن خودکار را تضمین نمی‌کند.
- هر fact با وضعیت `verified` به شناسه‌ی یک صفحه‌ی رسمی وصل است. تاریخ بررسی کنار هر منبع ثبت شده است.
- `valid_for` زمینه‌ی زمانی/کاربردی fact را بیان می‌کند؛ تاریخ آن را تضمین یا تمدید نمی‌کند.
- شهریه‌ی هر سه برنامه هنوز **جمع‌آوری نشده** و عمداً بدون مقدار است. مقدار خالی به معنی شهریه‌ی صفر یا رایگان بودن نیست.

## فهرست منابع ثبت‌شده

| شناسه در داده | صفحه‌ی رسمی | دانشگاه / ناشر | URL | بررسی |
|---|---|---|---|---|
| `uoft-mscac-apply` | Application Process | MScAC Program, Department of Computer Science, University of Toronto | [mscac.utoronto.ca/apply](https://mscac.utoronto.ca/apply/) | 2026-11-05 |
| `waterloo-mmath-program` | Computer Science — Master of Math (MMath) | Future Graduate Students, University of Waterloo | [uwaterloo.ca/.../computer-science-master-math-mmath](https://uwaterloo.ca/future-graduate-students/programs/by-faculty/math/computer-science-master-math-mmath) | 2026-11-05 |
| `ubc-cs-admissions` | Admissions — Computer Science Graduate Programs | Department of Computer Science, The University of British Columbia | [cs.ubc.ca/students/grad/admissions](https://www.cs.ubc.ca/students/grad/admissions) | 2026-11-05 |
| `ubc-cs-eligibility` | Eligibility — Computer Science Graduate Programs | Department of Computer Science, The University of British Columbia | [cs.ubc.ca/.../admissions/eligibility](https://www.cs.ubc.ca/students/grad/admissions/eligibility) | 2026-11-05 |

منبع اصلی حقیقت `backend/catalog.json` است؛ جدول بالا راهنمای خواندن آن است.

## Factهای ثبت‌شده

### University of Toronto — MScAC, Artificial Intelligence

- **موعد درخواست:** ۱ دسامبر ۲۰۲۶، ساعت ۱۱:۵۹ شب به وقت شرقی، برای Fall 2027.
- **پایه‌ی نمره:** دست‌کم B+ (در مقیاس U of T حدود ۷۷–۷۹٪) در سال پایانی دوره‌ی کارشناسی.
- **پیش‌نیازهای تمرکز AI:** آشنایی مرتبط با علوم کامپیوتر، آمار یا مهندسی؛ شامل حسابان، جبر خطی، احتمال/آمار و برنامه‌نویسی.
- **انتخاب تمرکز:** تمرکز باید در خود درخواست انتخاب شود و ارزیابی AI رقابتی و جداگانه است.
- **معرف‌ها:** سه referee؛ صفحه توصیه می‌کند ترجیحاً دست‌کم دو نفر دانشگاهی باشند.
- **تجربه‌ی کار/پژوهش:** ترجیح داده می‌شود، اما الزامی اعلام نشده است.
- **شهریه:** در این snapshot جمع‌آوری نشده است.

تمام موارد بالا به `uoft-mscac-apply` ارجاع دارند. حداقل‌های عمومی یا پیش‌نیاز تمرکز به معنی تضمین پذیرش نیستند.

### University of Waterloo — Computer Science MMath

- **نوع/ساختار:** کارشناسی ارشد پژوهشی؛ پذیرش مستقیم به گزینه‌ی thesis در صفحه ذکر شده است.
- **مدت:** ۲۴ ماه تمام‌وقت؛ به‌صورت fact جداگانه به همان صفحه ارجاع دارد.
- **شیوه‌ی برگزاری:** حضوری در campus؛ fact جداگانه با ارجاع به همان صفحه دارد.
- **موعد:** ۱ دسامبر برای پذیرش September سال بعد؛ در snapshot به September 2027 وصل شده است.
- **پیش‌زمینه و نمره:** مدرک honours در Computer Science یا Engineering (یا معادل) با دست‌کم ۷۸٪ طبق صفحه‌ی برنامه.
- **معرف‌ها:** سه مرجع؛ دست‌کم دو نفر باید دانشگاهی باشند.
- **شهریه:** در این snapshot جمع‌آوری نشده است.

موعد و حداقل نمره به صفحه‌ی رسمی برنامه وصل‌اند؛ حداقل اعلام‌شده به معنی تضمین پذیرش نیست.

### The University of British Columbia — Computer Science MSc

- **موعد درج‌شده:** ۱۵ دسامبر ۲۰۲۶ برای برنامه‌هایی که September 2027 یا January 2028 آغاز می‌شوند؛ term موردنظر باید در صفحه‌ی رسمی دوباره بررسی شود.
- **مدت:** دو سال و حدود ۱۶ ماه پژوهش تمام‌وقت، طبق صفحه‌ی پذیرش دپارتمان.
- **پیش‌زمینه:** بیشتر متقاضیان مدرکی معادل مدرک چهارساله‌ی UBC در Computer Science دارند؛ معیار نمره به کشور وابسته است.
- **محدودیت پذیرش:** برآورده‌کردن حداقل شرایط، به‌تنهایی برای پذیرش کافی نیست.
- **تأمین مالی:** صفحه‌ی دپارتمان می‌گوید برنامه‌های research MSc، PhD و PhD Track کاملاً تأمین مالی می‌شوند؛ جزئیات بسته، صلاحیت و شروط باید مستقیماً از دانشگاه تأیید شوند.
- **شهریه:** در این snapshot جمع‌آوری نشده است.

مهلت، مدت و گزاره‌ی تأمین مالی به `ubc-cs-admissions` ارجاع دارند؛ قاعده‌ی پیش‌زمینه و حداقل صلاحیت به `ubc-cs-eligibility` ارجاع دارد.

## چه چیزی را نباید از داده نتیجه گرفت؟

- «Not captured» را نباید رایگان، صفر، ناموجود یا بی‌اهمیت تعبیر کرد.
- حداقل معدل منتشرشده، احتمال پذیرش فردی را پیش‌بینی نمی‌کند.
- گزاره‌ی تأمین مالی UBC تضمین‌کننده‌ی مبلغ یا شرایط یک متقاضی خاص نیست.
- deadlineهای ۲۰۲۶ ممکن است پس از این snapshot تغییر کرده باشند یا از موعد بگذرند؛ UI آن‌ها را snapshot معرفی می‌کند، نه اعلان زنده.
- عنوان‌های `fields`، `tags` و `summary` داده‌ی دسته‌بندی/معرفی‌اند، نه معیار رسمی پذیرش.

## روش به‌روزرسانی داده

۱. صفحه‌ی **رسمی دانشگاه** را برای intake مشخص باز و دوباره بررسی کن؛ از snippet موتور جست‌وجو یا وب‌سایت ثالث به‌عنوان تنها مدرک استفاده نکن.
۲. مقدار و زمینه‌ی آن را در `backend/catalog.json` به‌روزرسانی کن؛ `valid_for` و `note` باید ابهام زمانی یا استثنا را نشان دهند.
۳. fact تأییدشده را به `source_id` معتبر وصل کن؛ اگر مقدار پیدا یا تأیید نشد، آن را `not_collected` نگه دار و مقدار نساز.
۴. `checked_at` همان منبع/برنامه و تاریخ `catalog_checked_at` را به‌روز کن.
۵. تست‌های Backend و build Frontend را اجرا کن؛ خروجی API و لینک‌های UI را نیز دستی مرور کن.

برای اجرای تست‌ها و build، راهنمای Windows PowerShell در [README](../README.md#تست-و-build) است.
