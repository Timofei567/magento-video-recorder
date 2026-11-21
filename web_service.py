"""Flask video service backed by PostgreSQL."""
import os
import time
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from flask import Flask, jsonify, request, send_from_directory, url_for
from psycopg2.extras import RealDictCursor
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", BASE_DIR / "uploads")).resolve()
ALLOWED_EXTENSIONS = {".webm", ".mp4", ".mov", ".m4v"}
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 500 * 1024 * 1024))


def get_db_connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=int(os.environ.get("DB_CONNECT_TIMEOUT", "5")),
    )


@contextmanager
def database_connection():
    """Commit or roll back a transaction and always close the connection."""
    connection = get_db_connection()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(max_attempts=60, retry_delay=2):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            with database_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS videos (
                            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            company_name TEXT NOT NULL UNIQUE,
                            file_path TEXT NOT NULL,
                            video_url TEXT NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        );
                    """)
            print("[INFO] PostgreSQL is ready; schema initialized.")
            return
        except psycopg2.OperationalError as exc:
            last_error = exc
            print(f"[INFO] Waiting for PostgreSQL ({attempt}/{max_attempts}): {exc}")
            if attempt < max_attempts:
                time.sleep(retry_delay)
    raise RuntimeError("PostgreSQL did not become ready.") from last_error


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def index():
        return jsonify(
            service="Magento video service",
            status="ok",
            endpoints={
                "upload": "POST /upload",
                "get_video_url": "GET /get_video_url?company_name=...",
                "media": "GET /media/<filename>",
                "videos": "GET /videos",
            },
        )

    @app.post("/upload")
    def upload_video():
        company_name = (request.form.get("company_name") or "").strip()
        video_file = request.files.get("file")
        if not company_name:
            return jsonify(error="company_name is required."), 400
        if video_file is None or not video_file.filename:
            return jsonify(error="A file field is required."), 400

        extension = Path(video_file.filename).suffix.lower() or ".webm"
        if extension not in ALLOWED_EXTENSIONS:
            return jsonify(error="Unsupported video file extension."), 400

        safe_company = secure_filename(company_name)[:100] or "recording"
        filename = f"{safe_company}{extension}"
        destination = UPLOAD_DIR / filename
        temporary = UPLOAD_DIR / f".{filename}.uploading"

        try:
            video_file.save(temporary)
            if not temporary.is_file() or temporary.stat().st_size == 0:
                temporary.unlink(missing_ok=True)
                return jsonify(error="Uploaded file is empty."), 400
            os.replace(temporary, destination)
            video_url = url_for("get_video", filename=filename, _external=True)

            with database_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO videos (company_name, file_path, video_url)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (company_name) DO UPDATE SET
                            file_path = EXCLUDED.file_path,
                            video_url = EXCLUDED.video_url,
                            updated_at = NOW();
                    """, (company_name, str(destination), video_url))

            return jsonify(company_name=company_name, video_url=video_url), 200
        except Exception:
            temporary.unlink(missing_ok=True)
            app.logger.exception("Video upload failed for %s", company_name)
            return jsonify(error="Video upload failed."), 500

    @app.get("/get_video_url")
    def get_video_url():
        company_name = (request.args.get("company_name") or "").strip()
        if not company_name:
            return jsonify(error="company_name is required."), 400
        with database_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT company_name, video_url FROM videos WHERE company_name = %s LIMIT 1;",
                    (company_name,),
                )
                record = cursor.fetchone()
        if record is None:
            return jsonify(error="Video not found."), 404
        return jsonify(company_name=record["company_name"], video_url=record["video_url"]), 200

    @app.get("/media/<path:filename>")
    def get_video(filename):
        return send_from_directory(
            UPLOAD_DIR, filename, mimetype="video/webm", conditional=True
        )

    @app.get("/videos")
    def list_videos():
        with database_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, company_name, file_path, video_url, created_at, updated_at
                    FROM videos ORDER BY id DESC;
                """)
                records = cursor.fetchall()
        for record in records:
            record["created_at"] = record["created_at"].isoformat()
            record["updated_at"] = record["updated_at"].isoformat()
        return jsonify(records)

    return app


app = create_app()
initialize_database()
