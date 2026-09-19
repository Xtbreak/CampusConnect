$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -m venv .venv-build
if ($LASTEXITCODE -ne 0) { throw '创建打包环境失败' }
& .\.venv-build\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { throw '安装打包依赖失败' }
& .\.venv-build\Scripts\python.exe prepare_icon.py
if ($LASTEXITCODE -ne 0) { throw '生成图标失败' }
& .\.venv-build\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --collect-all customtkinter --add-data 'assets;assets' --icon assets\campus.ico --name CampusConnect desktop.py
if ($LASTEXITCODE -ne 0) { throw 'EXE 打包失败' }
Write-Host '完成：dist\CampusConnect.exe'
