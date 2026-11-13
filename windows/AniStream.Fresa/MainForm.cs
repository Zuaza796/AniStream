using System.Diagnostics;
using System.Runtime.InteropServices;
using AniStream.Core;
using LibVLCSharp.Shared;
using LibVLCSharp.WinForms;
using VlcPlayer = LibVLCSharp.Shared.MediaPlayer;
namespace AniStream.Fresa;

public sealed class MainForm : Form
{
    readonly AnimeProvider provider = new();
    readonly LibraryStore library = new(Path.Combine(Program.Data,"library.json"));
    readonly LibVLC vlc;
    readonly VlcPlayer player;
    readonly VideoView video = new() { Dock = DockStyle.Fill, BackColor = Color.Black };
    readonly Panel shell = new() { Dock = DockStyle.Fill };
    readonly Panel browse = new() { Dock = DockStyle.Fill, AutoScroll = true };
    readonly Panel playerPage = new() { Dock = DockStyle.Fill, Visible = false, BackColor = Candy.Cream };
    readonly Panel videoHost = new() { Dock = DockStyle.Fill, BackColor = Color.Black };
    readonly Panel videoBar = new() { Height = 112, BackColor = Candy.Pink };
    readonly FlowLayoutPanel playbackButtons = new() { Dock = DockStyle.Bottom, Height = 72, WrapContents = false, BackColor = Candy.Pink };
    readonly TrackBar seek = new() { TickStyle = TickStyle.None, Minimum = 0, Maximum = 1000, Dock = DockStyle.Top, Height = 30, BackColor = Candy.Pink, AccessibleName = "Posición del episodio" };
    readonly TrackBar volume = new() { Minimum = 0, Maximum = 100, Value = 80, Width = 85, Height = 40, TickStyle = TickStyle.None, BackColor = Candy.Pink, AccessibleName = "Volumen", Margin = new(2,18,2,0) };
    readonly Label clock = new() { Width = 132, Height = 50, Margin = new(4,20,2,0), ForeColor = Candy.Ink, TextAlign = ContentAlignment.MiddleLeft };
    readonly Label status = new() { Dock = DockStyle.Bottom, Height = 36, Padding = new(16,8,10,0), ForeColor = Candy.Berry, BackColor = Candy.Cream, AutoEllipsis = true };
    readonly Label heading = new() { Text = "Tu rincón de anime", Dock = DockStyle.Top, Height = 52, Font = Candy.Font(24,FontStyle.Bold), ForeColor = Candy.Ink, Padding = new(20,7,0,0) };
    readonly TextBox search = new() { BorderStyle = BorderStyle.None, BackColor = Color.White, ForeColor = Candy.Ink, Font = Candy.Font(13), Width = 530, PlaceholderText = "Busca tu próximo anime…" };
    readonly ToolTip tips = new();
    readonly System.Windows.Forms.Timer tick = new() { Interval = 400 };
    readonly Stopwatch inactivity = Stopwatch.StartNew();
    readonly Label pipPlaceholder = new() { Dock = DockStyle.Fill, Text = "Tu anime sigue en la ventanita de fresa.\n\nPulsa P para traerlo de vuelta.", TextAlign = ContentAlignment.MiddleCenter, ForeColor = Candy.Berry, Font = Candy.Font(18) };
    readonly StrawberryButton pause, mute, previous, next, pipButton;
    readonly List<Control> compactHidden = [];
    readonly HashSet<string> imageRequests = [];
    CancellationTokenSource navigation = new(), playback = new();
    Form? pip;
    Media? media;
    Anime? current, requested;
    int requestedEpisode;
    IReadOnlyList<int> episodes = [];
    int episode, viewRevision;
    long lastSaved;
    bool closing, seeking, fullscreen, loading;
    Rectangle normalBounds;
    string view = "home";
    IReadOnlyList<Anime>? homeCatalog;
    Point lastMouse, lastScreenMouse;

    public MainForm(string? localVideo = null)
    {
        Text = "AniStream Fresa"; Size = new(1220,820); MinimumSize = new(980,680);
        StartPosition = FormStartPosition.CenterScreen; BackColor = Candy.Cream; ForeColor = Candy.Ink; Font = Candy.Font(); KeyPreview = true;
        string icon = Path.Combine(AppContext.BaseDirectory,"Assets","fresa.ico");
        if (File.Exists(icon)) Icon = new Icon(icon);
        else Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        vlc = new LibVLC("--no-video-title-show", "--no-mouse-events", "--no-keyboard-events");
        player = new(vlc) { Volume = 80 }; video.MediaPlayer = player;
        BuildBrowser();
        pause = Berry("Ⅱ","Pausar o continuar (Espacio)",(_,_) => { player.Pause(); ShowVideoControls(); });
        mute = Berry("♪","Silenciar o activar sonido",(_,_) => { player.Mute=!player.Mute;ShowVideoControls(); });
        previous = Berry("⏮","Episodio anterior",async (_,_) => await Step(-1));
        next = Berry("⏭","Episodio siguiente",async (_,_) => await Step(1));
        pipButton = Berry("pip","Picture-in-Picture (P)",(_,_) => TogglePip());
        var back = Berry("↶","Volver a los episodios (Esc)",async (_,_) => await LeavePlayer());
        var backward = Berry("−10","Retroceder diez segundos",(_,_) => player.Time=Math.Max(0,player.Time-10000));
        var forward = Berry("+10","Avanzar diez segundos",(_,_) => player.Time=Math.Min(Math.Max(0,player.Length-500),player.Time+10000));
        var full = Berry("⛶","Pantalla completa (F)",(_,_) => Fullscreen());
        var retry = Berry("↻","Volver a conectar",async (_,_) => { if(requested!=null) await Play(requested,requestedEpisode); });
        playbackButtons.Controls.AddRange([back,previous,backward,pause,forward,next,mute,volume,clock,retry,pipButton,full]);
        compactHidden.AddRange([back,previous,backward,forward,next,volume,retry,full]);
        videoBar.Controls.Add(playbackButtons);videoBar.Controls.Add(seek);
        videoHost.Controls.Add(video);videoHost.Controls.Add(videoBar);videoBar.BringToFront();
        playerPage.Controls.Add(videoHost);shell.Controls.Add(playerPage);playerPage.BringToFront();
        videoHost.Resize += (_,_) => PositionBar();
        video.MouseMove += (_,e) => { if(e.Location!=lastMouse){lastMouse=e.Location;ShowVideoControls();} };
        videoHost.MouseMove += (_,_) => ShowVideoControls();
        video.MouseDoubleClick += (_,_) => Fullscreen();
        foreach(Control control in playbackButtons.Controls) control.MouseMove += (_,_) => ShowVideoControls();
        seek.MouseDown += (_,_) => { seeking=true;ShowVideoControls(); };
        seek.MouseUp += (_,_) => { if(player.Length>0)player.Time=(long)(player.Length*seek.Value/1000.0);seeking=false;ShowVideoControls(); };
        seek.KeyUp += (_,e) => { if(player.Length>0)player.Time=(long)(player.Length*seek.Value/1000.0);ShowVideoControls(); };
        volume.ValueChanged += (_,_) => { player.Volume=volume.Value;ShowVideoControls(); };
        KeyDown += OnKeys;
        tick.Tick += (_,_) => Tick();tick.Start();
        FormClosing += OnClosing;
        Shown += async (_,_) =>
        {
            SetCaptionPink();
            if(localVideo!=null && File.Exists(localVideo))
            {
                current=new("Vídeo local", "/local");episode=1;episodes=[1];
                StartMedia(new(new Uri(Path.GetFullPath(localVideo)).AbsoluteUri,"https://animeav1.com/","Local"),0);
            }
            else await Home();
        };
    }
    StrawberryButton Berry(string glyph,string name,EventHandler click)
    {
        var b=new StrawberryButton(glyph,name,click);tips.SetToolTip(b,name);return b;
    }
    static Label Label(string text,int width=800,int height=36,float size=12,FontStyle style=FontStyle.Regular)
        => new(){Text=text,Width=width,Height=height,ForeColor=Candy.Ink,Font=Candy.Font(size,style),AutoEllipsis=true,Margin=new(12,5,8,5)};
    static FlowLayoutPanel Stack(int width) => new(){Width=width,AutoSize=true,FlowDirection=FlowDirection.TopDown,WrapContents=false,BackColor=Color.Transparent};
    void BuildBrowser()
    {
        var side=new FlowLayoutPanel(){Dock=DockStyle.Left,Width=112,BackColor=Candy.Pink,FlowDirection=FlowDirection.TopDown,WrapContents=false,Padding=new(10,14,0,0)};
        var logo=new StrawberryButton("♡","AniStream Fresa"){Size=new(82,92),Enabled=false,TabStop=false};side.Controls.Add(logo);
        foreach(var item in new (string Glyph,string Name,Func<Task> Action)[]{("home","Inicio",Home),("♡","Mi lista",()=>Collection("favorites")),("↺","Historial",()=>Collection("history"))})
        {
            var b=Berry(item.Glyph,item.Name,async (_,_) => await item.Action());b.Size=new(66,76);b.Margin=new(10,14,0,0);side.Controls.Add(b);
            var caption=Label(item.Name,90,24,10,FontStyle.Bold);caption.Margin=new(0);caption.TextAlign=ContentAlignment.MiddleCenter;side.Controls.Add(caption);
        }
        var header=new Panel(){Dock=DockStyle.Top,Height=154,BackColor=Candy.Cream};
        var brand=Label("AniStream Fresa",600,46,25,FontStyle.Bold);brand.Location=new(14,5);header.Controls.Add(brand);
        var subtitle=Label("Un episodio más, con un poquito de dulzura.",700,26,10);subtitle.Location=new(16,51);header.Controls.Add(subtitle);
        var searchPanel=new Panel(){BackColor=Color.White,Location=new(28,94),Size=new(560,40),Padding=new(12,10,6,6)};
        search.Dock=DockStyle.Fill;searchPanel.Controls.Add(search);header.Controls.Add(searchPanel);
        search.KeyDown+=async (_,e)=>{if(e.KeyCode==Keys.Enter){e.SuppressKeyPress=true;await Search();}};
        var find=Berry("search","Buscar anime",async (_,_)=>await Search());find.Location=new(598,80);header.Controls.Add(find);
        Controls.Add(shell);Controls.Add(side);Controls.Add(status);
        shell.Controls.Add(browse);shell.Controls.Add(heading);shell.Controls.Add(header);
        browse.Resize+=(_,_)=> Reflow();
    }
    void Reflow()
    {
        foreach(Control control in browse.Controls)
        {
            control.Width=Math.Max(600,browse.ClientSize.Width-34);
            if(control is FlowLayoutPanel stack)
                foreach(Control row in stack.Controls)
                    if(row is FlowLayoutPanel)row.Width=Math.Max(580,browse.ClientSize.Width-54);
        }
    }
    CancellationToken BeginView(string name,string title)
    {
        SavePosition();
        if(pip==null && playerPage.Visible){playback.Cancel();loading=false;player.Stop();current=null;}
        view=name;viewRevision++;
        navigation.Cancel();navigation.Dispose();navigation=new();
        heading.Text=title;heading.Visible=true;browse.Visible=true;
        playerPage.Visible=false;
        BrowseClear();status.Text="";
        return navigation.Token;
    }
    void BrowseClear(){foreach(Control c in browse.Controls.Cast<Control>().ToArray())c.Dispose();browse.Controls.Clear();}
    FlowLayoutPanel Content()
    {
        var stack=Stack(Math.Max(600,browse.ClientSize.Width-34));stack.Location=new(8,6);browse.Controls.Add(stack);return stack;
    }
    public async Task Home()
    {
        var ct=BeginView("home","Tu rincón de anime");
        var stack=Content();stack.Controls.Add(Label("Continuar viendo",800,42,18,FontStyle.Bold));
        var ongoing=library.Continuing.ToArray();
        if(ongoing.Length==0)stack.Controls.Add(Label("Aquí te esperarán los episodios que dejes a medias.",800,40));
        else AddCards(stack,ongoing.Select(w=>w.Series),ongoing,true);
        stack.Controls.Add(Label("Para tu próxima maratón",800,42,18,FontStyle.Bold));
        if(homeCatalog!=null)AddCards(stack,homeCatalog);
        else stack.Controls.Add(Label("Recolectando animes…",800,36));
        try
        {
            var items=await provider.Catalog("",ct);if(ct.IsCancellationRequested)return;
            homeCatalog=items;
            // Rebuild only this view after the catalog arrives; local progress is retained.
            BrowseClear();stack=Content();stack.Controls.Add(Label("Continuar viendo",800,42,18,FontStyle.Bold));
            if(ongoing.Length==0)stack.Controls.Add(Label("Aquí te esperarán los episodios que dejes a medias.",800,40));
            else AddCards(stack,ongoing.Select(w=>w.Series),ongoing,true);
            stack.Controls.Add(Label("Para tu próxima maratón",800,42,18,FontStyle.Bold));AddCards(stack,items);status.Text=$"{items.Count} animes · Tu biblioteca se guarda en este equipo";
        }
        catch(OperationCanceledException) when(ct.IsCancellationRequested){}
        catch(Exception e){if(!ct.IsCancellationRequested)Error(e,"No se pudo cargar el catálogo. Tu lista y tu historial siguen disponibles.");}
    }
    async Task Search()
    {
        if(string.IsNullOrWhiteSpace(search.Text)){await Home();return;}
        var ct=BeginView("search","Resultados para «"+search.Text.Trim()+"»");var stack=Content();status.Text="Buscando entre las fresitas…";
        try{var items=await provider.Catalog(search.Text.Trim(),ct);if(ct.IsCancellationRequested)return;AddCards(stack,items);status.Text=items.Count==0?"No hay resultados para esa búsqueda.":$"{items.Count} animes encontrados";}
        catch(OperationCanceledException)when(ct.IsCancellationRequested){}
        catch(Exception e){if(!ct.IsCancellationRequested)Error(e,"La búsqueda no respondió. Inténtalo otra vez.");}
    }
    Task Collection(string kind)
    {
        BeginView(kind,kind=="favorites"?"Mi cestita de favoritos":"Historial de episodios");var stack=Content();
        var history=kind=="history"?library.Recent.ToArray():null;
        var items=history?.Select(h=>h.Series).ToArray()??library.State.Favorites.Values.Reverse().ToArray();
        if(items.Length==0)stack.Controls.Add(Label(kind=="favorites"?"Guarda un anime con la fresita de corazón para encontrarlo aquí.":"Tus episodios aparecerán aquí cuando empieces a verlos.",800,70));
        else AddCards(stack,items,history);
        status.Text=$"{items.Length} animes guardados";return Task.CompletedTask;
    }
    void AddCards(FlowLayoutPanel stack,IEnumerable<Anime> source,IEnumerable<Watch>? watches=null,bool resume=false)
    {
        var row=new FlowLayoutPanel(){Width=Math.Max(580,browse.ClientSize.Width-54),AutoSize=true,WrapContents=true,BackColor=Color.Transparent,Margin=new(4,2,4,12)};
        var indexed=watches?.ToDictionary(w=>w.Series.Path)??new();
        foreach(var anime in source)
        {
            indexed.TryGetValue(anime.Path,out var watch);
            var card=new Panel(){Size=new(202,watch==null?350:382),Margin=new(8,8,8,16),BackColor=Color.FromArgb(255,235,242),Cursor=Cursors.Hand};
            var picture=new PictureBox(){Location=new(8,8),Size=new(186,228),SizeMode=PictureBoxSizeMode.Zoom,BackColor=Color.FromArgb(249,207,223),AccessibleName=anime.Title};card.Controls.Add(picture);picture.Disposed+=(_,_)=>picture.Image?.Dispose();
            _=LoadCover(picture,anime.Image);
            var title=Label(anime.Title,184,44,10,FontStyle.Bold);title.Location=new(8,240);title.Margin=Padding.Empty;card.Controls.Add(title);
            int actionsY=280;
            if(watch!=null)
            {
                var caption=Label($"Ep. {watch.Episode} · {Clock(watch.Position)} / {Clock(watch.Duration)}",184,22,9);caption.Location=new(8,283);card.Controls.Add(caption);
                var progress=new ProgressBar(){Location=new(10,308),Size=new(182,5),Maximum=1000,Value=watch.Duration>0?(int)Math.Clamp(watch.Position/watch.Duration*1000,0,1000):0};card.Controls.Add(progress);actionsY=316;
            }
            async Task Open(){if(resume&&watch!=null)await Resume(watch);else await Detail(anime);}
            picture.Click+=async (_,_)=>await Open();title.Click+=async (_,_)=>await Open();
            var play=Berry("▶",watch!=null&&LibraryStore.IsUnfinished(watch)?"Continuar episodio "+watch.Episode:"Ver episodios",async (_,_)=>{if(watch!=null&&LibraryStore.IsUnfinished(watch))await Resume(watch);else await Detail(anime);});play.Location=new(10,actionsY);play.Size=new(46,55);card.Controls.Add(play);
            var favorite=Berry(library.State.Favorites.ContainsKey(anime.Path)?"♥":"♡","Guardar o quitar de Mi lista",(_,_)=>library.ToggleFavorite(anime));
            favorite.Click+=async (_,_)=>{favorite.Glyph=library.State.Favorites.ContainsKey(anime.Path)?"♥":"♡";favorite.Invalidate();if(view=="favorites")await Collection("favorites");};
            favorite.Location=new(144,actionsY);favorite.Size=new(46,55);card.Controls.Add(favorite);
            row.Controls.Add(card);
        }
        stack.Controls.Add(row);
    }
    async Task LoadCover(PictureBox picture,string url)
    {
        if(string.IsNullOrEmpty(url)||!Uri.TryCreate(url,UriKind.Absolute,out var uri)||uri.Scheme!="https")return;
        try
        {
            using var http=new HttpClient(){Timeout=TimeSpan.FromSeconds(12)};
            var bytes=await http.GetByteArrayAsync(uri);
            using var stream=new MemoryStream(bytes);using var image=Image.FromStream(stream);
            if(!picture.IsDisposed)picture.Image=new Bitmap(image);
        }
        catch{/* A missing cover must never block navigation. */}
    }
    async Task Detail(Anime anime)
    {
        var ct=BeginView("detail",anime.Title);var stack=Content();
        var description=Label(anime.Description,Math.Max(580,browse.ClientSize.Width-60),100,11);description.AutoEllipsis=true;stack.Controls.Add(description);
        var favorite=Berry(library.State.Favorites.ContainsKey(anime.Path)?"♥":"♡","Añadir o quitar de Mi lista",(_,_)=>library.ToggleFavorite(anime));favorite.Click+=(_,_)=>{favorite.Glyph=library.State.Favorites.ContainsKey(anime.Path)?"♥":"♡";favorite.Invalidate();};stack.Controls.Add(favorite);
        status.Text="Preparando los episodios…";
        try
        {
            var nums=await provider.Episodes(anime,ct);if(ct.IsCancellationRequested)return;
            var last=library.State.History.GetValueOrDefault(anime.Path);
            if(last!=null&&nums.Contains(last.Episode))
            {
                var text=Label($"Continuar episodio {last.Episode} desde {Clock(last.Position)}",700,28,11,FontStyle.Bold);stack.Controls.Add(text);
                stack.Controls.Add(Berry("▶","Continuar episodio",async (_,_)=>{episodes=nums;await Play(anime,last.Episode);}));
            }
            stack.Controls.Add(Label("Elige tu episodio",700,38,17,FontStyle.Bold));
            var row=new FlowLayoutPanel(){Width=Math.Max(580,browse.ClientSize.Width-54),AutoSize=true,WrapContents=true};
            foreach(int n in nums)
            {
                var berry=Berry(n.ToString(),"Reproducir episodio "+n,async (_,_)=>{episodes=nums;await Play(anime,n);});berry.Size=new(62,72);row.Controls.Add(berry);
            }
            stack.Controls.Add(row);status.Text=$"{nums.Count} episodios disponibles";
        }
        catch(OperationCanceledException)when(ct.IsCancellationRequested){}
        catch(Exception e){if(!ct.IsCancellationRequested)Error(e,"No se pudieron obtener los episodios.");}
    }
    async Task Resume(Watch watch)
    {
        navigation.Cancel();navigation.Dispose();navigation=new();var ct=navigation.Token;
        status.Text=$"Preparando {watch.Series.Title} · episodio {watch.Episode}…";
        try{var nums=await provider.Episodes(watch.Series,ct);if(ct.IsCancellationRequested)return;if(!nums.Contains(watch.Episode))throw new InvalidOperationException("El episodio ya no está disponible.");episodes=nums;await Play(watch.Series,watch.Episode);}
        catch(OperationCanceledException)when(ct.IsCancellationRequested){}
        catch(Exception e){if(!ct.IsCancellationRequested)Error(e,"No se pudo continuar el episodio.");}
    }
    async Task Play(Anime anime,int number)
    {
        SavePosition();if(pip!=null)ReturnPip();
        navigation.Cancel();requested=anime;requestedEpisode=number;
        playback.Cancel();playback.Dispose();playback=new();var ct=playback.Token;
        player.Stop();current=null;loading=true;
        heading.Visible=false;browse.Visible=false;playerPage.Visible=true;playerPage.BringToFront();
        ShowVideoControls();status.Text=$"{anime.Title} · Episodio {number} · Conectando…";
        try
        {
            var sources=await provider.Sources(anime,number,ct);
            Exception? last=null;
            foreach(var source in sources.SelectMany(s=>new[]{s,s}))
            {
                ct.ThrowIfCancellationRequested();
                try
                {
                    status.Text=$"{anime.Title} · Episodio {number} · {source.Name}…";
                    var link=await provider.Resolve(source,ct);ct.ThrowIfCancellationRequested();
                    current=anime;episode=number;
                    double position=library.Position(anime,number);
                    if(library.State.History.TryGetValue(anime.Path,out var watch)&&watch.Episode==number&&watch.Duration>0&&position>=watch.Duration-3)position=0;
                    StartMedia(link,position);
                    var deadline=DateTime.UtcNow.AddSeconds(22);
                    while(DateTime.UtcNow<deadline && !ct.IsCancellationRequested)
                    {
                        await Task.Delay(200,ct);
                        if(player.State==VLCState.Error)throw new IOException("El servidor no pudo iniciar el vídeo.");
                        if(player.Time>0&&player.Length>0){loading=false;status.Text=$"{anime.Title} · Episodio {number}";return;}
                    }
                    throw new TimeoutException("El vídeo tardó demasiado en responder.");
                }
                catch(OperationCanceledException)when(ct.IsCancellationRequested){throw;}
                catch(Exception e){last=e;player.Stop();current=null;Program.Log(source.Name+": "+e.Message);}
            }
            throw last??new IOException("No hay servidores compatibles para este episodio.");
        }
        catch(OperationCanceledException)when(ct.IsCancellationRequested){}
        catch(Exception e){if(!ct.IsCancellationRequested){loading=false;Error(e,"No se pudo cargar el vídeo. La fresita de reintento vuelve a conectar.");ShowVideoControls();}}
    }
    void StartMedia(StreamLink link,double position)
    {
        media?.Dispose();media=new Media(vlc,new Uri(link.Url));
        media.AddOption(":http-referrer="+link.Referer);media.AddOption(":http-user-agent=Mozilla/5.0");
        media.AddOption(":network-caching=1500");media.AddOption(":start-time="+position.ToString(System.Globalization.CultureInfo.InvariantCulture));
        media.AddOption(":avcodec-hw=any");
        video.MediaPlayer=player;player.Play(media);lastSaved=0;
        heading.Visible=false;browse.Visible=false;playerPage.Visible=true;playerPage.BringToFront();ShowVideoControls();
    }
    async Task Step(int direction)
    {
        if(current==null)return;int i=episodes.ToList().IndexOf(episode)+direction;
        if(i>=0&&i<episodes.Count)await Play(current,episodes[i]);
    }
    async Task LeavePlayer()
    {
        SavePosition();playback.Cancel();loading=false;player.Stop();current=null;
        if(pip!=null)ReturnPip();if(fullscreen)Fullscreen();playerPage.Visible=false;
        heading.Visible=true;browse.Visible=true;
        if(view=="history"||view=="favorites")await Collection(view);else await Home();
    }
    void SavePosition()
    {
        if(current==null||current.Path=="/local"||player.Time<=0)return;
        try{library.Record(current,episode,player.Time/1000.0,player.Length/1000.0);lastSaved=player.Time;}
        catch(Exception e){Program.Log(e.ToString());status.Text="No se pudo guardar la posición. Comprueba el espacio del disco.";}
    }
    void Tick()
    {
        if(closing)return;
        Point pointer=Cursor.Position;
        if(pointer!=lastScreenMouse&&videoHost.Visible&&videoHost.RectangleToScreen(videoHost.ClientRectangle).Contains(pointer))ShowVideoControls();
        lastScreenMouse=pointer;
        long time=player.Time,length=player.Length;
        pause.Glyph=player.IsPlaying?"Ⅱ":"▶";pause.Invalidate();mute.Glyph=player.Mute?"×":"♪";mute.Invalidate();
        if(!seeking&&length>0)seek.Value=(int)Math.Clamp(time/(double)length*1000,0,1000);
        clock.Text=Clock(time/1000.0)+" / "+Clock(length/1000.0);
        int i=episodes.ToList().IndexOf(episode);previous.Enabled=current!=null&&i>0;next.Enabled=current!=null&&i>=0&&i<episodes.Count-1;
        pipButton.Enabled=current!=null&&length>0&&!loading;
        if(current!=null&&time>0&&Math.Abs(time-lastSaved)>=5000)SavePosition();
        if(player.State==VLCState.Error&&!loading){status.Text="La conexión se interrumpió. Pulsa la fresita de reintento.";ShowVideoControls();}
        if(inactivity.ElapsedMilliseconds>2500&&!seeking&&!loading&&player.State!=VLCState.Error)videoBar.Visible=false;
        if(videoBar.Visible)videoBar.BringToFront();
    }
    static string Clock(double seconds)=>TimeSpan.FromSeconds(Math.Max(0,double.IsFinite(seconds)?seconds:0)).ToString(seconds>=3600?@"h\:mm\:ss":@"mm\:ss");
    void PositionBar(){videoBar.SetBounds(0,Math.Max(0,videoHost.Height-videoBar.Height),videoHost.Width,videoBar.Height);videoBar.BringToFront();}
    void ShowVideoControls(){inactivity.Restart();videoBar.Visible=true;PositionBar();}
    void TogglePip()
    {
        if(pip!=null){ReturnPip();return;}if(current==null||loading)return;
        if(fullscreen)Fullscreen();SavePosition();
        pip=new Form(){Text="AniStream Fresa · PiP",Size=new(500,330),MinimumSize=new(370,250),TopMost=true,BackColor=Color.Black,StartPosition=FormStartPosition.Manual,KeyPreview=true,Icon=Icon};
        var area=Screen.FromControl(this).WorkingArea;pip.Location=new(area.Right-pip.Width-20,area.Bottom-pip.Height-20);
        pip.KeyDown+=OnKeys;pip.FormClosing+=(_,e)=>{if(!closing&&pip!=null){e.Cancel=true;ReturnPip();}};
        videoHost.Parent=pip;videoHost.Dock=DockStyle.Fill;
        playerPage.Controls.Add(pipPlaceholder);pipPlaceholder.BringToFront();
        foreach(var c in compactHidden)c.Visible=false;
        pip.Show();ShowVideoControls();
    }
    void ReturnPip()
    {
        if(pip==null)return;var old=pip;pip=null;
        videoHost.Parent=playerPage;videoHost.Dock=DockStyle.Fill;
        pipPlaceholder.Parent=null;foreach(var c in compactHidden)c.Visible=true;
        old.Close();old.Dispose();ShowVideoControls();
        if(!closing){playerPage.Visible=true;heading.Visible=false;browse.Visible=false;Activate();}
    }
    void Fullscreen()
    {
        if(pip!=null)ReturnPip();
        if(!fullscreen){normalBounds=Bounds;FormBorderStyle=FormBorderStyle.None;WindowState=FormWindowState.Normal;Bounds=Screen.FromControl(this).Bounds;fullscreen=true;}
        else{FormBorderStyle=FormBorderStyle.Sizable;Bounds=normalBounds;fullscreen=false;}
        ShowVideoControls();
    }
    async void OnKeys(object? sender,KeyEventArgs e)
    {
        if(!playerPage.Visible&&pip==null)return;
        if(ActiveControl==search)return;
        if(e.KeyCode==Keys.Space){player.Pause();e.SuppressKeyPress=true;}
        else if(e.KeyCode==Keys.P)TogglePip();
        else if(e.KeyCode==Keys.F)Fullscreen();
        else if(e.KeyCode==Keys.Left)player.Time=Math.Max(0,player.Time-10000);
        else if(e.KeyCode==Keys.Right)player.Time=Math.Min(Math.Max(0,player.Length-500),player.Time+10000);
        else if(e.KeyCode==Keys.Escape){if(pip!=null)ReturnPip();else if(fullscreen)Fullscreen();else await LeavePlayer();}
        else return;
        e.Handled=true;ShowVideoControls();
    }
    void Error(Exception e,string message){Program.Log(e.ToString());status.Text=message+" "+e.Message;}
    void OnClosing(object? sender,FormClosingEventArgs e)
    {
        closing=true;SavePosition();navigation.Cancel();playback.Cancel();tick.Stop();ReturnPip();
        video.MediaPlayer=null;player.Stop();media?.Dispose();player.Dispose();vlc.Dispose();provider.Dispose();tips.Dispose();
    }
    [DllImport("dwmapi.dll")]static extern int DwmSetWindowAttribute(IntPtr hwnd,int attr,ref int value,int size);
    void SetCaptionPink(){try{int color=ColorTranslator.ToWin32(Candy.Pink);DwmSetWindowAttribute(Handle,35,ref color,4);}catch(DllNotFoundException){}}
}
