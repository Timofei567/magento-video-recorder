using Microsoft.Data.Sqlite;

namespace MagentoVideoRecorder;

public static class VideoService
{
    private static readonly string Root = AppContext.BaseDirectory;
    private static readonly string UploadDirectory = Path.Combine(Root, "uploads");
    private static readonly string DatabasePath = Path.Combine(Root, "videos.db");
    private static string ConnectionString =>
        new SqliteConnectionStringBuilder { DataSource = DatabasePath, DefaultTimeout = 30 }.ToString();

    public static async Task RunAsync()
    {
        Directory.CreateDirectory(UploadDirectory);
        await InitializeDatabaseAsync();

        var builder = WebApplication.CreateBuilder();
        var host = Environment.GetEnvironmentVariable("FLASK_HOST");
        var port = Environment.GetEnvironmentVariable("FLASK_PORT");
        builder.WebHost.UseUrls($"http://{(string.IsNullOrWhiteSpace(host) ? "0.0.0.0" : host)}:{(int.TryParse(port, out var parsedPort) ? parsedPort : 8000)}");

        var app = builder.Build();

        app.MapPost("/upload", async (HttpRequest request) =>
        {
            if (!request.HasFormContentType)
                return Results.BadRequest(new { error = "Expected multipart/form-data." });

            var form = await request.ReadFormAsync();
            var companyName = form["company_name"].ToString().Trim();
            var file = form.Files.GetFile("file");

            if (string.IsNullOrWhiteSpace(companyName))
                return Results.BadRequest(new { error = "company_name is required." });
            if (file is null || file.Length == 0)
                return Results.BadRequest(new { error = "A non-empty file field is required." });

            var fileName = SafeFileName(companyName) + ".webm";
            var destination = Path.GetFullPath(Path.Combine(UploadDirectory, fileName));
            var temporary = destination + ".uploading";

            try
            {
                await using (var output = File.Create(temporary))
                    await file.CopyToAsync(output);

                File.Move(temporary, destination, overwrite: true);
                var videoUrl = $"{request.Scheme}://{request.Host}/media/{Uri.EscapeDataString(fileName)}";

                await using var connection = new SqliteConnection(ConnectionString);
                await connection.OpenAsync();
                await using var command = connection.CreateCommand();
                command.CommandText = """
                    INSERT INTO videos (company_name, file_path, video_url)
                    VALUES ($company, $path, $url)
                    ON CONFLICT(company_name) DO UPDATE SET
                        file_path = excluded.file_path,
                        video_url = excluded.video_url,
                        updated_at = datetime('now');
                    """;
                command.Parameters.AddWithValue("$company", companyName);
                command.Parameters.AddWithValue("$path", destination);
                command.Parameters.AddWithValue("$url", videoUrl);
                await command.ExecuteNonQueryAsync();

                return Results.Ok(new { company_name = companyName, video_url = videoUrl });
            }
            catch
            {
                if (File.Exists(temporary)) File.Delete(temporary);
                throw;
            }
        });

        app.MapGet("/get_video_url", async (string? company_name) =>
        {
            if (string.IsNullOrWhiteSpace(company_name))
                return Results.BadRequest(new { error = "company_name is required." });

            await using var connection = new SqliteConnection(ConnectionString);
            await connection.OpenAsync();
            await using var command = connection.CreateCommand();
            command.CommandText = "SELECT company_name, video_url FROM videos WHERE company_name = $company LIMIT 1";
            command.Parameters.AddWithValue("$company", company_name.Trim());
            await using var reader = await command.ExecuteReaderAsync();

            if (!await reader.ReadAsync())
                return Results.NotFound(new { error = "Video not found." });

            return Results.Ok(new { company_name = reader.GetString(0), video_url = reader.GetString(1) });
        });

        app.MapGet("/media/{filename}", (string filename) =>
        {
            var safeName = Path.GetFileName(filename);
            if (!string.Equals(filename, safeName, StringComparison.Ordinal))
                return Results.BadRequest(new { error = "Invalid filename." });

            var path = Path.Combine(UploadDirectory, safeName);
            return File.Exists(path)
                ? Results.File(path, "video/webm", enableRangeProcessing: true)
                : Results.NotFound();
        });

        app.MapGet("/videos", async () =>
        {
            var records = new List<object>();
            await using var connection = new SqliteConnection(ConnectionString);
            await connection.OpenAsync();
            await using var command = connection.CreateCommand();
            command.CommandText = "SELECT company_name, file_path, video_url, created_at, updated_at FROM videos ORDER BY id DESC";
            await using var reader = await command.ExecuteReaderAsync();
            while (await reader.ReadAsync())
                records.Add(new
                {
                    company_name = reader.GetString(0),
                    file_path = reader.GetString(1),
                    video_url = reader.GetString(2),
                    created_at = reader.GetString(3),
                    updated_at = reader.GetString(4)
                });
            return Results.Ok(records);
        });

        Console.WriteLine("Video service listening. SQLite database: " + DatabasePath);
        await app.RunAsync();
    }

    private static async Task InitializeDatabaseAsync()
    {
        await using var connection = new SqliteConnection(ConnectionString);
        await connection.OpenAsync();
        await using var command = connection.CreateCommand();
        command.CommandText = """
            PRAGMA journal_mode=WAL;
            PRAGMA busy_timeout=30000;
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL UNIQUE,
                file_path TEXT NOT NULL,
                video_url TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """;
        await command.ExecuteNonQueryAsync();
    }

    private static string SafeFileName(string value)
    {
        var invalid = Path.GetInvalidFileNameChars();
        var cleaned = new string(value.Trim().Select(c => invalid.Contains(c) || c == '/' || c == '\\' ? '_' : c).ToArray());
        cleaned = string.Join("_", cleaned.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));
        return string.IsNullOrWhiteSpace(cleaned) ? "recording" : cleaned[..Math.Min(cleaned.Length, 100)];
    }
}
