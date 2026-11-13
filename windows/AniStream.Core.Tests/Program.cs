using System.Text;
using System.Text.Json;
using AniStream.Core;

int count=0;
void Assert(bool check,string name){if(!check)throw new Exception("FAIL "+name);Console.WriteLine("PASS "+name);count++;}
var catalog=AnimeProvider.ParseCatalog("<article><a href='/media/example'></a><h3>Anime de prueba</h3><img src='/cover.jpg'><p>Sinopsis</p></article>");
Assert(catalog.Count==1&&catalog[0].Title=="Anime de prueba"&&catalog[0].Image==AnimeProvider.Base+"/cover.jpg","Catálogo y portada relativa");
Assert(AnimeProvider.ParseCatalog("<article><h3>Sin enlace</h3></article>").Count==0,"Artículos sin serie ignorados");
var episodes=AnimeProvider.ParseEpisodes("episodes:["+string.Join(',',Enumerable.Range(1,220).Select(n=>"{id:"+n+",number:"+n+"}"))+"]","/media/example");
Assert(episodes.Count==220&&episodes[219]==220,"Todos los episodios serializados, no solo los primeros 50");
var sources=AnimeProvider.ParseSources("embeds:{SUB:[{server:\"Voe\",url:\"https://voe.sx/e/example\"}]},downloads:{SUB:[{server:\"MP4Upload\",url:\"https://download.example\"}]}");
Assert(sources.Count==1&&sources[0].Name=="Voe","No se confunden descargas con fuentes de vídeo");
var links=AnimeProvider.ParseSources("embeds:{SUB:[{server:\"Voe\",url:\"https://voe.sx/e/a\"},{server:\"MP4Upload\",url:\"https://www.mp4upload.com/embed-a.html\"}]},downloads:{}");
Assert(links[0].Name=="MP4Upload"&&links[1].Name=="Voe","Prioridad de servidores y fallback");
string target="https://video.example/master.m3u8";
string first=Convert.ToBase64String(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new{source=target})));
string shifted=new(first.Reverse().Select(c=>(char)(c+3)).ToArray());
string encoded=Convert.ToBase64String(Encoding.UTF8.GetBytes(shifted));
encoded=new(encoded.Select(c=>c is >= 'a' and <= 'z'?(char)('a'+(c-'a'+13)%26):c is >= 'A' and <= 'Z'?(char)('A'+(c-'A'+13)%26):c).ToArray());
Assert(AnimeProvider.DecodeVoe(encoded)==target,"Datos Voe decodificados sin ejecutar scripts");
string folder=Path.Combine(Path.GetTempPath(),"anistream-fresa-test-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(folder);
try
{
    string file=Path.Combine(folder,"library.json");var store=new LibraryStore(file);var anime=catalog[0];
    store.ToggleFavorite(anime);store.Record(anime,3,120,1440);
    var again=new LibraryStore(file);
    Assert(again.State.Favorites.ContainsKey(anime.Path),"Favoritos conservados al reabrir");
    Assert(again.Position(anime,3)==120&&again.Continuing.Single().Episode==3,"Continuar episodio correcto desde la posición guardada");
    again.Record(anime,3,1400,1440);
    Assert(!again.Continuing.Any()&&again.Recent.Count()==1,"Terminados quedan en historial y salen de Continuar");
    again.ToggleFavorite(anime);Assert(!new LibraryStore(file).State.Favorites.Any(),"Quitar favorito persiste");
    again.Record(anime,4,double.NaN,0);Assert(again.Recent.Single().Episode==3,"No se registra un intento sin reproducción válida");
    File.WriteAllText(file,"invalid json");var recovered=new LibraryStore(file);
    Assert(!recovered.State.History.Any()&&Directory.GetFiles(folder,"*.invalid-*").Length==1,"Biblioteca dañada se conserva como copia");
}
finally{Directory.Delete(folder,true);}
Console.WriteLine($"{count} pruebas correctas.");
if(args.Contains("--live"))
{
    using var provider=new AnimeProvider();using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(100));
    var items=await provider.Catalog("naruto",timeout.Token);Console.WriteLine("LIVE catálogo: "+items.Count+" resultados");
    var anime=items.First(a=>a.Path=="/media/naruto");var nums=await provider.Episodes(anime,timeout.Token);
    Console.WriteLine("LIVE episodios: "+nums.Count);
    var hosts=await provider.Sources(anime,nums[0],timeout.Token);
    foreach(var host in hosts)
    {
        try{var link=await provider.Resolve(host,timeout.Token);Console.WriteLine("LIVE vídeo comprobado: "+link.Server+" / "+new Uri(link.Url).Host);break;}
        catch(Exception e){Console.WriteLine("LIVE "+host.Name+": "+e.Message);if(host==hosts.Last())throw;}
    }
}
