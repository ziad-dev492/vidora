FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libpq5 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/media /app/staticfiles && python manage.py collectstatic --noinput
EXPOSE 3000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:3000", "--workers", "3", "--timeout", "120"]
