using System.Text.Json;
namespace AniStream.Core;

public sealed record Anime(string Title, string Path, string Image = "", string Description = "");
public sealed record Source(string Name, string Embed);
public sealed record StreamLink(string Url, string Referer, string Server);
public sealed record Watch(Anime Series, int Episode, double Position, double Duration, DateTimeOffset Updated);
public sealed class LibraryState
{
    public Dictionary<string, Anime> Favorites { get; set; } = [];
    public Dictionary<string, Watch> History { get; set; } = [];
    public Dictionary<string, Dictionary<int, double>> Positions { get; set; } = [];
    public Dictionary<string, Dictionary<int, double>> Durations { get; set; } = [];
}
public sealed class LibraryStore
{
    readonly string path;
    static readonly JsonSerializerOptions Json = new() { WriteIndented = true, PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
    public LibraryState State { get; private set; } = new();
    public LibraryStore(string path)
    {
        this.path = path;
        if (!File.Exists(path)) return;
        try
        {
            State = JsonSerializer.Deserialize<LibraryState>(File.ReadAllText(path), Json) ?? new();
            State.Favorites ??= []; State.History ??= []; State.Positions ??= []; State.Durations ??= [];
        }
        catch (JsonException)
        {
            File.Move(path, path + ".invalid-" + DateTime.UtcNow.Ticks);
        }
    }
    public void Save()
    {
        Directory.CreateDirectory(System.IO.Path.GetDirectoryName(System.IO.Path.GetFullPath(path))!);
        string temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            using (var file = new FileStream(temp, FileMode.CreateNew, FileAccess.Write))
            {
                JsonSerializer.Serialize(file, State, Json);
                file.Flush(true);
            }
            File.Move(temp, path, true);
        }
        finally { if (File.Exists(temp)) File.Delete(temp); }
    }
    public IEnumerable<Watch> Recent => State.History.Values.OrderByDescending(x => x.Updated);
    public IEnumerable<Watch> Continuing => Recent.Where(IsUnfinished);
    public static bool IsUnfinished(Watch watch) => watch.Position > 0 && double.IsFinite(watch.Position)
        && (watch.Duration <= 0 || (watch.Position < watch.Duration * .95 && watch.Duration - watch.Position > 3));
    public double Position(Anime anime, int episode) => State.Positions.GetValueOrDefault(anime.Path)?.GetValueOrDefault(episode) ?? 0;
    public void Record(Anime anime, int episode, double seconds, double duration)
    {
        if (!double.IsFinite(seconds) || seconds <= 0) return;
        if (!State.Positions.ContainsKey(anime.Path)) State.Positions[anime.Path] = [];
        State.Positions[anime.Path][episode] = seconds;
        if (duration > 0 && double.IsFinite(duration))
        {
            if (!State.Durations.ContainsKey(anime.Path)) State.Durations[anime.Path] = [];
            State.Durations[anime.Path][episode] = duration;
        }
        State.History[anime.Path] = new(anime, episode, seconds, duration, DateTimeOffset.UtcNow);
        Save();
    }
    public void ToggleFavorite(Anime anime)
    {
        if (!State.Favorites.Remove(anime.Path)) State.Favorites[anime.Path] = anime;
        Save();
    }
}
