# wsgi.py — robust entrypoint
import traceback

app = None

try:
    import app as app_module
    if hasattr(app_module, "app"):
        app = app_module.app
except Exception:
    traceback.print_exc()

if app is None:
    try:
        import app as app_module
        if hasattr(app_module, "application"):
            app = app_module.application
    except Exception:
        traceback.print_exc()

if app is None:
    try:
        import app as app_module
        if hasattr(app_module, "create_app"):
            app = app_module.create_app()
    except Exception:
        traceback.print_exc()

if app is None:
    from flask import Flask
    app = Flask(__name__)

    @app.get("/")
    def _boot_error():
        return "WSGI failed to locate your Flask app. Ensure you expose 'app' or 'create_app' in app.py.", 500
