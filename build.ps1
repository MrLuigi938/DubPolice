# Builds dist/DubPolice.exe. Requirements are in docs/development.md.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

foreach ($file in 'libspeex-1.dll', '7z.exe', '7z.dll') {
    if (-not (Test-Path -LiteralPath "bin\$file")) { throw "bin\$file is missing, see docs/development.md." }
}

if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --quiet --disable-pip-version-check -r requirements-build.txt

.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name DubPolice `
    --icon "$PSScriptRoot\assets\dub-police.ico" `
    --distpath dist --workpath build --specpath build --paths src `
    --hidden-import sammax_de --hidden-import gui --hidden-import enhance `
    --add-binary "$PSScriptRoot\bin\libspeex-1.dll;bin" `
    --add-binary "$PSScriptRoot\bin\7z.exe;bin" `
    --add-binary "$PSScriptRoot\bin\7z.dll;bin" `
    --add-data "$PSScriptRoot\src\ui;ui" `
    src\launcher.py
