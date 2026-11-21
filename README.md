# Magento Video Recorder

This repository contains the original Python recorder, the C# implementation from Test Task 2, and the Dockerized Flask/PostgreSQL version for Internship Task 1.

## Internship Task 1 — Docker, Apache, Flask and PostgreSQL

The internship implementation runs two services with Docker Compose:

- `web`: Apache + mod_wsgi + Flask, exposed at `http://localhost:8000`.
- `db`: PostgreSQL 16.

The Docker image installs only the web-service dependencies from `requirements-web.txt`. The root `requirements.txt` remains for the original Playwright recorder.

PostgreSQL data and uploaded videos are stored in named Docker volumes and survive container recreation.

### Requirements

- Docker Engine
- Docker Compose v2

### Configure and start

Copy `.env.example` to `.env`, then set a private database password:

```bash
cp .env.example .env
```

Start both containers:

```bash
docker compose up --build
```

The web container waits for PostgreSQL's healthcheck and also retries its database initialization before Apache starts serving the Flask application.

Open the service status endpoint:

```text
http://localhost:8000/
```

### API

- `POST /upload` — multipart form fields `file` and `company_name`; stores the video and inserts or updates the company record.
- `GET /get_video_url?company_name=...` — returns the saved video URL, or HTTP 404 if the company is not found.
- `GET /media/<filename>` — serves the uploaded video with byte-range support.
- `GET /videos` — lists stored video records.

Example upload:

```bash
curl -X POST http://localhost:8000/upload \
  -F "company_name=Example Company" \
  -F "file=@./example.webm"
```

Look up the URL:

```bash
curl "http://localhost:8000/get_video_url?company_name=Example%20Company"
```

### Persistence check

Stop and remove the containers without deleting named volumes:

```bash
docker compose down
docker compose up -d
```

The database records and uploaded videos remain available. Do not use `docker compose down -v` when you want to preserve them; that command deletes the named volumes.

Stop the services:

```bash
docker compose down
```

### Configuration

Database settings are supplied through environment variables. Keep the real `.env` file private and never commit it. `.env.example` is a safe template.

## Python Task 1 — Browser recorder

The original Python CSV-driven Playwright implementation remains available.

### Requirements

- Python 3.9+
- Chromium installed through Playwright

### Setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

Put data in `input.csv` using a semicolon delimiter and this exact header:

```text
URL;Company Name;Language;Country;Postcode;City;Street;HouseNo
```

Run:

```bash
python capture_video.py
```

Videos are saved to `./video/<Company_Name>.webm`.

## Test Task 2 — C# implementation

The C#/.NET 8 implementation is retained in `csharp/`. It includes the ASP.NET Core web service, SQLite metadata storage, video upload, and Chromium preview.

See [C# Task 2 instructions](csharp/README.md) for setup and usage.
