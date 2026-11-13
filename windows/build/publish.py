"""Cross-publish the Windows app and a self-contained, offline, per-user installer."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[2]
WINDOWS=ROOT/'windows'
ARTIFACTS=WINDOWS/'artifacts'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dotnet',default='dotnet')
    args=parser.parse_args()
    def publish(project,destination,*extra):
        subprocess.run([args.dotnet,'publish',str(WINDOWS/project),'-c','Release','-r','win-x64','--self-contained','true','-o',str(destination),'-p:EnableWindowsTargeting=true','-v','minimal',*extra],check=True,cwd=ROOT)
    portable=ARTIFACTS/'portable'
    if portable.exists():shutil.rmtree(portable)
    publish('AniStream.Fresa/AniStream.Fresa.csproj',portable)
    for path in ('AniStreamFresa.exe','libvlc/win-x64/libvlc.dll','libvlc/win-x64/libvlccore.dll','libvlc/win-x64/plugins/codec/libavcodec_plugin.dll'):
        if not (portable/path).is_file():raise RuntimeError('Paquete incompleto: '+path)
    for pdb in portable.rglob('*.pdb'):pdb.unlink()
    shutil.copytree(WINDOWS/'licenses',portable/'licenses',dirs_exist_ok=True)
    shutil.copy2(ROOT/'LICENSE',portable/'licenses/AniStream-MIT.txt')
    shutil.copy2(ROOT/'third_party/anicli-esp/LICENSE',portable/'licenses/anicli-esp-MIT.txt')
    shutil.copy2(WINDOWS/'README.md',portable/'LEEME.md')
    # Windows PowerShell 5.1 expects a BOM to interpret Spanish correctly.
    (portable/'Uninstall.ps1').write_text((WINDOWS/'build/Uninstall.ps1').read_text(),encoding='utf-8-sig')
    release=ARTIFACTS/'releases';release.mkdir(parents=True,exist_ok=True)
    payload=release/'AniStreamFresa-Windows-x64-portable.zip'
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(portable.rglob('*')):
            if path.is_file():archive.write(path,path.relative_to(portable).as_posix())
    setup=ARTIFACTS/'setup'
    if setup.exists():shutil.rmtree(setup)
    publish('AniStream.Fresa.Setup/AniStream.Fresa.Setup.csproj',setup,'-p:PayloadZip='+str(payload))
    shutil.copy2(setup/'AniStreamFresa-Setup.exe',release/'AniStreamFresa-Setup.exe')
    products=[release/'AniStreamFresa-Setup.exe',payload]
    checksums=[]
    for file in products:
        with file.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        checksums.append(digest+'  '+file.name)
        print(file.name,round(file.stat().st_size/1024/1024,1),'MiB',digest)
    (release/'SHA256SUMS.txt').write_text('\n'.join(checksums)+'\n')
    (release/'BUILD-INFO.json').write_text(json.dumps({'edition':'AniStream Fresa','version':'0.1.0','target':'Windows x64','selfContained':True,'nativePlayer':'LibVLC 3.0.24','windowsGuiValidated':False,'buildCommand':'python windows/build/publish.py'},indent=2)+'\n')

if __name__=='__main__':main()
