
import os
from datetime import datetime, date, time
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# ============== Config ==============
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "app.db")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-prod")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL:
    # fly.io often provides postgres:// - normalize to postgresql+psycopg2://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ============== Models ==============
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    day = db.Column(db.String(20), nullable=False)  # Sunday..Saturday
    start = db.Column(db.String(5), nullable=False) # "16:00"
    end = db.Column(db.String(5), nullable=False)   # "16:50"
    mode = db.Column(db.String(20), default="حضوري")  # حضوري / عن بعد

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(20), nullable=False)  # ميد / فاينل
    date = db.Column(db.String(10), nullable=False)  # 2025-08-20
    start = db.Column(db.String(5), nullable=False)
    end = db.Column(db.String(5), nullable=False)

# ============== Helpers ==============
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
        u = current_user()
        if not u or not getattr(u, 'is_admin', False):
            flash('هذه الصفحة للمشرفين فقط', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)

# ============== Routes ==============
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
        user = User(name=name, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.flush()
        # اجعل أول مستخدم مشرف تلقائياً
        if User.query.count() == 0:
            user.is_admin = True
        db.session.commit()
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
        flash("مرحبًا بك يا {}!".format(user.name), "success")
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

    # --- إحصائيات المستخدم ---
    def _to_minutes(t):
        try:
            h, m = map(int, str(t).split(":"))
            return h*60 + m
        except Exception:
            return 0

    lec_count = len(courses)
    onsite_keywords = {"حضوري", "onsite", "inperson", "presence"}
    online_keywords = {"عن بعد", "اونلاين", "online", "remote"}
    onsite_count = sum(1 for c in courses if str(c.mode).strip() in onsite_keywords)
    online_count = sum(1 for c in courses if str(c.mode).strip() in online_keywords)

    total_minutes = sum(max(0, _to_minutes(getattr(c, "end", "0:00")) - _to_minutes(getattr(c, "start", "0:00"))) for c in courses)
    total_hours = round(total_minutes/60, 2)

    exam_count = len(exams)
    mid_count = sum(1 for e in exams if getattr(e, "kind", "") == "ميد")
    final_count = sum(1 for e in exams if getattr(e, "kind", "") == "فاينل")

    return render_template(
        "dashboard.html",
        user=user,
        courses=courses,
        exams=exams,
        lec_count=lec_count,
        onsite_count=onsite_count,
        online_count=online_count,
        total_hours=total_hours,
        exam_count=exam_count,
        mid_count=mid_count,
        final_count=final_count,
    )

@app.route("/course", methods=["POST"])
@login_required
def add_course():
    user = current_user()
    data = request.form
    course = Course(
        user_id=user.id,
        title=data.get("title","").strip(),
        day=data.get("day"),
        start=data.get("start"),
        end=data.get("end"),
        mode=data.get("mode","حضوري"),
    )
    db.session.add(course)
    db.session.commit()
    flash("تمت إضافة المحاضرة.", "success")
    return redirect(url_for("dashboard"))

@app.route("/exam", methods=["POST"])
@login_required
def add_exam():
    user = current_user()
    data = request.form
    exam = Exam(
        user_id=user.id,
        title=data.get("title","").strip(),
        kind=data.get("kind"),
        date=data.get("date"),
        start=data.get("start"),
        end=data.get("end"),
    )
    db.session.add(exam)
    db.session.commit()
    flash("تمت إضافة الاختبار.", "success")
    return redirect(url_for("dashboard"))

@app.route("/course/<int:cid>/delete", methods=["POST"])
@login_required
def delete_course(cid):
    user = current_user()
    c = Course.query.filter_by(id=cid, user_id=user.id).first_or_404()
    db.session.delete(c)
    db.session.commit()
    flash("تم حذف المحاضرة.", "info")
    return redirect(url_for("dashboard"))

@app.route("/exam/<int:eid>/delete", methods=["POST"])
@login_required
def delete_exam(eid):
    user = current_user()
    e = Exam.query.filter_by(id=eid, user_id=user.id).first_or_404()
    db.session.delete(e)
    db.session.commit()
    flash("تم حذف الاختبار.", "info")
    return redirect(url_for("dashboard"))

# API for exporting data as JSON (optional)
@app.route("/api/my-schedule")
@login_required
def api_schedule():
    user = current_user()
    courses = [{
        "title": c.title, "day": c.day, "start": c.start, "end": c.end, "mode": c.mode
    } for c in Course.query.filter_by(user_id=user.id)]
    exams = [{
        "title": e.title, "kind": e.kind, "date": e.date, "start": e.start, "end": e.end
    } for e in Exam.query.filter_by(user_id=user.id)]
    return jsonify({"courses": courses, "exams": exams})

# CLI init
@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("Database initialized.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))



@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.id.desc()).all()
    return render_template("admin.html",
        users=users,
        user_count=User.query.count(),
        admin_count=User.query.filter_by(is_admin=True).count(),
        course_count=Course.query.count(),
        exam_count=Exam.query.count())

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
    u.is_admin = False
    db.session.commit()
    flash("تمت إزالة صلاحيات المشرف.", "warning")
    return redirect(url_for('admin_dashboard'))

@app.post("/admin/user/<int:uid>/delete")
@login_required
@admin_required
def delete_user_admin(uid):
    # حذف المستخدم وكل بياناته
    Course.query.filter_by(user_id=uid).delete()
    Exam.query.filter_by(user_id=uid).delete()
    User.query.filter_by(id=uid).delete()
    db.session.commit()
    flash("تم حذف المستخدم وبياناته.", "danger")
    return redirect(url_for('admin_dashboard'))

@app.post("/admin/clear-all")
@login_required
@admin_required
def clear_all_data():
    Course.query.delete()
    Exam.query.delete()
    db.session.commit()
    flash("تم مسح كل المحاضرات والاختبارات.", "warning")
    return redirect(url_for('admin_dashboard'))



@app.get("/health")
def health():
    return "ok", 200
