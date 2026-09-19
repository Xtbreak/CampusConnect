param([string]$OutputDirectory = 'dist')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$projectRoot = (Get-Location).Path
$assetDirectory = Join-Path $projectRoot 'assets'
$iconPath = Join-Path $assetDirectory 'campus.ico'
py -m venv .venv-build
if ($LASTEXITCODE -ne 0) { throw '创建打包环境失败' }
& .\.venv-build\Scripts\python.exe -m pip install -r requirements\build.txt
if ($LASTEXITCODE -ne 0) { throw '安装打包依赖失败' }
& .\.venv-build\Scripts\python.exe -m scripts.prepare_icon
if ($LASTEXITCODE -ne 0) { throw '生成图标失败' }
& .\.venv-build\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --paths $projectRoot --collect-all customtkinter --add-data "$assetDirectory;assets" --icon $iconPath --specpath build --distpath $OutputDirectory --name CampusConnect scripts\launch.py
if ($LASTEXITCODE -ne 0) { throw 'EXE 打包失败' }
Write-Host (Join-Path $OutputDirectory 'CampusConnect.exe')
