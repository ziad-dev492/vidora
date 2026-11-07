# Vidora

مشروع تطوير لمنصة فيديو باسم قابل للتغيير، مبني على Django 5.2 وDjango REST Framework وDjango ORM وPostgreSQL، مع قوالب HTML وBootstrap وJavaScript، وRedis/Celery وFFmpeg للمهام الخلفية. الاسم يمكن تغييره عبر `VIDORA_BRAND_NAME`. لا تتعامل مع هذه النسخة على أنها خدمة عامة جاهزة للإنتاج أو مدققة أمنيًا.

## ما نُفذ

- مستخدم Django مخصص، التسجيل والدخول والخروج واستعادة كلمة المرور، إعداد الملف الشخصي والقناة، روابط تحقق بريد موقعة صالحة 24 ساعة عند إعداد SMTP، وإدارة صور الحساب والقناة مع حد الحجم. تغيير اسم القناة يحدّث slug الفريد.
- نماذج Django ومهاجرات للقنوات والاشتراكات والفيديوهات والتصنيفات والوسوم ومهام المعالجة والنسخ والتفاعلات والتعليقات/الردود والقوائم والمحفوظات والسجل والإشعارات والبلاغات وسجل تدقيق الإدارة، مع قيود تكرار وفهارس.
- صفحة رئيسية وبحث DB مع صفحات وتصنيفات، قنوات ومشاهدة فيديو وShorts واشتراكات ومكتبة، ولوحتا مالك ومشرف منفصلتان. واجهات DRF الحالية للقراءة العامة فقط؛ عمليات التغيير تتم عبر صفحات Django المحمية بالجلسة وCSRF.
- رفع multipart لملف الفيديو والصورة المصغرة، تقدم رفع من المتصفح، وفحص توقيع الملف/الحجم، وملكية خادمية للفيديو، وإعادة محاولة المعالجة من الاستوديو. المعالجة تستخدم FFprobe وFFmpeg لإنشاء بيانات الفيديو وصورة مصغرة ونسخ MP4 حتى جودة المصدر، ويمكنها إخراج master HLS متكيف وقوائم تشغيل متعددة الدقات عند ضبط `ENABLE_HLS=1`. روابط الفيديو والصورة وHLS تمر عبر عروض تتحقق من الحالة والخصوصية، ويدعم MP4 طلبات HTTP Range.
- تفاعلات الإعجاب/عدم الإعجاب والاشتراك والتعليقات والردود والبلاغات والمشاهدة والحفظ والقوائم الخاصة والعامة، إشعارات التعليقات والردود والإعجاب والاشتراك وفيديو جديد من قناة مشترَك بها، مع قوائم إشعارات غير مقروءة.
- واجهة عربية RTL، وتفضيل إنجليزي يبدّل اتجاه الصفحة إلى LTR، ووضع فاتح/داكن وتصميم متجاوب. أغلب نصوص المنتج ما زالت بالعربية حتى عند اختيار LTR؛ لم تكتمل ترجمة الواجهة الإنجليزية.
- أُجري اختبار فعلي مؤقت باستخدام FFmpeg لفيديو عمودي مولّد للاختبار: استخرج مدة ثانيتين، أنشأ نسختي 360p/480p، وأنتج HLS بنجاح. لم تُحفظ هذه البيانات الاختبارية ضمن ملفات المشروع أو محتواه.

## تشغيل كامل عبر Docker Compose

المتطلبات: Docker Engine مع إضافة Compose، Git، وملف `.env` محلي. الأوامر التالية لـPowerShell داخل مجلد المشروع:

```powershell
Copy-Item .env.example .env
# غيّر SECRET_KEY إلى قيمة عشوائية محلية، وحدد ALLOWED_HOSTS المناسب.
docker compose up --build
```

يفتح الموقع على الجهاز المضيف عبر `http://localhost:3000`. للوصول من جهاز آخر على الشبكة نفسها، احصل على عنوان IPv4 للجهاز المضيف عبر `ipconfig`، ثم افتح `http://<عنوان-IPv4>:3000` من الجهاز الآخر. عنوان المضيف الحالي في بيئة التطوير هو `192.168.10.103` (قد يتغير من الراوتر؛ لا تستخدم `192.168.1.5` إلا إذا كان ذلك هو العنوان الحالي فعلًا). يجب أن يكون الجهازان على الشبكة نفسها، وأن تسمح قاعدة Windows Firewall باتصالات TCP الواردة على المنفذ 3000 من عناوين الشبكة المحلية فقط. إذا كان Windows يمنع الاتصال، افتح PowerShell كمسؤول ونفّذ:

```powershell
New-NetFirewallRule -DisplayName "Vidora LAN TCP 3000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3000 -RemoteAddress LocalSubnet -Profile Any
```

لا تستخدم خادم التطوير هذا أو HTTP للنشر على الإنترنت العام.

Compose يشغل PostgreSQL 16 وRedis 7؛ مهاجرات Django تُطبق عند بدء الويب، ويعمل عامل Celery بجواره. لإضافة التصنيفات الافتراضية وإنشاء حساب مشرف، في نافذة PowerShell ثانية:

```powershell
docker compose exec web python manage.py seed_categories
docker compose exec web python manage.py createsuperuser
```

بيانات PostgreSQL الافتراضية في Compose للاستخدام المحلي المعزول فقط، وليست بيانات إنتاج. يستخدم هذا Compose خادم Django التطويري؛ لا تنشره كما هو.

## تشغيل Django وCelery من VS Code على Windows

يمكن تشغيل PostgreSQL وRedis من Compose وحدهما (المنافذ منشورة على `127.0.0.1` فقط)، وتشغيل التطبيق وعامل Celery محليًا:

```powershell
Copy-Item .env.example .env
# عدّل DATABASE_URL إلى postgresql://vidora:vidora@localhost:5432/vidora
# وعدّل REDIS_URL إلى redis://localhost:6379/0
# ثم ابدأ الخدمتين فقط:
docker compose up -d db redis
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_categories
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

هذا يجعل خادم التطوير متاحًا على واجهات الشبكة؛ افتحه من جهاز آخر عبر `http://<عنوان-IPv4>:8000` واسمح بالمنفذ 8000 في Windows Firewall لعناوين الشبكة المحلية فقط. عند تشغيل `DEBUG=0` بدل وضع التطوير، أضف عنوان IP للمضيف إلى `ALLOWED_HOSTS`، وأضف أصل الصفحة الكامل (مثل `http://192.168.10.103:8000`) إلى `CSRF_TRUSTED_ORIGINS` إذا كان النموذج سيُرسل من ذلك الأصل. لا تفتح منافذ PostgreSQL أو Redis للإنترنت.

من خارج الشبكة المحلية، عنوان IP الخاص مثل `192.168.x.x` لا يمكن الوصول إليه عبر الإنترنت. يتطلب ذلك عنوانًا عامًا، وإعداد تحويل منفذ في الراوتر والجدار الناري، كما يجب نشر الموقع خلف HTTPS بإعداد إنتاجي؛ لا توجّه الإنترنت إلى خادم Django التطويري أو إلى HTTP.

في طرفية VS Code ثانية:

```powershell
.\.venv\Scripts\Activate.ps1
celery -A config worker -l INFO --pool=solo
```

بدون Docker، ثبّت PostgreSQL 16 وRedis 7 بصورة مستقلة، أنشئ قاعدة البيانات والمستخدم `vidora`، واضبط عنوانيهما في `.env`. على سبيل المثال داخل `psql` بصلاحية مدير محلي:

```sql
CREATE USER vidora WITH PASSWORD 'vidora';
CREATE DATABASE vidora OWNER vidora;
```

ثبّت FFmpeg/FFprobe لنظام Windows وأضف مجلد `bin` إلى `PATH`، ثم افتح طرفية جديدة وتأكد من `ffmpeg -version` و`ffprobe -version`. عند تشغيل التطبيق محليًا دون Docker يجب أن تكون PostgreSQL وRedis وFFmpeg/FFprobe متاحة فعلًا، وأن يبقى عامل Celery عاملًا لتظهر نتيجة المعالجة. افتح مجلد المشروع في VS Code واختر بيئة `.venv` مفسرًا للمشروع. على Linux/macOS استخدم `python3 -m venv .venv` ثم `source .venv/bin/activate` و`celery -A config worker -l INFO`.

## الاختبارات والفحوص

```powershell
python manage.py collectstatic --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

تم التحقق من `manage.py check` و`makemigrations --check --dry-run` ونجاح 27 اختبارًا باستخدام SQLite الاختبارية. كما اختُبر طلب GET ونموذج POST من عنوان LAN؛ أُرسل CSRF cookie وقُبل الطلب غير المكتمل بدل رفضه بسبب CSRF. SQLite خيار للاختبارات فقط (`SQLITE_USE=1`)، وليست القاعدة الأساسية. تشغيل الموقع عبر Docker يعتمد PostgreSQL وRedis؛ فحوص الاختبارات لا تغني عن إعداد HTTPS وإعدادات الإنتاج قبل النشر العام. أُجري اختبار FFmpeg/HLS منفصل بقاعدة ووسائط مؤقتة، كما ورد أعلاه.

## البريد وHLS والتخزين الخارجي

- البريد المحلي يطبع الرسائل إلى سجل الطرفية. للبريد الفعلي اضبط `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` و`EMAIL_HOST` و`EMAIL_PORT` و`EMAIL_HOST_USER` و`EMAIL_HOST_PASSWORD` و`EMAIL_USE_TLS` أو `EMAIL_USE_SSL` عبر متغيرات بيئة سرية. التحقق من البريد لا يمنع تسجيل الدخول حاليًا.
- لتشغيل HLS في التطوير، عيّن `ENABLE_HLS=1` في `.env` وأعد تشغيل الويب والعامل. يجب وجود FFmpeg/FFprobe وRedis. الدقات الناتجة تعتمد على أبعاد وجودة المصدر، ولا يُنشأ rendition أعلى من المصدر.
- التخزين الافتراضي محلي. يمكن إعداد `VIDEO_STORAGE=s3` واسم bucket ومنطقة S3 ومفاتيحها في بيئة التشغيل؛ استخدم bucket خاصًا، واختبر سياسات الوصول وروابط البث والصور ومشاركة ملفات الوسائط قبل تشغيل إنتاجي. لا تضع مفاتيح AWS أو أسرار SMTP في Git.

## حدود النسخة الحالية

هذه نسخة قابلة للتشغيل المحلي وليست مكافئة لكل معايير المنصة الكبيرة. الرفع حاليًا طلب multipart واحد مع إظهار تقدمه؛ لم يُنفذ الرفع المجزأ أو الاستئناف. الاتجاه LTR متاح لكن تعريب/ترجمة كل النصوص الإنجليزية لم يكتمل. لوحة المشرف تنفذ الحسابات والقنوات والتصنيفات والبلاغات وسجل التدقيق والإحصاءات الأساسية؛ لم تُنفذ إعدادات منصة عامة شاملة أو أدوات إدارة محتوى تغطي كل السيناريوهات. التوصيات أولية قائمة على البيانات المتاحة وليست نموذج ذكاء اصطناعي. لا توجد مراجعة أمنية مستقلة أو اختبار ضغط أو تحقق من إعداد نشر عام؛ اختبر إعدادات HTTPS وALLOWED_HOSTS والكوكيز وحدود الطلب والتخزين والنسخ الاحتياطي والأسرار في بيئة الهدف قبل النشر.
