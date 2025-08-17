
# SEU Scheduler (Fly.io)

منظّم جداول لطلاب **الجامعة السعودية الإلكترونية** مع تسجيل مستخدمين، إنشاء جدول أسبوعي وإضافة اختبارات، مع إمكانية تنزيل الجدول كـ **PNG** أو **PDF** من الواجهة مباشرة.

## التشغيل محليًا
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app.py
python app.py
# افتح http://localhost:8080
```

> أول تشغيل ينشئ قاعدة `app.db` تلقائيًا.

## النشر على Fly.io
1) ثبّت أداة Fly:
```bash
curl -L https://fly.io/install.sh | sh
```
2) سجّل الدخول ثم أنشئ التطبيق:
```bash
fly auth login
fly launch --no-deploy  # وافق على اسم التطبيق أو غيّره
```
3) (اختياري) إن أردت Postgres مُدار:
```bash
fly postgres create
fly postgres attach --app <APP_NAME> <PG_APP_NAME>
```
4) انشر:
```bash
fly deploy
```
> اضبط متغير `SECRET_KEY` عبر:
```bash
fly secrets set SECRET_KEY=$(openssl rand -hex 32)
```

## ملاحظات
- التصدير إلى PNG/PDF يتم عبر **html2canvas + jsPDF** على المتصفح، لا حاجة لحزم ثقيلة.
- الشعار موجود في `static/img/seu-logo.png` ومستخدم في الواجهة.
- حقوق أسفل الصفحة:
> فكرة وتنفيذ المدرب **منصور مباركي** — تمت البرمجة بمساعدة **ChatGPT** • © 2025
