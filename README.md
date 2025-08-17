# SEU Scheduler (Fly.io)

## نشر سريع
1. ارفع هذا المشروع إلى GitHub.
2. على Fly:
   - أنشئ حجم تخزين: `fly volumes create data --region fra --size 1 -a APPNAME`
   - اضبط السرّ: `fly secrets set SECRET_KEY=$(openssl rand -hex 32) -a APPNAME`
   - (اختياري) لا تستخدم DATABASE_URL وسيتم حفظ SQLite في `/data/app.db` افتراضيًا.
3. تأكد من `fly.toml` أن `internal_port=8080` و healthcheck على `/health`.
4. انشر: `fly deploy -a APPNAME --remote-only`.
5. بعد الإقلاع، قم بتهيئة/ترقية قاعدة البيانات:
   ```bash
   fly ssh console -a APPNAME
   cd /app
   flask --app app init-db
   flask --app app upgrade-db
   exit
   ```

## ملاحظات
- أوّل مستخدم يُنشأ يصبح مشرفًا تلقائيًا.
- واجهة متجاوبة + ألوان مميِّزة: حضوري/عن بعد، ميد/فاينل.
- زر إظهار/إخفاء الإحصائيات، وتصدير CSV للمحاضرات والاختبارات، وطباعة PDF من المتصفح.