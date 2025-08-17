# Simple, reliable image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fly will provide PORT, default to 8080
ENV PORT=8080

# Using Flask's built-in server for simplicity; you can switch to gunicorn later
CMD ["python", "app.py"]