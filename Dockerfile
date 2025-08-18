# Dockerfile (template) — use if your current Dockerfile fails to boot
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir gunicorn
# Ensure data mount exists
RUN mkdir -p /data
COPY . /app
EXPOSE 8080
# Serve robustly via wsgi:app (loads from wsgi.py)
CMD ["gunicorn","-w","2","-k","gthread","--threads","2","-b","0.0.0.0:8080","--log-level","debug","wsgi:app"]
