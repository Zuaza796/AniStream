using LibVLCSharp.Shared;
namespace AniStream.Fresa;
internal static class Program
{
    public static readonly string Data = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AniStreamFresa");
    [STAThread]
    static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        Directory.CreateDirectory(Data);
        Application.ThreadException += (_,e) => Report(e.Exception);
        AppDomain.CurrentDomain.UnhandledException += (_,e) => Log(e.ExceptionObject.ToString() ?? "Error");
        try
        {
            string vlc = Path.Combine(AppContext.BaseDirectory, "libvlc", "win-x64");
            LibVLCSharp.Shared.Core.Initialize(vlc);
            Application.Run(new MainForm(args.FirstOrDefault()));
        }
        catch (Exception e) { Report(e); }
    }
    public static void Log(string text)
    {
        try { File.AppendAllText(Path.Combine(Data,"errors.log"),DateTimeOffset.Now+" "+text+Environment.NewLine); } catch { }
    }
    static void Report(Exception e)
    {
        Log(e.ToString());
        MessageBox.Show("No se pudo completar la operación.\n\n"+e.Message+"\n\nEl registro está en:\n"+Path.Combine(Data,"errors.log"),"AniStream Fresa",MessageBoxButtons.OK,MessageBoxIcon.Information);
    }
}
