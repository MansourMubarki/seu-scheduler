FROM python:3.11-slim

# Install system deps (for psycopg2-binary runtime libs)
RUN apt-get update && apt-get install -y --no-install-recommends     libpq5 curl ca-certificates && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PORT=8080     PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Copy app
COPY . /app

# Ensure data dir exists and is writable
RUN mkdir -p /data && chmod 755 /data

# Healthcheck is served by /health route
EXPOSE 8080

# Use gunicorn for production
CMD ["gunicorn", "-w", "2", "-k", "gthread", "--threads", "4", "--timeout", "120", "-b", "0.0.0.0:8080", "wsgi:app"]
