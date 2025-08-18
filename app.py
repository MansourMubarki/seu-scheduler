import os
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "app.db"))

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-prod")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

# ---- Jinja time filter (24h -> 12h ص/م) ----
def _to12(time_str):
    if not time_str: return ""
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

# ---- Models ----
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    day = db.Column(db.String(20), nullable=False)  # الأحد..السبت
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

def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None



# --- Admin helper/decorators ---
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u or not getattr(u, 'is_admin', False):
            flash('هذه الصفحة للمشرفين فقط', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_user():
    u = current_user()
    return {'auth_user': u, 'is_admin': (u.is_admin if u else False)}
# ---- Routes ----
@app.get("/healthz")
def healthz(): return "ok", 200

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
        first = (User.query.count() == 0)
        user = User(name=name, email=email, password_hash=generate_password_hash(password), is_admin=first)
        db.session.add(user); db.session.commit()
        if first:
            flash('تم إنشاء حسابك كمشرف (أول مستخدم).', 'info')
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
    db.create_all(); print("Database initialized.")


# ---- Admin Panel ----
@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.id.asc()).all()
    from models import Course if False else None  # placeholder if linter
    user_count = User.query.count()
    admin_count = User.query.filter_by(is_admin=True).count()
    course_count = Course.query.count() if 'Course' in globals() else 0
    exam_count = Exam.query.count() if 'Exam' in globals() else 0
    return render_template("admin.html",
                           users=users,
                           user_count=user_count,
                           admin_count=admin_count,
                           course_count=course_count,
                           exam_count=exam_count)

@app.post("/admin/user/<int:uid>/make-admin")
@login_required
@admin_required
def make_admin(uid):
    u = User.query.get_or_404(uid)
    u.is_admin = True
    db.session.commit()
    flash("تمت ترقية المستخدم إلى مشرف.", "success")
    return redirect(url_for('admin_dashboard'))

@app.post("/admin/user/<int:uid>/remove-admin")
@login_required
@admin_required
def remove_admin(uid):
    u = User.query.get_or_404(uid)
    # لا تقم بإزالة آخر مشرف
    if User.query.filter_by(is_admin=True).count() <= 1 and u.is_admin:
        flash("لا يمكن إزالة آخر مشرف.", "danger")
        return redirect(url_for('admin_dashboard'))
    u.is_admin = False
    db.session.commit()
    flash("تمت إزالة صلاحية المشرف.", "info")
    return redirect(url_for('admin_dashboard'))

@app.post("/admin/user/<int:uid>/delete")
@login_required
@admin_required
def delete_user_admin(uid):
    # منع حذف نفسك
    if current_user().id == uid:
        flash("لا يمكنك حذف نفسك.", "danger")
        return redirect(url_for('admin_dashboard'))
    # حذف بيانات المستخدم
    Course.query.filter_by(user_id=uid).delete()
    Exam.query.filter_by(user_id=uid).delete()
    u = User.query.get_or_404(uid)
    db.session.delete(u)
    db.session.commit()
    flash("تم حذف المستخدم وجميع بياناته.", "warning")
    return redirect(url_for('admin_dashboard'))

@app.post("/admin/clear-all")
@login_required
@admin_required
def clear_all_data():
    # مسح جميع المحاضرات والاختبارات (تبقى حسابات المستخدمين)
    Course.query.delete()
    Exam.query.delete()
    db.session.commit()
    flash("تم مسح كل المحاضرات والاختبارات.", "warning")
    return redirect(url_for('admin_dashboard'))



# ===== Admin bootstrap (protected) =====
@app.get("/make_admin")
def make_admin_bootstrap():
    # حماية بسيطة عبر توكن من متغير بيئة
    token_param = request.args.get("token", "")
    token_env = os.environ.get("ADMIN_SETUP_TOKEN", "")
    if not token_env or token_param != token_env:
        return "Forbidden", 403

    target_email = "metuo@msn.com"
    target_name = "Metuo"
    u = User.query.filter_by(email=target_email.lower()).first()
    if u:
        u.is_admin = True
    else:
        # NOTE: غيّر كلمة المرور بعد أول دخول
        default_password = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "ChangeMe#123")
        u = User(name=target_name, email=target_email.lower(),
                 password_hash=generate_password_hash(default_password),
                 is_admin=True)
        db.session.add(u)
    db.session.commit()
    return "✅ تم تعيين metuo@msn.com كأدمن. تذكر حذف هذا المسار أو تعطيله.", 200


if __name__ == "__main__":
    with app.app_context(): db.create_all()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
