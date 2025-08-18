# wsgi.py — robust entrypoint
import traceback

app = None

# 1) app.py يحتوي كائن app
try:
    import app as app_module
    if hasattr(app_module, "app"):
        app = app_module.app
except Exception:
    traceback.print_exc()

# 2) app.py يحتوي كائن application
if app is None:
    try:
        import app as app_module
        if hasattr(app_module, "application"):
            app = app_module.application
    except Exception:
        traceback.print_exc()

# 3) app.py يحتوي دالة create_app()
if app is None:
    try:
        import app as app_module
        if hasattr(app_module, "create_app"):
            app = app_module.create_app()
    except Exception:
        traceback.print_exc()

# 4) آخر حل: تطبيق صغير برسالة خطأ مفيدة
if app is None:
    from flask import Flask
    app = Flask(__name__)

    @app.get("/")
    def _boot_error():
        return "WSGI failed to locate your Flask app. Ensure you expose 'app' or 'create_app' in app.py.", 500
