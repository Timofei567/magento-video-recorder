# C# implementation — CSV-driven Browser Automation Video Recorder

This folder contains the C#/.NET implementation of the second task. The Python Task 1 implementation is maintained in the repository alongside this C# project.

## Requirements
- .NET 8 SDK
- Chromium installed through Microsoft Playwright

## Build and install browser

From this folder:

```bash
dotnet restore
dotnet build
```

Install Chromium with PowerShell 7:

```bash
pwsh bin/Debug/net8.0/playwright.ps1 install chromium
```

On Linux without PowerShell, use the bundled Playwright CLI:

```bash
bin/Debug/net8.0/.playwright/node/linux-x64/node bin/Debug/net8.0/.playwright/package/cli.js install chromium
```

## Start the web service

```bash
dotnet run -- --serve
```

The service listens on `http://0.0.0.0:8000` by default. Override the host and port with `FLASK_HOST` and `FLASK_PORT`.

Endpoints:
- `POST /upload` — multipart fields `file` and `company_name`
- `GET /get_video_url?company_name=...` — returns the stored URL
- `GET /media/{filename}` — serves the WebM file with range support
- `GET /videos` — lists stored records

SQLite database: `videos.db`. Uploaded files: `uploads/`. Only file paths and URLs are stored in SQLite; video bytes remain on disk.

## Run the recorder

Place `input.csv` in this folder. Use semicolon delimiter and this exact header:

```text
URL;Company Name;Language;Country;Postcode;City;Street;HouseNo
```

Record locally without upload:

```bash
dotnet run
```

Record, upload each successful video, and preview it in Chromium:

```bash
dotnet run -- --server http://127.0.0.1:8000
```

Control preview duration (seconds):

```bash
dotnet run -- --server http://127.0.0.1:8000 --view-seconds 8
```

A value greater than zero closes the preview after that many seconds. A value of zero (default) waits for Enter in the console. Upload or preview errors are logged per row and do not stop the batch.

Videos are recorded into `./video/`. Repeated company names receive a numeric suffix rather than overwriting earlier local recordings.
