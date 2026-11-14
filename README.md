# CSV-driven Browser Automation Video Recorder

## Requirements
- Python 3.9+
- Chromium installed through Playwright

## Setup
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Run
Put your data in `input.csv` using `;` as delimiter and the exact header:
`URL;Company Name;Language;Country;Postcode;City;Street;HouseNo`

Then run:
```bash
python capture_video.py
```

Videos are saved to `./video/<Company_Name>.webm`. If a company name repeats,
a numeric suffix is added rather than overwriting an earlier recording.

The sample scenario searches DuckDuckGo for `Magento developer in <City>`.
`Language`, `Country`, `Postcode`, `Street`, and `HouseNo` are accepted as
required function arguments as specified in the task; the requested demo query
uses the city value.


## Task 2 — C# implementation

The second task is implemented separately in [`csharp/`](csharp/). See [`csharp/README.md`](csharp/README.md) for .NET setup, service endpoints, database details, recording, upload, and browser preview instructions. The Python Task 1 implementation is in the repository.
