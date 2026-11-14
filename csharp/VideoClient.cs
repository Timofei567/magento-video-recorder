using System.Net.Http.Headers;
using System.Net.Http.Json;

namespace MagentoVideoRecorder;

public sealed class VideoClient
{
    private readonly HttpClient _http;

    public VideoClient(HttpClient? httpClient = null)
    {
        _http = httpClient ?? new HttpClient { Timeout = TimeSpan.FromMinutes(5) };
    }

    public async Task<string> UploadVideoAsync(string serverUrl, string videoPath, string companyName)
    {
        if (!File.Exists(videoPath))
            throw new FileNotFoundException("Video file not found.", videoPath);

        using var form = new MultipartFormDataContent();
        await using var stream = File.OpenRead(videoPath);
        using var fileContent = new StreamContent(stream);
        fileContent.Headers.ContentType = new MediaTypeHeaderValue("video/webm");
        form.Add(fileContent, "file", Path.GetFileName(videoPath));
        form.Add(new StringContent(companyName), "company_name");

        using var response = await _http.PostAsync(new Uri(new Uri(EnsureSlash(serverUrl)), "upload"), form);
        response.EnsureSuccessStatusCode();
        var result = await response.Content.ReadFromJsonAsync<VideoUrlResponse>()
                     ?? throw new InvalidOperationException("Upload response was empty.");
        return result.VideoUrl;
    }

    public async Task<string> GetVideoURLAsync(string serverUrl, string companyName)
    {
        var url = new Uri(new Uri(EnsureSlash(serverUrl)),
            "get_video_url?company_name=" + Uri.EscapeDataString(companyName));
        using var response = await _http.GetAsync(url);
        response.EnsureSuccessStatusCode();
        var result = await response.Content.ReadFromJsonAsync<VideoUrlResponse>()
                     ?? throw new InvalidOperationException("Lookup response was empty.");
        return result.VideoUrl;
    }

    private static string EnsureSlash(string value) => value.EndsWith('/') ? value : value + "/";

    private sealed class VideoUrlResponse
    {
        [System.Text.Json.Serialization.JsonPropertyName("video_url")]
        public string VideoUrl { get; set; } = "";
    }
}
