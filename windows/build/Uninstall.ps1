$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
$target = $PSScriptRoot
$answer = [System.Windows.Forms.MessageBox]::Show('¿Desinstalar AniStream Fresa? Tus favoritos e historial se conservarán.', 'AniStream Fresa', 'YesNo', 'Question')
if ($answer -ne 'Yes') { exit 0 }
foreach ($process in (Get-Process -Name AniStreamFresa -ErrorAction SilentlyContinue)) {
    if ($process.Path -eq (Join-Path $target 'AniStreamFresa.exe')) {
        [System.Windows.Forms.MessageBox]::Show('Cierra AniStream Fresa y vuelve a desinstalar.', 'AniStream Fresa') | Out-Null
        exit 1
    }
}
foreach ($directory in @([Environment]::GetFolderPath('Programs'), [Environment]::GetFolderPath('DesktopDirectory'))) {
    $shortcut = Join-Path $directory 'AniStream Fresa.lnk'
    if (Test-Path -LiteralPath $shortcut) { Remove-Item -LiteralPath $shortcut -Force }
}
Remove-Item -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AniStreamFresa' -Recurse -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $target -Recurse -Force
[System.Windows.Forms.MessageBox]::Show('AniStream Fresa se desinstaló. Tus datos se conservan en %LOCALAPPDATA%\AniStreamFresa.', 'AniStream Fresa') | Out-Null
