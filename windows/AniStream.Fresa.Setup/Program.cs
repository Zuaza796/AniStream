using System.Diagnostics;
using System.IO.Compression;
using System.Reflection;
using System.Runtime.InteropServices;
using Microsoft.Win32;
using AniStream.Fresa;
namespace AniStream.Fresa.Setup;

internal static class Program
{
    [STAThread] static void Main()
    {
        ApplicationConfiguration.Initialize();Application.Run(new SetupForm());
    }
}
public sealed class SetupForm:Form
{
    readonly string target=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","AniStreamFresa");
    readonly Label status=new(){AutoSize=false,Text="Un rinconcito rosa para tus próximas maratones.",ForeColor=Candy.Ink,Font=Candy.Font(12),TextAlign=ContentAlignment.MiddleCenter};
    readonly ProgressBar progress=new(){Minimum=0,Maximum=100,Visible=false,Style=ProgressBarStyle.Marquee};
    readonly StrawberryButton install;
    readonly Label caption=new(){Text="Instalar",TextAlign=ContentAlignment.MiddleCenter,ForeColor=Candy.Berry,Font=Candy.Font(12,FontStyle.Bold)};
    bool installed,busy;
    public SetupForm()
    {
        Text="Instalar AniStream Fresa";ClientSize=new(580,540);FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=false;StartPosition=FormStartPosition.CenterScreen;BackColor=Candy.Cream;
        Icon=Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        var logo=new StrawberryButton("♡","Bienvenida a AniStream Fresa"){Location=new(235,24),Size=new(110,125),TabStop=false,Cursor=Cursors.Default};Controls.Add(logo);
        var title=new Label(){Text="AniStream Fresa",Font=Candy.Font(27,FontStyle.Bold),ForeColor=Candy.Berry,TextAlign=ContentAlignment.MiddleCenter,Bounds=new(20,158,540,54)};Controls.Add(title);
        status.Bounds=new(35,221,510,70);Controls.Add(status);
        install=new StrawberryButton("+","Instalar AniStream Fresa",async (_,_)=>{if(installed)Launch();else await Install();}){Bounds=new(253,309,74,86)};Controls.Add(install);
        caption.Bounds=new(180,400,220,35);Controls.Add(caption);
        var destination=new Label(){Text="Se instalará solo para tu usuario, sin permisos de administrador.\nTus favoritos y tu historial tendrán su propia cestita.",ForeColor=Candy.Ink,Font=Candy.Font(9),TextAlign=ContentAlignment.MiddleCenter,Bounds=new(30,455,520,55)};Controls.Add(destination);
        progress.Bounds=new(75,437,430,6);Controls.Add(progress);
        FormClosing+=(_,e)=>{if(busy)e.Cancel=true;};
    }
    async Task Install()
    {
        if(busy)return;busy=true;install.Enabled=false;progress.Visible=true;caption.Text="Preparando tu cestita…";
        status.Text="Instalando la aplicación y su reproductor. No hace falta descargar nada más.";
        try
        {
            await Task.Run(Extract);
            CreateShortcuts();RegisterUninstaller();
            installed=true;install.Glyph="▶";install.AccessibleName="Abrir AniStream Fresa";caption.Text="Abrir AniStream Fresa";
            status.Text="¡Tu cestita está lista!\nEncuentra AniStream Fresa en Inicio y en el escritorio.";
        }
        catch(Exception e){status.Text="No se pudo completar la instalación.\n"+e.Message;caption.Text="Volver a intentar";}
        finally{busy=false;install.Enabled=true;progress.Visible=false;}
    }
    void Extract()
    {
        foreach(var process in Process.GetProcessesByName("AniStreamFresa"))
        {
            using(process)
            {
                try{if(string.Equals(process.MainModule?.FileName,Path.Combine(target,"AniStreamFresa.exe"),StringComparison.OrdinalIgnoreCase))throw new IOException("Cierra AniStream Fresa antes de actualizarla.");}
                catch(System.ComponentModel.Win32Exception){}
            }
        }
        string parent=Path.GetDirectoryName(target)!;Directory.CreateDirectory(parent);
        string staging=Path.Combine(parent,".anistream-fresa-"+Guid.NewGuid().ToString("N"));
        string backup=target+".previous";
        try
        {
            Directory.CreateDirectory(staging);
            using var payload=Assembly.GetExecutingAssembly().GetManifestResourceStream("AniStream.Payload.zip")??throw new IOException("El instalador no contiene la aplicación.");
            using var zip=new ZipArchive(payload,ZipArchiveMode.Read);
            zip.ExtractToDirectory(staging);
            if(!File.Exists(Path.Combine(staging,"AniStreamFresa.exe")))throw new IOException("El paquete de instalación está incompleto.");
            if(Directory.Exists(backup))Directory.Delete(backup,true);
            if(Directory.Exists(target))Directory.Move(target,backup);
            try{Directory.Move(staging,target);}
            catch{if(Directory.Exists(backup)&&!Directory.Exists(target))Directory.Move(backup,target);throw;}
            if(Directory.Exists(backup))Directory.Delete(backup,true);
        }
        finally{if(Directory.Exists(staging))Directory.Delete(staging,true);}
    }
    void CreateShortcuts()
    {
        Type shell=Type.GetTypeFromProgID("WScript.Shell")??throw new IOException("No se pudieron crear los accesos directos.");
        dynamic instance=Activator.CreateInstance(shell)!;
        try
        {
            foreach(string directory in new[]{Environment.GetFolderPath(Environment.SpecialFolder.Programs),Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory)})
            {
                Directory.CreateDirectory(directory);
                dynamic shortcut=instance.CreateShortcut(Path.Combine(directory,"AniStream Fresa.lnk"));
                shortcut.TargetPath=Path.Combine(target,"AniStreamFresa.exe");shortcut.WorkingDirectory=target;shortcut.Description="Tu rincón de anime rosa pastel";shortcut.IconLocation=Path.Combine(target,"AniStreamFresa.exe")+",0";shortcut.Save();
                Marshal.FinalReleaseComObject(shortcut);
            }
        }
        finally{Marshal.FinalReleaseComObject(instance);}
    }
    void RegisterUninstaller()
    {
        using var key=Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\AniStreamFresa");
        key.SetValue("DisplayName","AniStream Fresa");key.SetValue("DisplayVersion","0.1.0");key.SetValue("Publisher","Zuaza796");
        key.SetValue("InstallLocation",target);key.SetValue("DisplayIcon",Path.Combine(target,"AniStreamFresa.exe"));
        key.SetValue("UninstallString","powershell.exe -NoProfile -ExecutionPolicy Bypass -File \""+Path.Combine(target,"Uninstall.ps1")+"\"");
        key.SetValue("NoModify",1);key.SetValue("NoRepair",1);
    }
    void Launch(){try{Process.Start(new ProcessStartInfo(Path.Combine(target,"AniStreamFresa.exe")){UseShellExecute=true});Close();}catch(Exception e){status.Text=e.Message;}}
}
