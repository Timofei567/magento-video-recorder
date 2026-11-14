# CSV-driven Browser Automation Video Recorder

## Python Task 1

The original Python implementation is kept in the repository.

### Requirements
- Python 3.9+
- Chromium installed through Playwright

### Setup
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

### Run
Put your data in `input.csv` using a semicolon (`;`) as delimiter and the exact header:

```text
URL;Company Name;Language;Country;Postcode;City;Street;HouseNo
```

Then run:

```bash
python capture_video.py
```

Videos are saved to `./video/<Company_Name>.webm`. If a company name repeats, a numeric suffix is added rather than overwriting an earlier recording.

The sample scenario searches DuckDuckGo for `Magento developer in <City>`. The other address and language fields are accepted as function arguments; the demo query uses the city value.

## Task 2 — C# implementation

Task 2 is implemented in C#/.NET 8 with an ASP.NET Core web service, SQLite metadata storage, video upload, and Chromium preview. The Python Task 1 files remain alongside it; **you do not need to install Python dependencies to run the C# Task 2 solution**.

See [C# Task 2 setup and usage](csharp/README.md) for build instructions, Chromium installation, API endpoints, server startup, and the complete recorder → upload → preview workflow.
