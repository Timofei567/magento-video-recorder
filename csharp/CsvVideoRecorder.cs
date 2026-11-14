using System.Globalization;
using Microsoft.Playwright;

namespace MagentoVideoRecorder;

public static class CsvVideoRecorder
{
    private static readonly string VideoDirectory = Path.GetFullPath("./video");
    private static readonly int ViewportWidth = 1280;
    private static readonly int ViewportHeight = 720;

    public static async Task RunAsync(string[] args)
    {
        var input = GetOption(args, "--input") ?? "input.csv";
        var serverUrl = GetOption(args, "--server");
        var viewSecondsText = GetOption(args, "--view-seconds") ?? "0";
        if (!double.TryParse(viewSecondsText, CultureInfo.InvariantCulture, out var viewSeconds) || viewSeconds < 0)
            throw new ArgumentException("--view-seconds must be a non-negative number.");

        if (!File.Exists(input))
            throw new FileNotFoundException("Input CSV was not found.", input);

        Directory.CreateDirectory(VideoDirectory);
        var rows = ReadCsv(input);
        if (rows.Count == 0) throw new InvalidOperationException("CSV contains no data rows.");

        var required = new[] { "URL", "Company Name", "Language", "Country", "Postcode", "City", "Street", "HouseNo" };
        var missing = required.Except(rows[0].Keys, StringComparer.Ordinal).ToArray();
        if (missing.Length > 0)
            throw new InvalidOperationException("CSV is missing columns: " + string.Join(", ", missing));

        var client = new VideoClient();
        var index = 1;
        foreach (var row in rows)
        {
            var company = row["Company Name"].Trim();
            Console.WriteLine($"[INFO] Row {index}: {company}");
            try
            {
                var videoPath = await RecordOneAsync(row, company);
                Console.WriteLine($"[OK] Video saved: {videoPath}");

                if (!string.IsNullOrWhiteSpace(serverUrl))
                {
                    try
                    {
                        var videoUrl = await client.UploadVideoAsync(serverUrl, videoPath, company);
                        Console.WriteLine($"[UPLOAD] {videoUrl}");
                        await PreviewAsync(videoUrl, viewSeconds);
                    }
                    catch (Exception ex)
                    {
                        Console.Error.WriteLine($"[UPLOAD/PREVIEW ERROR] {company}: {ex.Message}");
                    }
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"[RECORD ERROR] {company}: {ex.Message}");
            }
            index++;
        }
        Console.WriteLine("[DONE] Batch finished.");
    }

    private static async Task<string> RecordOneAsync(Dictionary<string, string> row, string company)
    {
        using var playwright = await Playwright.CreateAsync();
        await using var browser = await playwright.Chromium.LaunchAsync(new BrowserTypeLaunchOptions { Headless = false });
        var context = await browser.NewContextAsync(new BrowserNewContextOptions
        {
            ViewportSize = new ViewportSize { Width = ViewportWidth, Height = ViewportHeight },
            RecordVideoDir = VideoDirectory,
            RecordVideoSize = new RecordVideoSize { Width = ViewportWidth, Height = ViewportHeight }
        });

        var page = await context.NewPageAsync();
        var video = page.Video ?? throw new InvalidOperationException("Video recording is not available.");
        await page.AddInitScriptAsync(CursorScript);
        page.SetDefaultTimeout(15000);
        var target = string.IsNullOrWhiteSpace(row["URL"]) ? "https://duckduckgo.com/" : row["URL"].Trim();
        await page.GotoAsync(target, new PageGotoOptions { WaitUntil = WaitUntilState.DOMContentLoaded, Timeout = 45000 });
        await page.WaitForTimeoutAsync(1000);

        var search = page.Locator("textarea[name='q']").First;
        await search.WaitForAsync(new LocatorWaitForOptions { State = WaitForSelectorState.Visible, Timeout = 20000 });
        var query = "Magento developer in " + row["City"].Trim();

        // Move the real Playwright mouse gradually, matching the Python recorder.
        var searchBox = await search.BoundingBoxAsync()
            ?? throw new InvalidOperationException("Search field has no bounding box.");
        var searchPoint = (
            X: searchBox.X + searchBox.Width / 2,
            Y: searchBox.Y + searchBox.Height / 2
        );
        var mousePosition = await SmoothMoveAsync(page, (X: 0d, Y: 0d), searchPoint);
        await page.Mouse.ClickAsync(searchPoint.X, searchPoint.Y);
        await page.Keyboard.TypeAsync(query, new KeyboardTypeOptions { Delay = 105 });
        await page.Keyboard.PressAsync("Enter");

        var firstResult = page.Locator("a[data-testid='result-title-a']").First;
        await firstResult.WaitForAsync(new LocatorWaitForOptions { State = WaitForSelectorState.Visible, Timeout = 45000 });
        await firstResult.ScrollIntoViewIfNeededAsync();

        var resultBox = await firstResult.BoundingBoxAsync()
            ?? throw new InvalidOperationException("First search result has no bounding box.");
        var resultPoint = (
            X: resultBox.X + resultBox.Width / 2,
            Y: resultBox.Y + resultBox.Height / 2
        );
        mousePosition = await SmoothMoveAsync(page, mousePosition, resultPoint, durationMs: 900, steps: 36);
        await page.Mouse.ClickAsync(resultPoint.X, resultPoint.Y);
        try
        {
            await page.WaitForLoadStateAsync(LoadState.DOMContentLoaded, new PageWaitForLoadStateOptions { Timeout = 12000 });
        }
        catch (TimeoutException) { }
        await page.WaitForTimeoutAsync(1800);

        await context.CloseAsync();
        var recordedPath = await video.PathAsync();
        await browser.CloseAsync();

        var safeName = SafeFileName(company);
        var destination = Path.Combine(VideoDirectory, safeName + ".webm");
        var suffix = 2;
        while (File.Exists(destination))
            destination = Path.Combine(VideoDirectory, $"{safeName}_{suffix++}.webm");
        File.Move(recordedPath, destination);
        return destination;
    }

    private static async Task<(double X, double Y)> SmoothMoveAsync(
        IPage page,
        (double X, double Y) start,
        (double X, double Y) end,
        int durationMs = 800,
        int steps = 30)
    {
        for (var index = 1; index <= steps; index++)
        {
            var t = (double)index / steps;
            // Smoothstep easing: gradual acceleration and deceleration.
            var eased = t * t * (3 - 2 * t);
            var x = start.X + (end.X - start.X) * eased;
            var y = start.Y + (end.Y - start.Y) * eased;

            await page.Mouse.MoveAsync(x, y);
            await Task.Delay(Math.Max(1, durationMs / steps));
        }

        return end;
    }

    private static async Task PreviewAsync(string videoUrl, double seconds)
    {
        using var playwright = await Playwright.CreateAsync();
        await using var browser = await playwright.Chromium.LaunchAsync(new BrowserTypeLaunchOptions { Headless = false });
        var page = await browser.NewPageAsync();
        await page.GotoAsync(videoUrl, new PageGotoOptions { WaitUntil = WaitUntilState.DOMContentLoaded, Timeout = 45000 });
        Console.WriteLine(seconds > 0
            ? $"[PREVIEW] Browser will close in {seconds} seconds."
            : "[PREVIEW] Press Enter in this console to close the preview browser.");
        if (seconds > 0) await Task.Delay(TimeSpan.FromSeconds(seconds));
        else Console.ReadLine();
    }

    private static List<Dictionary<string, string>> ReadCsv(string path)
    {
        using var reader = new StreamReader(path);
        var headerLine = reader.ReadLine() ?? throw new InvalidOperationException("CSV is empty.");
        var headers = ParseCsvLine(headerLine).Select(x => x.Trim()).ToArray();
        var rows = new List<Dictionary<string, string>>();
        string? line;
        while ((line = reader.ReadLine()) is not null)
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            var values = ParseCsvLine(line);
            var row = new Dictionary<string, string>(StringComparer.Ordinal);
            for (var i = 0; i < headers.Length; i++)
                row[headers[i]] = i < values.Count ? values[i] : "";
            rows.Add(row);
        }
        return rows;
    }

    private static List<string> ParseCsvLine(string line)
    {
        var values = new List<string>();
        var current = new System.Text.StringBuilder();
        var quoted = false;
        for (var i = 0; i < line.Length; i++)
        {
            var ch = line[i];
            if (ch == '"')
            {
                if (quoted && i + 1 < line.Length && line[i + 1] == '"') { current.Append('"'); i++; }
                else quoted = !quoted;
            }
            else if (ch == ';' && !quoted) { values.Add(current.ToString()); current.Clear(); }
            else current.Append(ch);
        }
        values.Add(current.ToString());
        return values;
    }

    private static string? GetOption(string[] args, string name)
    {
        var index = Array.IndexOf(args, name);
        return index >= 0 && index + 1 < args.Length ? args[index + 1] : null;
    }

    private static string SafeFileName(string value)
    {
        var invalid = Path.GetInvalidFileNameChars().Concat(new[] { '/', '\\' }).ToHashSet();
        var cleaned = new string((string.IsNullOrWhiteSpace(value) ? "recording" : value.Trim())
            .Select(c => invalid.Contains(c) ? '_' : c).ToArray());
        return cleaned.Length > 100 ? cleaned[..100] : cleaned;
    }

    private const string CursorScript = """
        (() => {
          const install = () => {
            if (!document.documentElement || document.getElementById('__capture_cursor')) return;
            const style = document.createElement('style');
            style.textContent = '#__capture_cursor{position:fixed;left:0;top:0;width:32px;height:32px;z-index:2147483647;pointer-events:none;transform:translate(-2px,-2px)} #__capture_highlight{position:fixed;width:64px;height:64px;border-radius:50%;background:rgba(255,220,0,.38);transform:translate(-50%,-50%);z-index:2147483645;pointer-events:none}';
            document.documentElement.appendChild(style);
            const cursor = document.createElementNS('http://www.w3.org/2000/svg','svg');
            cursor.id='__capture_cursor'; cursor.setAttribute('viewBox','0 0 32 32');
            cursor.innerHTML='<path d="M3 2 L3 26 L10 19 L15 29 L20 26 L15 16 L26 16 Z" fill="white" stroke="black" stroke-width="1.8"/>';
            const highlight=document.createElement('div'); highlight.id='__capture_highlight';
            document.documentElement.append(cursor,highlight);
            document.addEventListener('mousemove',e=>{cursor.style.left=e.clientX+'px';cursor.style.top=e.clientY+'px';highlight.style.left=e.clientX+'px';highlight.style.top=e.clientY+'px';},true);
          };
          if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',install,{once:true}); else install();
        })();
        """;
}
