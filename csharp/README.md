# C# implementation — CSV-driven Browser Automation Video Recorder

This is the C#/.NET implementation of Task 2. It includes the recorder workflow, a lightweight ASP.NET Core web service, SQLite metadata storage, video upload, and Chromium preview. The original Python Task 1 implementation remains available in the repository; it is not required to run this C# Task 2 workflow.

## Requirements

- .NET 8 SDK
- Chromium for Microsoft Playwright

No Python packages are needed for the C# implementation.

## Build and install Chromium

Run these commands from this directory:

```bash
dotnet restore
dotnet build
```

Install the Playwright Chromium browser. The PowerShell script is the standard option on Windows, Linux, and macOS when PowerShell 7 is installed:

```bash
pwsh bin/Debug/net8.0/playwright.ps1 install chromium
```

On Linux x64 without PowerShell, the bundled Playwright Node runtime can be used instead:

```bash
bin/Debug/net8.0/.playwright/node/linux-x64/node bin/Debug/net8.0/.playwright/package/cli.js install chromium
```

If you build in Release configuration, replace `Debug` with `Release` in the install path.

## Start the web service

Open a terminal in this directory and run:

```bash
dotnet run -- --serve
```

By default, the service listens on port `8000` on all interfaces. You can override the bind address and port with `FLASK_HOST` and `FLASK_PORT` (for example, `FLASK_PORT=8080 dotnet run -- --serve` on Linux/macOS).

Keep this terminal running. Open a second terminal in the same directory for the recorder.

## API

- `POST /upload` — multipart form with `file` and `company_name`; saves the video and upserts the company record.
- `GET /get_video_url?company_name=...` — returns the saved video URL, or HTTP 404 if no record exists.
- `GET /media/{filename}` — serves the WebM file with byte-range support so browsers can play and seek.
- `GET /videos` — lists stored records.

Example API checks (run while the service is running):

```bash
curl -i http://127.0.0.1:8000/videos
curl -i 'http://127.0.0.1:8000/get_video_url?company_name=Example'
```

The second request returns 404 until a video for that company has been uploaded; this is expected.

## Data storage

The service creates `videos.db` (SQLite) and an `uploads/` directory in its working directory. SQLite stores the company name, local file path, video URL, and timestamps. Video bytes remain in files under `uploads/`, not in the database. Uploading another video for the same company updates its database record.

The recorder writes its local recordings under `video/`. These runtime files and the SQLite database are local data and should not be committed to Git.

## Run the recorder

Use a semicolon-delimited `input.csv` with this exact header:

```text
URL;Company Name;Language;Country;Postcode;City;Street;HouseNo
```

From the second terminal, run the recorder locally without uploading:

```bash
dotnet run
```

To record each row, upload the resulting video to the service, and open the returned URL in Chromium:

```bash
dotnet run -- --input input.csv --server http://127.0.0.1:8000
```

To close each preview automatically after eight seconds:

```bash
dotnet run -- --input input.csv --server http://127.0.0.1:8000 --view-seconds 8
```

A positive `--view-seconds` value closes the preview after that many seconds. The default value, `0`, waits for Enter in the console before closing the preview.

Upload and preview errors are logged for the affected CSV row; processing continues with the next row. The server must be running before using `--server`.