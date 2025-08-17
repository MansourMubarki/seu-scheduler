# seu-scheduler patch

What changed:

1. **`is_admin` column added** to `User` model.
2. Fixed first-user logic: the first registered user becomes admin automatically.
3. Added `/health` route returning `200 OK` (for Fly.io health checks).
4. Added a simple CLI migration command: `flask --app app upgrade-db`.

## How to deploy on Fly.io

1. Replace your `app.py` with the one in this zip.
2. If your DB already exists on Fly (SQLite at `/data/app.db`):
   ```bash
   fly ssh console -a seu-scheduler
   cd /app
   flask --app app upgrade-db
   exit
   ```
3. (Recommended) Ensure you use gunicorn in `Dockerfile`:
   ```dockerfile
   CMD ["gunicorn","-w","1","-k","gthread","--threads","2","--timeout","120","--graceful-timeout","30","-b","0.0.0.0:8080","app:app"]
   ```
4. Deploy:
   ```bash
   fly deploy -a seu-scheduler --remote-only
   ```
5. Verify health:
   - Open https://seu-scheduler.fly.dev/health → should return `ok`.
   - `fly logs -a seu-scheduler --since 2m` should show `GET /health ... 200`.
