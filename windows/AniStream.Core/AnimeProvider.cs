// AnimeAv1 adapter based on anicli-esp 1.3.1, Alejandro Sempere (MIT).
// See third_party/anicli-esp/LICENSE in the repository and bundled licenses.
using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using AngleSharp.Html.Parser;
namespace AniStream.Core;

public sealed class AnimeProvider : IDisposable
{
    public const string Base = "https://animeav1.com";
    readonly HttpClient http = new() { Timeout = TimeSpan.FromSeconds(18) };
    public AnimeProvider() => http.DefaultRequestHeaders.UserAgent.ParseAdd("Mozilla/5.0");
    public void Dispose() => http.Dispose();
    async Task<string> Text(string url, CancellationToken ct, string? referer = null)
    {
        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri) || uri.Scheme != "https") throw new InvalidOperationException("El proveedor devolvió un enlace no válido.");
        for (int retry = 0; ; retry++)
        {
            try
            {
                using var request = new HttpRequestMessage(HttpMethod.Get, uri);
                if (referer != null) request.Headers.Referrer = new(referer);
                using var response = await http.SendAsync(request, ct).ConfigureAwait(false);
                response.EnsureSuccessStatusCode();
                return await response.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
            }
            catch (HttpRequestException) when (retry == 0 && !ct.IsCancellationRequested)
            { await Task.Delay(450, ct).ConfigureAwait(false); }
        }
    }
    public static IReadOnlyList<Anime> ParseCatalog(string html)
    {
        var doc = new HtmlParser().ParseDocument(html);
        return doc.QuerySelectorAll("article").Select(a =>
        {
            var link = a.QuerySelector("a[href^='/media/']")?.GetAttribute("href");
            var title = a.QuerySelector("h3")?.TextContent.Trim();
            var image = a.QuerySelector("img")?.GetAttribute("src") ?? "";
            return link == null || string.IsNullOrWhiteSpace(title) ? null
                : new Anime(title, link, image.Length == 0 ? "" : new Uri(new Uri(Base), image).ToString(), a.QuerySelector("p")?.TextContent.Trim() ?? "");
        }).Where(a => a != null).Cast<Anime>().DistinctBy(a => a.Path).ToArray();
    }
    public Task<IReadOnlyList<Anime>> Catalog(string query, CancellationToken ct) => CatalogInternal(query, ct);
    async Task<IReadOnlyList<Anime>> CatalogInternal(string query, CancellationToken ct)
        => ParseCatalog(await Text(Base + "/catalogo?search=" + Uri.EscapeDataString(query), ct).ConfigureAwait(false));
    public static IReadOnlyList<int> ParseEpisodes(string html, string path)
    {
        var block = Regex.Match(html, @"episodes:\[(.*?)\]", RegexOptions.Singleline);
        var numbers = Regex.Matches(block.Value, @"number:(\d+)").Select(m => int.Parse(m.Groups[1].Value)).ToArray();
        if (numbers.Length == 0)
        {
            var doc = new HtmlParser().ParseDocument(html);
            numbers = doc.QuerySelectorAll("article a[href]").Select(a => a.GetAttribute("href")!)
                .Where(p => p.StartsWith(path + "/", StringComparison.Ordinal))
                .Select(p => int.TryParse(p.Split('/').Last(), out var n) ? n : 0).Where(n => n > 0).ToArray();
        }
        if (numbers.Length == 0) throw new InvalidOperationException("Esta serie no tiene episodios disponibles en este momento.");
        return numbers.Distinct().Order().ToArray();
    }
    public async Task<IReadOnlyList<int>> Episodes(Anime anime, CancellationToken ct)
        => ParseEpisodes(await Text(Base + anime.Path, ct).ConfigureAwait(false), anime.Path);
    public static IReadOnlyList<Source> ParseSources(string html)
    {
        var block = Regex.Match(html, @"embeds:\{(.*?)\},downloads:", RegexOptions.Singleline);
        if (!block.Success) throw new InvalidOperationException("No hay servidores disponibles para este episodio.");
        var pairs = Regex.Matches(block.Groups[1].Value, "server:\"([^\"]+)\",url:\"([^\"]+)\"")
            .Select(m => new Source(m.Groups[1].Value, m.Groups[2].Value.Replace("\\", ""))).Distinct().ToArray();
        return new[] { "MP4Upload", "Voe" }.SelectMany(name => pairs.Where(p => p.Name == name)).ToArray();
    }
    public async Task<IReadOnlyList<Source>> Sources(Anime anime, int episode, CancellationToken ct)
        => ParseSources(await Text(Base + anime.Path + "/" + episode, ct).ConfigureAwait(false));
    public static string DecodeVoe(string encoded)
    {
        string rotated = new(encoded.Select(c => c is >= 'a' and <= 'z' ? (char)('a' + (c - 'a' + 13) % 26)
            : c is >= 'A' and <= 'Z' ? (char)('A' + (c - 'A' + 13) % 26) : c).ToArray());
        rotated = Regex.Replace(rotated, "[^A-Za-z0-9+/=]", "");
        string shifted = Encoding.UTF8.GetString(Convert.FromBase64String(rotated));
        string reversed = new(shifted.Select(c => (char)(c - 3)).Reverse().ToArray());
        using var json = JsonDocument.Parse(Convert.FromBase64String(reversed));
        return json.RootElement.GetProperty("source").GetString() ?? throw new InvalidOperationException("Voe no devolvió el vídeo.");
    }
    public async Task<StreamLink> Resolve(Source source, CancellationToken ct)
    {
        string embed = source.Embed;
        string html = await Text(embed, ct, Base + "/").ConfigureAwait(false);
        string url, referer;
        if (source.Name == "MP4Upload")
        {
            var match = Regex.Match(html, "src:\\s*[\"'](https:[^\"']+)[\"']");
            if (!match.Success) throw new InvalidOperationException("MP4Upload no devolvió un enlace de vídeo.");
            url = match.Groups[1].Value.Replace("\\", "");
            if (!Regex.IsMatch(url, @"\.(mp4|m3u8)(\?|$)")) throw new InvalidOperationException("El enlace del servidor no es un vídeo.");
            referer = "https://www.mp4upload.com/";
        }
        else if (source.Name == "Voe")
        {
            for (int i = 0; i < 3; i++)
            {
                var redirect = Regex.Match(html, "window\\.location\\.href\\s*=\\s*[\"'](https://[^\"']+)");
                if (!redirect.Success) break;
                embed = redirect.Groups[1].Value;
                html = await Text(embed, ct, Base + "/").ConfigureAwait(false);
            }
            var doc = new HtmlParser().ParseDocument(html);
            var data = doc.QuerySelector("script[type='application/json']")?.TextContent ?? throw new InvalidOperationException("Voe no devolvió datos del vídeo.");
            using var json = JsonDocument.Parse(data);
            url = DecodeVoe(json.RootElement[0].GetString()!);
            referer = embed;
        }
        else throw new InvalidOperationException("Servidor no compatible.");
        await CheckMedia(url, referer, ct).ConfigureAwait(false);
        return new(url, referer, source.Name);
    }
    public async Task CheckMedia(string url, string referer, CancellationToken ct)
    {
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(ct);
        deadline.CancelAfter(TimeSpan.FromSeconds(16));
        for (int depth = 0; depth < 4; depth++)
        {
            if (!Uri.TryCreate(url, UriKind.Absolute, out var uri) || uri.Scheme != "https") throw new InvalidOperationException("El vídeo no tiene un enlace HTTPS válido.");
            using var request = new HttpRequestMessage(HttpMethod.Get, uri);
            request.Headers.Referrer = new(referer);
            request.Headers.Range = new(0, 16383);
            using var response = await http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, deadline.Token).ConfigureAwait(false);
            response.EnsureSuccessStatusCode();
            using var input = await response.Content.ReadAsStreamAsync(deadline.Token).ConfigureAwait(false);
            byte[] buffer = new byte[16384];
            int count = 0;
            while (count < buffer.Length)
            {
                int read = await input.ReadAsync(buffer.AsMemory(count), deadline.Token).ConfigureAwait(false);
                if (read == 0) break;
                count += read;
            }
            if (count == 0) throw new InvalidOperationException("El servidor devolvió un vídeo vacío.");
            string first = Encoding.UTF8.GetString(buffer, 0, count);
            if (!first.StartsWith("#EXTM3U", StringComparison.Ordinal)) return;
            var next = first.Split('\n').Select(l => l.Trim()).FirstOrDefault(l => l.Length > 0 && !l.StartsWith('#'));
            if (next == null) throw new InvalidOperationException("Lista de reproducción vacía.");
            url = new Uri(uri, next).ToString();
        }
        throw new InvalidOperationException("No se pudo comprobar el vídeo.");
    }
}
