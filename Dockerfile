FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System-Abhängigkeiten + Node.js (für Tailwind-Build)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python-Abhängigkeiten installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Quellcode kopieren
COPY . .

# Vendor-JS/CSS herunterladen (kein CDN zur Laufzeit – DSGVO)
RUN mkdir -p static/vendor/js static/vendor/css static/vendor/leaflet/images

RUN curl -fsSL https://unpkg.com/alpinejs@3.13.5/dist/cdn.min.js \
        -o static/vendor/js/alpine.min.js \
    && curl -fsSL https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js \
        -o static/vendor/js/htmx.min.js \
    && curl -fsSL https://unpkg.com/leaflet@1.9.4/dist/leaflet.js \
        -o static/vendor/js/leaflet.js \
    && curl -fsSL https://unpkg.com/leaflet@1.9.4/dist/leaflet.css \
        -o static/vendor/css/leaflet.css \
    && curl -fsSL "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png" \
        -o static/vendor/leaflet/images/marker-icon.png \
    && curl -fsSL "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png" \
        -o static/vendor/leaflet/images/marker-icon-2x.png \
    && curl -fsSL "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png" \
        -o static/vendor/leaflet/images/marker-shadow.png

# Tailwind CSS bauen
WORKDIR /app/theme/static_src
RUN npm install
RUN npm run build

WORKDIR /app

# Ausgabeverzeichnis für Tailwind sicherstellen
RUN mkdir -p theme/static/css/dist

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
