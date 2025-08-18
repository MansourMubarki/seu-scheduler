import os, json
from datetime import timedelta, datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import csv, io
from sqlalchemy import inspect, text as _sql_text

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "app.db"))

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-prod")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

# ---- Jinja time filter (24h -> 12h ص/م) ----
def _to12(time_str):
    if not time_str:
        return ""
    try:
        h, m = map(int, str(time_str).split(":"))
    except Exception:
        return str(time_str)
    suffix = "م" if h >= 12 else "ص"
    h12 = ((h + 11) % 12) + 1
    return f"{h12}:{m:02d} {suffix}"
app.jinja_env.filters["t12"] = _to12

# ---- Database config ----
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}
db = SQLAlchemy(app)

# --- lightweight migration: ensure 'role' column exists
def ensure_role_column():
    try:
        insp = inspect(db.engine)
        cols = [c['name'] for c in insp.get_columns('user')]
        if 'role' not in cols:
            # اقتباس اسم الجدول "user" للـ Postgres، وقيمة النص 'Student' للـ SQLite/Postgres
            sql = 'ALTER TABLE "user" ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT \'Student\''
            with db.engine.begin() as con:
                con.execute(_sql_text(sql))
    except Exception:
        # نتجاهل لو العمود موجود أو لا يدعم ALTER TABLE في بعض النسخ
        pass

# ---- Models ----
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='Student', nullable=False)  # Admin / Student

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    day = db.Column(db.String(20), nullable=False)  # الأحد..الخميس
    start = db.Column(db.String(5), nullable=False) # "16:00"
    end = db.Column(db.String(5), nullable=False)   # "16:50"
    mode = db.Column(db.String(20), default="حضوري")  # حضوري / عن بعد

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(20), nullable=False)  # ميد / فاينل
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    start = db.Column(db.String(5), nullable=False)
    end = db.Column(db.String(5), nullable=False)

# ---- Helpers ----
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        u = current_user()
        if not u or getattr(u, 'role', 'Student') != 'Admin':
            flash("تحتاج صلاحية مشرف للوصول.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper

def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None

# نضمن إنشاء الجداول والترقية عند أول طلب (تفيد تحت gunicorn/Fly)
@app.before_first_request
def _init_db_once():
    with app.app_context():
        db.create_all()
        ensure_role_column()

# ---- Routes ----
@app.get("/healthz")
def healthz():
    return "ok", 200

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not name or not email or not password:
            flash("يرجى تعبئة جميع الحقول", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("البريد مستخدم مسبقًا", "danger")
            return redirect(url_for("register"))

        # أول مسجل يصبح Admin
        first = (User.query.count() == 0)
        role = 'Admin' if first else 'Student'
        user = User(name=name, email=email,
                    password_hash=generate_password_hash(password),
                    role=role)
        db.session.add(user); db.session.commit()
        flash("تم التسجيل بنجاح! سجل الدخول الآن.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("بيانات الدخول غير صحيحة", "danger")
            return redirect(url_for("login"))
        session["user_id"] = user.id
        session["role"] = getattr(user,'role','Student')
        flash(f"مرحبًا بك يا {user.name}!", "success")
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("تم تسجيل الخروج", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    courses = Course.query.filter_by(user_id=user.id).all()
    exams = Exam.query.filter_by(user_id=user.id).all()
    return render_template("dashboard.html", user=user, courses=courses, exams=exams)

@app.route("/course", methods=["POST"])
@login_required
def add_course():
    user = current_user(); data = request.form
    c = Course(user_id=user.id, title=data.get("title","").strip(), day=data.get("day"),
               start=data.get("start"), end=data.get("end"), mode=data.get("mode","حضوري"))
    db.session.add(c); db.session.commit()
    flash("تمت إضافة المحاضرة.", "success")
    return redirect(url_for("dashboard"))

@app.route("/course/<int:cid>/delete", methods=["POST"])
@login_required
def delete_course(cid):
    user = current_user()
    c = Course.query.filter_by(id=cid, user_id=user.id).first_or_404()
    db.session.delete(c); db.session.commit()
    flash("تم حذف المحاضرة.", "info")
    return redirect(url_for("dashboard"))

@app.route("/exam", methods=["POST"])
@login_required
def add_exam():
    user = current_user(); data = request.form
    e = Exam(user_id=user.id, title=data.get("title","").strip(), kind=data.get("kind"),
             date=data.get("date"), start=data.get("start"), end=data.get("end"))
    db.session.add(e); db.session.commit()
    flash("تمت إضافة الاختبار.", "success")
    return redirect(url_for("dashboard"))

@app.route("/exam/<int:eid>/delete", methods=["POST"])
@login_required
def delete_exam(eid):
    user = current_user()
    e = Exam.query.filter_by(id=eid, user_id=user.id).first_or_404()
    db.session.delete(e); db.session.commit()
    flash("تم حذف الاختبار.", "info")
    return redirect(url_for("dashboard"))

@app.route("/api/my-schedule")
@login_required
def api_schedule():
    user = current_user()
    courses = [{"title": c.title, "day": c.day, "start": c.start, "end": c.end, "mode": c.mode}
               for c in Course.query.filter_by(user_id=user.id)]
    exams = [{"title": e.title, "kind": e.kind, "date": e.date, "start": e.start, "end": e.end}
             for e in Exam.query.filter_by(user_id=user.id)]
    return jsonify({"courses": courses, "exams": exams})

@app.cli.command("init-db")
def init_db():
    db.create_all(); ensure_role_column(); print("Database initialized.")

# ======== Admin & Stats Routes (SEU Scheduler V5) ========
DAYS_AR = ['الأحد','الاثنين','الثلاثاء','الأربعاء','الخميس']

def _minutes(hhmm):
    try:
        h,m = hhmm.split(':')
        return int(h)*60 + int(m)
    except Exception:
        return 0

def _duration_minutes(start, end):
    return max(0, _minutes(end) - _minutes(start))

@app.route('/admin')
@admin_required
def admin():
    u = current_user()
    return render_template('admin.html', user=u)

@app.route('/api/stats')
@login_required
def api_stats():
    u = current_user()
    # Query data
    courses = Course.query.filter_by(user_id=u.id).all()
    exams = Exam.query.filter_by(user_id=u.id).all()

    # Counts
    day_counts = {d:0 for d in DAYS_AR}
    mode_counts = {'حضوري':0, 'عن بعد':0}
    total_minutes = 0
    sessions_per_week = 0

    for c in courses:
        day_counts[c.day] = day_counts.get(c.day,0) + 1
        mode_counts[c.mode] = mode_counts.get(c.mode,0) + 1
        total_minutes += _duration_minutes(getattr(c,'start','00:00'), getattr(c,'end','00:00'))
        sessions_per_week += 1

    weekly_hours = round(total_minutes/60, 1)

    # Upcoming exams in next 30 days
    today = date.today()
    upcoming = 0
    for e in exams:
        try:
            d = datetime.strptime(e.date, '%Y-%m-%d').date()
            if 0 <= (d - today).days <= 30:
                upcoming += 1
        except Exception:
            pass

    # Insights
    busiest_day = max(day_counts, key=lambda k: day_counts[k]) if day_counts else None
    total_modes = sum(mode_counts.values()) or 1
    remote_pct = round(100 * (mode_counts.get('عن بعد',0) / total_modes))
    def overlap(a_start,a_end,b_start,b_end):
        return _minutes(a_start) < _minutes(b_end) and _minutes(b_start) < _minutes(a_end)
    conflicts = []
    for i in range(len(courses)):
        for j in range(i+1, len(courses)):
            ci, cj = courses[i], courses[j]
            if ci.day == cj.day and overlap(ci.start, ci.end, cj.start, cj.end):
                conflicts.append(f"تعارض: {ci.title} مع {cj.title} يوم {ci.day}")

    insights = []
    if busiest_day:
        insights.append(f"أكثر يوم ازدحامًا: {busiest_day} ({day_counts[busiest_day]} محاضرات)")
    insights.append(f"نسبة المحاضرات عن بعد: {remote_pct}%")
    if conflicts:
        insights.extend(conflicts[:5])
    if upcoming:
        insights.append(f"{upcoming} اختبار/ات خلال 30 يوم")

    return jsonify({
        'courses_count': len(courses),
        'sessions_per_week': sessions_per_week,
        'weekly_hours': weekly_hours,
        'upcoming_exams_30d': upcoming,
        'day_counts': day_counts,
        'mode_counts': mode_counts,
        'insights': insights
    })

# ---- Data export/import ----
@app.route('/export/courses.csv')
@login_required
def export_courses_csv():
    u = current_user()
    rows = [('title','day','start','end','mode')]
    for c in Course.query.filter_by(user_id=u.id):
        rows.append((c.title, c.day, c.start, c.end, c.mode))
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    mem = io.BytesIO(buf.getvalue().encode('utf-8-sig'))
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name='courses.csv', mimetype='text/csv')

@app.route('/export/exams.csv')
@login_required
def export_exams_csv():
    u = current_user()
    rows = [('title','kind','date','start','end')]
    for e in Exam.query.filter_by(user_id=u.id):
        rows.append((e.title, e.kind, e.date, e.start, e.end))
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    mem = io.BytesIO(buf.getvalue().encode('utf-8-sig'))
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name='exams.csv', mimetype='text/csv')

@app.route('/export.json')
@login_required
def export_json():
    u = current_user()
    payload = {
        'courses': [ {'title':c.title,'day':c.day,'start':c.start,'end':c.end,'mode':c.mode}
                    for c in Course.query.filter_by(user_id=u.id) ],
        'exams': [ {'title':e.title,'kind':e.kind,'date':e.date,'start':e.start,'end':e.end}
                    for e in Exam.query.filter_by(user_id=u.id) ]
    }
    mem = io.BytesIO(json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'))
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name='data.json', mimetype='application/json')

@app.route('/import', methods=['POST'])
@login_required
def import_data():
    u = current_user()
    file = request.files.get('file')
    if not file:
        flash('لم يتم اختيار ملف','danger')
        return redirect(url_for('admin'))
    name = file.filename.lower()
    text = file.read().decode('utf-8-sig')

    imported = 0
    try:
        if name.endswith('.json'):
            obj = json.loads(text)
            for c in obj.get('courses', []):
                db.session.add(Course(user_id=u.id, title=c['title'], day=c['day'],
                                      start=c['start'], end=c['end'], mode=c['mode']))
                imported += 1
            for e in obj.get('exams', []):
                db.session.add(Exam(user_id=u.id, title=e['title'], kind=e['kind'],
                                    date=e['date'], start=e.get('start','00:00'), end=e.get('end','00:00')))
                imported += 1
            db.session.commit()
        else:
            rdr = csv.reader(io.StringIO(text))
            header = next(rdr, [])
            header = [h.strip().lower() for h in header]
            if header == ['title','day','start','end','mode']:
                for row in rdr:
                    if not row: continue
                    title, day, start, end, mode = row
                    db.session.add(Course(user_id=u.id, title=title, day=day, start=start, end=end, mode=mode))
                    imported += 1
                db.session.commit()
            elif header == ['title','kind','date','start','end']:
                for row in rdr:
                    if not row: continue
                    title, kind, d, start, end = row
                    db.session.add(Exam(user_id=u.id, title=title, kind=kind, date=d, start=start, end=end))
                    imported += 1
                db.session.commit()
            else:
                flash('رأس CSV غير معروف','danger')
                return redirect(url_for('admin'))
        flash(f'تم الاستيراد بنجاح: {imported} سجل','success')
    except Exception as ex:
        db.session.rollback()
        flash('فشل الاستيراد: ' + str(ex),'danger')
    return redirect(url_for('admin'))

# ---- Admin user management ----
@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.order_by(User.id.asc()).all()
    return render_template('admin_users.html', users=users)

@app.post('/admin/users/<int:uid>/set-role')
@admin_required
def admin_set_role(uid):
    u = User.query.get_or_404(uid)
    new_role = request.form.get('role','Student')
    if new_role not in ['Admin','Student']:
        flash('دور غير صالح','danger'); return redirect(url_for('admin_users'))
    u.role = new_role; db.session.commit()
    flash('تم تحديث الدور بنجاح','success')
    return redirect(url_for('admin_users'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        ensure_role_column()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
