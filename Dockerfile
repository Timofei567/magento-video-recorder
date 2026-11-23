FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends apache2 apache2-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt \
    && mod_wsgi-express module-config > /etc/apache2/mods-available/wsgi.load \
    && a2enmod wsgi

COPY web_service.py video_service.wsgi apache-vhost.conf ./
RUN a2dissite 000-default \
    && cp /app/apache-vhost.conf /etc/apache2/sites-available/video-service.conf \
    && a2ensite video-service \
    && mkdir -p /app/uploads \
    && chown -R www-data:www-data /app

EXPOSE 80
CMD ["apache2ctl", "-D", "FOREGROUND"]
